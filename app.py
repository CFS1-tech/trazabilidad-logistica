"""
app.py  —  WMS MASEF en Streamlit
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
import io
from google.oauth2.service_account import Credentials
from datetime import date, datetime

st.set_page_config(
    page_title="WMS MASEF",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #0f1923; }
[data-testid="stSidebar"] * { color: #e0e6f0 !important; }
[data-testid="stSidebar"] hr { border-color: #2d3748; }
[data-testid="stMetric"] { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 20px; }
[data-testid="stMetricLabel"] { font-size: 12px !important; color: #64748b !important; }
[data-testid="stMetricValue"] { font-size: 26px !important; color: #0f172a !important; font-weight: 600 !important; }
.stButton > button { background-color: #185FA5 !important; color: white !important; border: none !important; border-radius: 8px !important; font-weight: 500 !important; }
.stButton > button:hover { background-color: #0C447C !important; }
[data-testid="stForm"] { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; }
h2 { color: #1e293b !important; font-weight: 600 !important; font-size: 18px !important; }
</style>
""", unsafe_allow_html=True)

MOVIMIENTOS_ENTRADA = {"INGRESO", "AJUSTE-IN"}
MOVIMIENTOS_SALIDA  = {"SALIDA", "AJUSTE-OUT", "MERMA"}
SHEET_NAME          = "TRAZABILIDAD"

@st.cache_resource
def get_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )

    return gspread.authorize(creds)

@st.cache_data(ttl=300)
def cargar_datos() -> pd.DataFrame:

    client = get_client()

    sh = client.open_by_key(
        st.secrets["spreadsheet_id"]
    )

    ws = sh.worksheet(SHEET_NAME)

    df = pd.DataFrame(
        ws.get_all_records()
    )

    def parse_fecha(col):

        parsed = pd.to_datetime(
            col,
            dayfirst=True,
            errors="coerce"
        )

        mask = (
            parsed.isna()
            &
            col.astype(str).str.strip().ne("")
        )

        if mask.any():

            parsed[mask] = pd.to_datetime(
                col[mask],
                format="%Y-%m-%d",
                errors="coerce"
            )

        return parsed

    df["FECHA"] = parse_fecha(
        df["FECHA"].astype(str)
    )

    df["FECHA VCTO"] = parse_fecha(
        df["FECHA VCTO"].astype(str)
    )

    df["TOTAL UNIT"] = pd.to_numeric(
        df["TOTAL UNIT"],
        errors="coerce"
    ).fillna(0).astype(int)

    df["SKU MASEF"] = df["SKU MASEF"].astype(str)

    df["CTN"] = df["CTN"].astype(str)

    return df.dropna(subset=["FECHA"])

@st.cache_data(ttl=300)
def cargar_packinglist() -> pd.DataFrame:

    client = get_client()

    sh = client.open_by_key(
        st.secrets["spreadsheet_id"]
    )

    ws = sh.worksheet("PACKINGLIST")

    df_pk = pd.DataFrame(
        ws.get_all_records()
    )

    return df_pk


def calcular_stock(
    df: pd.DataFrame,
    fecha_corte,
    excluir_tipos=None
) -> pd.DataFrame:

    corte = pd.to_datetime(fecha_corte)

    sub = df[
        df["FECHA"].dt.date <= corte.date()
    ].copy()

    if excluir_tipos:
        sub = sub[
            ~sub["TIPO DE MOVIMIENTO"].isin(excluir_tipos)
        ]

    # ─────────────────────────────────────────────
    # LIMPIAR CAMPOS
    # ─────────────────────────────────────────────

    sub["SKU MASEF"]   = sub["SKU MASEF"].astype(str).str.strip()
    sub["CTN"]         = sub["CTN"].astype(str).str.strip()
    sub["ESTADO"]      = sub["ESTADO"].astype(str).str.strip()
    sub["DESCRIPTION"] = sub["DESCRIPTION"].astype(str).str.strip()

    # ─────────────────────────────────────────────
    # MATRIZ SKU -> DESCRIPCIÓN
    # ─────────────────────────────────────────────

    matriz_sku = (
        sub[["SKU MASEF", "DESCRIPTION"]]
        .dropna()
        .query("DESCRIPTION != ''")
        .drop_duplicates(subset=["SKU MASEF"])
    )

    # ─────────────────────────────────────────────
    # PASO 1: SKUs con stock NETO > 0
    # Solo los SKUs donde la suma total de TOTAL UNIT
    # es mayor a 0 tienen stock real en almacén.
    # ─────────────────────────────────────────────

    neto_por_sku = (
        sub
        .groupby("SKU MASEF")["TOTAL UNIT"]
        .sum()
    )

    skus_con_stock = neto_por_sku[neto_por_sku > 0].index

    # ─────────────────────────────────────────────
    # PASO 2: Filtrar solo filas de esos SKUs
    # ─────────────────────────────────────────────

    sub_valido = sub[sub["SKU MASEF"].isin(skus_con_stock)]

    # ─────────────────────────────────────────────
    # PASO 3: Agrupar por detalle y quedarse
    # solo con combinaciones de stock positivo.
    # GENERAL: agrupa SIN fecha vencimiento
    # Resto:   agrupa CON fecha vencimiento
    # ─────────────────────────────────────────────

    sub_general = sub_valido[sub_valido["ESTADO"] == "GENERAL"]
    sub_resto   = sub_valido[sub_valido["ESTADO"] != "GENERAL"]

    # GENERAL → SKU + CTN + ESTADO (sin FECHA VCTO)
    result_general = (
        sub_general
        .groupby(["SKU MASEF", "CTN", "ESTADO"], dropna=False)["TOTAL UNIT"]
        .sum()
        .reset_index()
        .rename(columns={"TOTAL UNIT": "Stock"})
    )
    result_general["FECHA VCTO"] = ""

    # Resto → SKU + CTN + ESTADO + FECHA VCTO
    result_resto = (
        sub_resto
        .groupby(["SKU MASEF", "CTN", "ESTADO", "FECHA VCTO"], dropna=False)["TOTAL UNIT"]
        .sum()
        .reset_index()
        .rename(columns={"TOTAL UNIT": "Stock"})
    )

    result = pd.concat([result_general, result_resto], ignore_index=True)

    result = result[result["Stock"] > 0].copy()

    result["Stock"] = result["Stock"].astype(int)

    # ─────────────────────────────────────────────
    # AGREGAR DESCRIPCIÓN
    # ─────────────────────────────────────────────

    result = result.merge(
        matriz_sku,
        on="SKU MASEF",
        how="left"
    )

    # ─────────────────────────────────────────────
    # FORMATEAR FECHA
    # ─────────────────────────────────────────────

    result["FECHA VCTO"] = (
        pd.to_datetime(result["FECHA VCTO"], errors="coerce")
        .dt.strftime("%Y-%m-%d")
        .fillna("")
    )

    return result.sort_values("Stock", ascending=False).reset_index(drop=True)


def to_excel(df_export: pd.DataFrame) -> bytes:

    buf = io.BytesIO()

    with pd.ExcelWriter(
        buf,
        engine="openpyxl"
    ) as writer:

        df_export.to_excel(
            writer,
            index=False,
            sheet_name="Reporte"
        )

    return buf.getvalue()

def botones_descarga(df_display, nombre):

    col_csv, col_xlsx = st.columns(2)

    with col_csv:

        st.download_button(
            "⬇️ Exportar CSV",
            df_display.to_csv(index=False).encode("utf-8"),
            f"{nombre}_{date.today()}.csv",
            "text/csv",
            use_container_width=True
        )

    with col_xlsx:

        st.download_button(
            "📊 Exportar Excel",
            to_excel(df_display),
            f"{nombre}_{date.today()}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:

    st.markdown("### 📦 WMS MASEF")

    st.markdown(
        "<small style='color:#64748b'>Warehouse Management System</small>",
        unsafe_allow_html=True
    )

    st.markdown("---")

    st.markdown(
        "<small style='color:#64748b;text-transform:uppercase;letter-spacing:.08em'>REPORTES</small>",
        unsafe_allow_html=True
    )

    vista = st.radio("", [
        "📦  Stock",
        "🔍  Trazabilidad",
        "📦  Packing List",
        "⚠️  Merma",
        "🚚  Despachos por Ingreso",
    ], label_visibility="collapsed")

    st.markdown("---")

    st.markdown(
        "<small style='color:#64748b;text-transform:uppercase;letter-spacing:.08em'>SISTEMA</small>",
        unsafe_allow_html=True
    )

    if st.button(
        "🔄  Recargar datos",
        use_container_width=True
    ):
        st.cache_data.clear()
        st.rerun()

    st.markdown(
        f"<small style='color:#4a5568'>Última carga: {datetime.now().strftime('%H:%M:%S')}</small>",
        unsafe_allow_html=True
    )

# ── Carga de datos ────────────────────────────────────────────────────────────

try:

    df = cargar_datos()
    packing_df = cargar_packinglist()

except Exception as e:

    st.error(
        f"❌ Error conectando a Google Sheets: {e}"
    )

    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# VISTA: STOCK
# ══════════════════════════════════════════════════════════════════════════════

if vista == "📦  Stock":

    st.markdown("## 📦 Reporte de Stock")

    st.caption(
        "Stock acumulado hasta la fecha de corte."
    )

    # ── Filtros ──
    with st.form("form_stock"):

        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

        with col1:

            fecha_corte = st.date_input(
                "📅 Fecha de corte",
                value=date.today(),
                min_value=df["FECHA"].min().date(),
                max_value=date.today()
            )

        with col2:

            buscar = st.text_input(
                "🔎 Buscar SKU o descripción",
                placeholder="ej: NUTELLA"
            )

        with col3:

            estados_opts = ["Todos"] + sorted(
                df["ESTADO"]
                .dropna()
                .unique()
                .tolist()
            )

            f_estado = st.selectbox(
                "🏷️ Estado",
                estados_opts
            )

        with col4:

            st.write("")
            st.write("")

            st.form_submit_button(
                "🔍 Buscar",
                use_container_width=True
            )

    # ─────────────────────────────────────────────────────────────
    # MÉTRICAS GLOBALES
    # ─────────────────────────────────────────────────────────────

    sub_global = df[
        df["FECHA"].dt.date <= fecha_corte
    ].copy()

    # Excluir MERMA para que cartilla y reporte sean consistentes
    sub_sin_merma = sub_global[sub_global["ESTADO"] != "MERMA"].copy()

    # Stock neto por SKU (sin MERMA)
    neto_sku = (
        sub_sin_merma
        .groupby("SKU MASEF")["TOTAL UNIT"]
        .sum()
    )

    # Total neto en stock (solo SKUs positivos, sin MERMA)
    total_neto = int(neto_sku[neto_sku > 0].sum())

    # SKUs con stock real
    skus_positivos = neto_sku[neto_sku > 0].index

    # Métricas por estado (ya sin MERMA)
    df_positivos = sub_sin_merma[
        sub_sin_merma["SKU MASEF"].isin(skus_positivos)
    ].copy()

    por_estado = (
        df_positivos
        .groupby("ESTADO")["TOTAL UNIT"]
        .sum()
    )

    por_estado = por_estado[por_estado > 0]

    # ── Métricas ──
    cols_metrics = st.columns(1 + len(por_estado))

    cols_metrics[0].metric(
        "Total en stock",
        f"{total_neto:,}"
    )

    for i, (estado, unidades) in enumerate(por_estado.items()):

        cols_metrics[1 + i].metric(
            estado,
            f"{int(unidades):,}"
        )

    st.divider()

    # ─────────────────────────────────────────────────────────────
    # DETALLE DE STOCK CORREGIDO
    # ─────────────────────────────────────────────────────────────

    # Pasamos df sin MERMA: así el neto interno de calcular_stock
    # y el total de la cartilla usan exactamente los mismos datos
    stock_df = calcular_stock(
        df[df["ESTADO"] != "MERMA"],
        fecha_corte
    )

    # ── Buscar ──
    if buscar:

        mask = (
            stock_df["SKU MASEF"].str.contains(
                buscar, case=False, na=False
            )
            |
            stock_df["DESCRIPTION"].str.contains(
                buscar, case=False, na=False
            )
        )

        stock_df = stock_df[mask]

    # ── Filtro Estado ──
    if f_estado != "Todos":

        stock_df = stock_df[
            stock_df["ESTADO"] == f_estado
        ]

    # ── Tabla ──
    st.markdown(
        f"**Detalle de stock** — {len(stock_df)} registros"
    )

    # ── Merge con PACKINGLIST para traer CASE PACK IN (presentación) ──
    pk_presentacion = (
        packing_df[["CTN", col_sku, "CASE PACK IN"]]
        .copy()
        .rename(columns={col_sku: "SKU MASEF"})
    )
    pk_presentacion["CTN"]      = pk_presentacion["CTN"].astype(str).str.strip()
    pk_presentacion["SKU MASEF"]= pk_presentacion["SKU MASEF"].astype(str).str.strip()
    pk_presentacion["CASE PACK IN"] = pd.to_numeric(
        pk_presentacion["CASE PACK IN"], errors="coerce"
    )
    pk_presentacion = pk_presentacion.drop_duplicates(subset=["CTN", "SKU MASEF"])

    stock_df = stock_df.merge(
        pk_presentacion,
        on=["CTN", "SKU MASEF"],
        how="left"
    )

    display = stock_df[[
        "SKU MASEF",
        "DESCRIPTION",
        "CTN",
        "ESTADO",
        "FECHA VCTO",
        "CASE PACK IN",
        "Stock",
    ]].rename(columns={
        "SKU MASEF":    "SKU",
        "DESCRIPTION":  "Descripción",
        "FECHA VCTO":   "Vencimiento",
        "CASE PACK IN": "Presentación",
        "Stock":        "Unidades en Stock",
    })

    max_stock = int(stock_df["Stock"].max()) if len(stock_df) else 1

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Unidades en Stock": st.column_config.ProgressColumn(
                "Unidades en Stock",
                min_value=0,
                max_value=max_stock,
                format="%d"
            )
        }
    )

    botones_descarga(display, "stock")

# ══════════════════════════════════════════════════════════════════════════════
# VISTA: TRAZABILIDAD
# ══════════════════════════════════════════════════════════════════════════════

elif vista == "🔍  Trazabilidad":

    st.markdown("## 🔍 Reporte de Trazabilidad")

    st.caption(
        "Base completa de movimientos."
    )

    with st.form("form_trazabilidad"):

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            contenedores = ["Todos"] + sorted(
                df["CTN"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            f_ctn = st.selectbox("📦 Contenedor", contenedores)

        with col2:

            skus = ["Todos"] + sorted(
                df["SKU MASEF"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            f_sku = st.selectbox("🏷️ SKU", skus)

        with col3:

            fecha_desde = st.date_input(
                "📅 Desde",
                value=df["FECHA"].min().date()
            )

        with col4:

            fecha_hasta = st.date_input(
                "📅 Hasta",
                value=date.today()
            )

        st.form_submit_button(
            "🔍 Buscar",
            use_container_width=True
        )

    traz = df.copy()

    if f_ctn != "Todos":
        traz = traz[traz["CTN"] == f_ctn]

    if f_sku != "Todos":
        traz = traz[traz["SKU MASEF"] == f_sku]

    traz = traz[
        (traz["FECHA"].dt.date >= fecha_desde)
        &
        (traz["FECHA"].dt.date <= fecha_hasta)
    ]

    traz = traz.sort_values("FECHA", ascending=False)

    m1, m2, m3 = st.columns(3)

    m1.metric("Movimientos", f"{len(traz):,}")
    m2.metric("SKUs",        f"{traz['SKU MASEF'].nunique():,}")
    m3.metric("CTNs",        f"{traz['CTN'].nunique():,}")

    st.divider()

    traz_display = traz.copy()

    for col in traz_display.columns:

        if "FECHA" in col.upper():

            try:
                traz_display[col] = pd.to_datetime(
                    traz_display[col], errors="coerce"
                ).dt.strftime("%Y-%m-%d")
            except:
                pass

    st.dataframe(
        traz_display,
        use_container_width=True,
        hide_index=True
    )

    botones_descarga(traz_display, "trazabilidad")

# ══════════════════════════════════════════════════════════════════════════════
# VISTA: PACKING LIST
# ══════════════════════════════════════════════════════════════════════════════

elif vista == "📦  Packing List":

    st.markdown("## 📦 Reporte Packing List")

    st.caption(
        "Base completa de la hoja PACKINGLIST."
    )

    with st.form("form_packing"):

        col1, col2 = st.columns(2)

        with col1:

            columnas_ctn = [
                c for c in packing_df.columns
                if "CTN" in c.upper() or "CONTENEDOR" in c.upper()
            ]

            col_ctn = columnas_ctn[0] if columnas_ctn else packing_df.columns[0]

            ctns = ["Todos"] + sorted(
                packing_df[col_ctn]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            f_ctn = st.selectbox("📦 Contenedor", ctns)

        with col2:

            columnas_sku = [
                c for c in packing_df.columns
                if "SKU" in c.upper()
            ]

            col_sku = columnas_sku[0] if columnas_sku else packing_df.columns[0]

            skus = ["Todos"] + sorted(
                packing_df[col_sku]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            f_sku = st.selectbox("🏷️ SKU", skus)

        st.form_submit_button(
            "🔍 Buscar",
            use_container_width=True
        )

    pk = packing_df.copy()

    if f_ctn != "Todos":
        pk = pk[pk[col_ctn].astype(str) == str(f_ctn)]

    if f_sku != "Todos":
        pk = pk[pk[col_sku].astype(str) == str(f_sku)]

    m1, m2 = st.columns(2)

    m1.metric("Registros", f"{len(pk):,}")
    m2.metric("SKUs",      f"{pk[col_sku].nunique():,}")

    st.divider()

    st.dataframe(pk, use_container_width=True, hide_index=True)

    botones_descarga(pk, "packinglist")

# ══════════════════════════════════════════════════════════════════════════════
# VISTA: MERMA
# ══════════════════════════════════════════════════════════════════════════════

elif vista == "⚠️  Merma":

    st.markdown("## ⚠️ Reporte de Merma")

    st.caption(
        "Stock correspondiente únicamente a productos en estado MERMA."
    )

    # ── Filtros ──
    with st.form("form_merma"):

        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:

            fecha_corte = st.date_input(
                "📅 Fecha de corte",
                value=date.today()
            )

        with col2:

            buscar = st.text_input(
                "🔎 Buscar SKU o descripción"
            )

        with col3:

            st.write("")
            st.write("")

            st.form_submit_button(
                "🔍 Buscar",
                use_container_width=True
            )

    # ── SOLO MERMA ──
    merma_df = calcular_stock(
        df[df["ESTADO"] == "MERMA"],
        fecha_corte
    )

    if buscar:

        mask = (
            merma_df["SKU MASEF"].str.contains(
                buscar, case=False, na=False
            )
            |
            merma_df["DESCRIPTION"].str.contains(
                buscar, case=False, na=False
            )
        )

        merma_df = merma_df[mask]

    total_merma = int(merma_df["Stock"].sum()) if len(merma_df) else 0

    m1, m2 = st.columns(2)

    m1.metric("Total merma",    f"{total_merma:,}")
    m2.metric("SKUs con merma", f"{len(merma_df):,}")

    st.divider()

    display = merma_df[[
        "SKU MASEF",
        "DESCRIPTION",
        "CTN",
        "ESTADO",
        "FECHA VCTO",
        "Stock"
    ]].rename(columns={
        "SKU MASEF":   "SKU",
        "DESCRIPTION": "Descripción",
        "FECHA VCTO":  "Vencimiento",
        "Stock":       "Unidades"
    })

    max_merma = int(merma_df["Stock"].max()) if len(merma_df) else 1

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Unidades": st.column_config.ProgressColumn(
                "Unidades",
                min_value=0,
                max_value=max_merma,
                format="%d"
            )
        }
    )

    botones_descarga(display, "merma")


# ══════════════════════════════════════════════════════════════════════════════
# VISTA: DESPACHOS POR INGRESO
# ══════════════════════════════════════════════════════════════════════════════

elif vista == "🚚  Despachos por Ingreso":

    st.markdown("## 🚚 Despachos por Ingreso")

    st.caption(
        "Para cada lote ingresado, muestra sus despachos por guía y fecha, más el stock resultante."
    )

    # ── Filtros ──
    with st.form("form_despachos"):

        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

        with col1:
            fecha_corte = st.date_input(
                "📅 Fecha de corte",
                value=date.today(),
                min_value=df["FECHA"].min().date(),
                max_value=date.today()
            )

        with col2:
            buscar = st.text_input(
                "🔎 Buscar SKU o descripción",
                placeholder="ej: NUTELLA"
            )

        with col3:
            estados_opts = ["Todos"] + sorted(
                df["ESTADO"].dropna().unique().tolist()
            )
            f_estado = st.selectbox("🏷️ Estado", estados_opts)

        with col4:
            st.write("")
            st.write("")
            st.form_submit_button("🔍 Buscar", use_container_width=True)

    # ── Preparar datos hasta fecha de corte ──
    sub = df[df["FECHA"].dt.date <= fecha_corte].copy()

    sub["SKU MASEF"]   = sub["SKU MASEF"].astype(str).str.strip()
    sub["CTN"]         = sub["CTN"].astype(str).str.strip()
    sub["ESTADO"]      = sub["ESTADO"].astype(str).str.strip()
    sub["DESCRIPTION"] = sub["DESCRIPTION"].astype(str).str.strip()
    sub["GUIA"]        = sub["GUIA"].astype(str).str.strip()

    # ── Clave de agrupación según estado ──
    def get_key(row):
        if row["ESTADO"] == "GENERAL":
            return (row["SKU MASEF"], row["CTN"], row["ESTADO"], "")
        else:
            vcto = pd.to_datetime(row["FECHA VCTO"], errors="coerce")
            vcto_str = vcto.strftime("%Y-%m-%d") if not pd.isna(vcto) else ""
            return (row["SKU MASEF"], row["CTN"], row["ESTADO"], vcto_str)

    sub["_KEY"] = sub.apply(get_key, axis=1)

    # ── Descripción por SKU ──
    desc_map = (
        sub[["SKU MASEF", "DESCRIPTION"]]
        .query("DESCRIPTION != '' and DESCRIPTION != 'nan'")
        .drop_duplicates(subset=["SKU MASEF"])
        .set_index("SKU MASEF")["DESCRIPTION"]
    )

    # ── Fecha de ingreso por KEY: primera fecha con TOTAL UNIT > 0 ──
    ingresos = sub[sub["TOTAL UNIT"] > 0].copy()
    fecha_ingreso_map = (
        ingresos
        .sort_values("FECHA")
        .groupby("_KEY")["FECHA"]
        .first()
        .dt.strftime("%Y-%m-%d")
    )

    # ── Salidas: movimientos con TOTAL UNIT < 0 ──
    salidas = sub[sub["TOTAL UNIT"] < 0].copy()
    salidas["FECHA_STR"] = salidas["FECHA"].dt.strftime("%Y-%m-%d")

    # Columna multiindex: (FECHA DESPACHO, GUIA)
    salidas["_COL"] = list(zip(salidas["FECHA_STR"], salidas["GUIA"]))

    # ── Pivot: filas = KEY, columnas = (FECHA, GUIA), valores = suma TOTAL UNIT ──
    if len(salidas) > 0:
        pivot = (
            salidas
            .groupby(["_KEY", "_COL"])["TOTAL UNIT"]
            .sum()
            .unstack("_COL")
            .fillna(0)
            .astype(int)
        )
        # Ordenar columnas por fecha
        pivot = pivot.reindex(sorted(pivot.columns, key=lambda x: x[0]), axis=1)
    else:
        pivot = pd.DataFrame()

    # ── Stock neto por KEY ──
    stock_neto = (
        sub
        .groupby("_KEY")["TOTAL UNIT"]
        .sum()
        .rename("Stock")
    )

    # ── Ingreso total por KEY ──
    ingreso_total = (
        ingresos
        .groupby("_KEY")["TOTAL UNIT"]
        .sum()
        .rename("Ingreso")
    )

    # ── Construir tabla base con todas las KEYs ──
    todas_keys = stock_neto.index.union(ingreso_total.index)
    base = pd.DataFrame(index=todas_keys)
    base.index.name = "_KEY"
    base = base.join(ingreso_total).join(stock_neto).fillna(0)
    base["Ingreso"] = base["Ingreso"].astype(int)
    base["Stock"]   = base["Stock"].astype(int)

    # Solo KEYs con stock o ingreso
    base = base[base["Ingreso"] > 0]

    # ── Unir pivot de salidas ──
    if len(pivot) > 0:
        tabla = base.join(pivot, how="left").fillna(0)
    else:
        tabla = base.copy()

    # ── Agregar columnas fijas ──
    tabla = tabla.reset_index()
    tabla["SKU MASEF"]      = tabla["_KEY"].apply(lambda x: x[0])
    tabla["CTN"]            = tabla["_KEY"].apply(lambda x: x[1])
    tabla["ESTADO"]         = tabla["_KEY"].apply(lambda x: x[2])
    tabla["FECHA VCTO"]     = tabla["_KEY"].apply(lambda x: x[3])
    tabla["Descripción"]    = tabla["SKU MASEF"].map(desc_map).fillna("")
    tabla["Fecha Ingreso"]  = tabla["_KEY"].map(fecha_ingreso_map).fillna("")

    # ── Filtros de búsqueda ──
    if buscar:
        mask = (
            tabla["SKU MASEF"].str.contains(buscar, case=False, na=False)
            | tabla["Descripción"].str.contains(buscar, case=False, na=False)
        )
        tabla = tabla[mask]

    if f_estado != "Todos":
        tabla = tabla[tabla["ESTADO"] == f_estado]

    # ── Columnas de despacho (multiindex) ──
    cols_despacho = [c for c in tabla.columns if isinstance(c, tuple)]

    # ── Armar DataFrame final para mostrar ──
    cols_fijas = ["SKU MASEF", "Descripción", "CTN", "ESTADO", "FECHA VCTO", "Fecha Ingreso", "Ingreso"]
    cols_stock = ["Stock"]

    df_final = tabla[cols_fijas + cols_despacho + cols_stock].copy()

    # Renombrar columnas fijas
    df_final = df_final.rename(columns={
        "SKU MASEF":     "SKU",
        "FECHA VCTO":    "Vencimiento",
        "Fecha Ingreso": "F. Ingreso",
    })

    # ── Convertir a MultiIndex en columnas para display ──
    fixed_cols   = ["SKU", "Descripción", "CTN", "ESTADO", "Vencimiento", "F. Ingreso", "Ingreso"]
    despacho_tuples = cols_despacho  # ya son (fecha, guia)
    stock_tuple  = [("", "Stock")]

    new_cols = (
        [("", c) for c in fixed_cols]
        + [("Despacho  " + t[0], t[1]) for t in despacho_tuples]
        + stock_tuple
    )

    df_final.columns = pd.MultiIndex.from_tuples(new_cols)

    # ── Métricas ──
    m1, m2, m3 = st.columns(3)
    m1.metric("Lotes",         f"{len(df_final):,}")
    m2.metric("Total Ingreso", f"{int(tabla['Ingreso'].sum()):,}" if len(tabla) else "0")
    m3.metric("Stock actual",  f"{int(tabla['Stock'].sum()):,}"   if len(tabla) else "0")

    st.divider()

    st.markdown(f"**{len(df_final)} lotes encontrados**")

    # ── Nota sobre columnas multiindex ──
    st.caption("Las columnas de despacho muestran: Fecha despacho (nivel 1) → Guía (nivel 2) → Unidades salidas (negativo = salida).")

    # Streamlit no renderiza MultiIndex bien en st.dataframe,
    # así que aplanamos los headers para display
    df_display = df_final.copy()
    df_display.columns = [
        b if not a.strip() else (f"{a.strip()} | {b}" if b.strip() else a.strip())
        for a, b in df_display.columns
    ]

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
    )

    # ── Exportar ──
    botones_descarga(df_display, "despachos_por_ingreso")
