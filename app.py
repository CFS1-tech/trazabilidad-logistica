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
        st.secrets["gcp_service_account"], scopes=scopes,
    )
    return gspread.authorize(creds)

@st.cache_data(ttl=300)
def cargar_datos() -> pd.DataFrame:
    client = get_client()
    sh  = client.open_by_key(st.secrets["spreadsheet_id"])
    ws  = sh.worksheet(SHEET_NAME)
    df  = pd.DataFrame(ws.get_all_records())
    # Parsear fechas — el Sheet usa formato D/M/YYYY
    def parse_fecha(col):
        parsed = pd.to_datetime(col, dayfirst=True, errors="coerce")
        # Para fechas que fallaron, intentar formato alternativo
        mask = parsed.isna() & col.astype(str).str.strip().ne("")
        if mask.any():
            parsed[mask] = pd.to_datetime(col[mask], format="%Y-%m-%d", errors="coerce")
        return parsed

    df["FECHA"]      = parse_fecha(df["FECHA"].astype(str))
    df["FECHA VCTO"] = parse_fecha(df["FECHA VCTO"].astype(str))
    df["TOTAL UNIT"] = pd.to_numeric(df["TOTAL UNIT"], errors="coerce").fillna(0).astype(int)
    df["SKU MASEF"]  = df["SKU MASEF"].astype(str)
    df["CTN"]        = df["CTN"].astype(str)
    return df.dropna(subset=["FECHA"])

def calcular_stock(df: pd.DataFrame, fecha_corte) -> pd.DataFrame:
    corte = pd.to_datetime(fecha_corte)
    sub   = df[df["FECHA"].dt.date <= corte.date()].copy()
    stk_sku = (
        sub.groupby(["SKU MASEF", "DESCRIPTION"])["TOTAL UNIT"]
        .sum().rename("Stock").reset_index()
    )
    ultima_info = (
        sub.sort_values("FECHA")
        .groupby(["SKU MASEF", "DESCRIPTION"])[["CTN", "ESTADO", "FECHA VCTO"]]
        .last().reset_index()
    )
    result = stk_sku.merge(ultima_info, on=["SKU MASEF", "DESCRIPTION"], how="left")
    result["Stock"] = result["Stock"].astype(int)
    result = result[result["Stock"] != 0].sort_values("Stock", ascending=False)
    result["FECHA VCTO"] = pd.to_datetime(result["FECHA VCTO"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    return result.reset_index(drop=True)

def to_excel(df_export: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Reporte")
    return buf.getvalue()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/warehouse.png", width=60)
    st.title("WMS MASEF")
    st.caption("Warehouse Management System")
    st.divider()
    vista = st.radio("Reportes", ["📦 Stock", "🔍 Trazabilidad"], label_visibility="collapsed")
    st.divider()
    if st.button("🔄 Recargar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Última carga: {datetime.now().strftime('%H:%M:%S')}")

# ── Carga de datos ────────────────────────────────────────────────────────────
try:
    df = cargar_datos()
except Exception as e:
    st.error(f"❌ Error conectando a Google Sheets: {e}")
    st.stop()


# DEBUG temporal
with st.expander("🔧 Debug info"):
    st.write("Filas leídas:", len(df))
    st.write("Suma TOTAL UNIT:", df["TOTAL UNIT"].sum())
    st.write("Fechas nulas:", df["FECHA"].isna().sum())
    st.write("Muestra FECHA (primeras 3):", df["FECHA"].head(3).tolist())
# ══════════════════════════════════════════════════════════════════════════════
# VISTA: STOCK
# ══════════════════════════════════════════════════════════════════════════════
if vista == "📦 Stock":
    st.header("📦 Reporte de Stock")
    st.caption("Stock acumulado desde el inicio hasta la fecha de corte seleccionada.")

    # Filtros + botón buscar
    with st.form("form_stock"):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            fecha_corte = st.date_input(
                "📅 Fecha de corte",
                value=date.today(),
                min_value=df["FECHA"].min().date(),
                max_value=date.today(),
            )
        with col2:
            buscar = st.text_input("🔎 Buscar SKU o descripción", placeholder="ej: NUTELLA o 1030013")
        with col3:
            st.write("")
            st.write("")
            buscar_btn = st.form_submit_button("🔍 Buscar", use_container_width=True)

    # Calcular stock
    stock_df = calcular_stock(df, fecha_corte)
    if buscar:
        mask = (
            stock_df["SKU MASEF"].str.contains(buscar, case=False) |
            stock_df["DESCRIPTION"].str.contains(buscar, case=False)
        )
        stock_df = stock_df[mask]

    # Métricas
    sub_corte      = df[df["FECHA"].dt.date <= pd.to_datetime(fecha_corte).date()]
    stock_neto     = int(stock_df["Stock"].sum())
    total_entradas = int(sub_corte[sub_corte["TOTAL UNIT"] > 0]["TOTAL UNIT"].sum())
    total_salidas  = int(sub_corte[sub_corte["TOTAL UNIT"] < 0]["TOTAL UNIT"].sum() * -1)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("SKUs con stock",  stock_df["SKU MASEF"].nunique())
    m2.metric("Total unidades",  f"{stock_neto:,}")
    m3.metric("Entradas acum.",  f"{total_entradas:,}")
    m4.metric("Salidas acum.",   f"{total_salidas:,}")

    st.divider()

    # Gráfico top 10
    top10 = stock_df.head(10)
    if not top10.empty:
        fig = px.bar(
            top10, x="Stock", y="DESCRIPTION", orientation="h",
            title="Top 10 SKUs por stock",
            color="Stock", color_continuous_scale="Blues",
            labels={"DESCRIPTION": "", "Stock": "Unidades"},
        )
        fig.update_layout(height=350, showlegend=False,
                          yaxis={"categoryorder": "total ascending"},
                          coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # Tabla
    st.subheader(f"Detalle de stock ({len(stock_df)} registros)")
    display = stock_df[["SKU MASEF", "DESCRIPTION", "CTN", "ESTADO", "FECHA VCTO", "Stock"]].rename(columns={
        "SKU MASEF":   "SKU",
        "DESCRIPTION": "Descripción",
        "FECHA VCTO":  "Vencimiento",
        "Stock":       "Unidades en Stock",
    })
    max_stock = int(stock_df["Stock"].max()) if len(stock_df) else 1
    st.dataframe(
        display, use_container_width=True, hide_index=True,
        column_config={
            "Unidades en Stock": st.column_config.ProgressColumn(
                "Unidades en Stock", min_value=0, max_value=max_stock, format="%d",
            ),
        },
    )

    # Descargas
    col_csv, col_xlsx = st.columns(2)
    with col_csv:
        st.download_button(
            "⬇️ Exportar CSV",
            display.to_csv(index=False).encode("utf-8"),
            f"stock_{fecha_corte}.csv",
            "text/csv",
            use_container_width=True,
        )
    with col_xlsx:
        st.download_button(
            "📊 Exportar Excel",
            to_excel(display),
            f"stock_{fecha_corte}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# VISTA: TRAZABILIDAD
# ══════════════════════════════════════════════════════════════════════════════
elif vista == "🔍 Trazabilidad":
    st.header("🔍 Reporte de Trazabilidad")
    st.caption("Historial de movimientos filtrado por contenedor, SKU y tipo.")

    # Filtros + botón buscar
    with st.form("form_traz"):
        col1, col2, col3 = st.columns(3)
        with col1:
            ctns  = ["Todos"] + sorted(df["CTN"].dropna().unique().tolist())
            f_ctn = st.selectbox("📦 Contenedor (CTN)", ctns)
        with col2:
            skus  = ["Todos"] + sorted(df["SKU MASEF"].dropna().unique().tolist())
            f_sku = st.selectbox("🏷️ SKU", skus)
        with col3:
            tipos  = ["Todos"] + sorted(df["TIPO DE MOVIMIENTO"].dropna().unique().tolist())
            f_tipo = st.selectbox("🔄 Tipo de movimiento", tipos)

        col4, col5, col6 = st.columns([2, 2, 1])
        with col4:
            f_desde = st.date_input("📅 Desde", value=df["FECHA"].min().date())
        with col5:
            f_hasta = st.date_input("📅 Hasta", value=date.today())
        with col6:
            st.write("")
            st.write("")
            filtrar_btn = st.form_submit_button("🔍 Buscar", use_container_width=True)

    # Aplicar filtros
    result = df.copy()

    def clasificar(tipo):
        if tipo in MOVIMIENTOS_ENTRADA: return "ENTRADA"
        elif tipo in MOVIMIENTOS_SALIDA: return "SALIDA"
        return tipo

    result["CLASE"] = result["TIPO DE MOVIMIENTO"].apply(clasificar)
    if f_ctn  != "Todos": result = result[result["CTN"] == f_ctn]
    if f_sku  != "Todos": result = result[result["SKU MASEF"] == f_sku]
    if f_tipo != "Todos": result = result[result["TIPO DE MOVIMIENTO"] == f_tipo]
    result = result[
        (result["FECHA"] >= pd.to_datetime(f_desde)) &
        (result["FECHA"] <= pd.to_datetime(f_hasta))
    ].sort_values("FECHA", ascending=False)

    # Métricas
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Movimientos",    len(result))
    m2.metric("SKUs únicos",    result["SKU MASEF"].nunique())
    m3.metric("CTNs únicos",    result["CTN"].nunique())
    m4.metric("Total unidades", f"{result['TOTAL UNIT'].sum():,}")

    st.divider()

    # Gráfico por tipo
    if not result.empty:
        resumen = result.groupby("TIPO DE MOVIMIENTO")["TOTAL UNIT"].sum().reset_index()
        fig2 = px.bar(
            resumen, x="TIPO DE MOVIMIENTO", y="TOTAL UNIT",
            title="Unidades por tipo de movimiento",
            color="TIPO DE MOVIMIENTO",
            color_discrete_map={
                "INGRESO": "#2196F3", "SALIDA": "#F44336",
                "AJUSTE-IN": "#4CAF50", "AJUSTE-OUT": "#FF9800", "MERMA": "#9C27B0",
            },
            labels={"TOTAL UNIT": "Unidades", "TIPO DE MOVIMIENTO": ""},
        )
        fig2.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    # Tabla
    st.subheader(f"Movimientos ({len(result)} registros)")
    cols_mostrar = ["FECHA", "CTN", "SKU MASEF", "DESCRIPTION", "TIPO DE MOVIMIENTO", "CLASE", "TOTAL UNIT", "ESTADO", "FECHA VCTO"]
    result_display = result[cols_mostrar].copy()
    result_display["FECHA"]     = result_display["FECHA"].dt.strftime("%Y-%m-%d")
    result_display["FECHA VCTO"] = result_display["FECHA VCTO"].dt.strftime("%Y-%m-%d").where(result_display["FECHA VCTO"].notna(), "")

    traz_renamed = result_display.rename(columns={
        "SKU MASEF":          "SKU",
        "DESCRIPTION":        "Descripción",
        "TIPO DE MOVIMIENTO": "Tipo",
        "CLASE":              "Entrada/Salida",
        "TOTAL UNIT":         "Unidades",
        "FECHA VCTO":         "Vencimiento",
    })
    st.dataframe(traz_renamed, use_container_width=True, hide_index=True)

    # Descargas
    col_csv, col_xlsx = st.columns(2)
    with col_csv:
        st.download_button(
            "⬇️ Exportar CSV",
            result_display.to_csv(index=False).encode("utf-8"),
            f"trazabilidad_{f_desde}_{f_hasta}.csv",
            "text/csv",
            use_container_width=True,
        )
    with col_xlsx:
        st.download_button(
            "📊 Exportar Excel",
            to_excel(traz_renamed),
            f"trazabilidad_{f_desde}_{f_hasta}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
