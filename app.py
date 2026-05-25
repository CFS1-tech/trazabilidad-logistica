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
        st.secrets["gcp_service_account"], scopes=scopes,
    )
    return gspread.authorize(creds)

@st.cache_data(ttl=300)
def cargar_datos() -> pd.DataFrame:
    client = get_client()
    sh  = client.open_by_key(st.secrets["spreadsheet_id"])
    ws  = sh.worksheet(SHEET_NAME)
    df  = pd.DataFrame(ws.get_all_records())

    def parse_fecha(col):
        parsed = pd.to_datetime(col, dayfirst=True, errors="coerce")
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

def calcular_stock(df: pd.DataFrame, fecha_corte, excluir_tipos=None) -> pd.DataFrame:
    """Calcula stock neto por SKU hasta fecha_corte, excluyendo tipos indicados."""
    corte = pd.to_datetime(fecha_corte)
    sub   = df[df["FECHA"].dt.date <= corte.date()].copy()
    if excluir_tipos:
        sub = sub[~sub["TIPO DE MOVIMIENTO"].isin(excluir_tipos)]
    stk = sub.groupby(["SKU MASEF", "DESCRIPTION"])["TOTAL UNIT"].sum().rename("Stock").reset_index()
    ultima = (
        sub.sort_values("FECHA")
        .groupby(["SKU MASEF", "DESCRIPTION"])[["CTN", "ESTADO", "FECHA VCTO"]]
        .last().reset_index()
    )
    result = stk.merge(ultima, on=["SKU MASEF", "DESCRIPTION"], how="left")
    result["Stock"] = result["Stock"].astype(int)
    result = result[result["Stock"] != 0].sort_values("Stock", ascending=False)
    result["FECHA VCTO"] = pd.to_datetime(result["FECHA VCTO"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    return result.reset_index(drop=True)

def to_excel(df_export: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Reporte")
    return buf.getvalue()

def botones_descarga(df_display, nombre):
    col_csv, col_xlsx = st.columns(2)
    with col_csv:
        st.download_button("⬇️ Exportar CSV", df_display.to_csv(index=False).encode("utf-8"),
            f"{nombre}_{date.today()}.csv", "text/csv", use_container_width=True)
    with col_xlsx:
        st.download_button("📊 Exportar Excel", to_excel(df_display),
            f"{nombre}_{date.today()}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📦 WMS MASEF")
    st.markdown("<small style='color:#64748b'>Warehouse Management System</small>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<small style='color:#64748b;text-transform:uppercase;letter-spacing:.08em'>REPORTES</small>", unsafe_allow_html=True)
    vista = st.radio("", [
        "📦  Stock",
        "🔍  Trazabilidad",
        "🚚  Despachos",
        "⚠️  Merma",
    ], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("<small style='color:#64748b;text-transform:uppercase;letter-spacing:.08em'>SISTEMA</small>", unsafe_allow_html=True)
    if st.button("🔄  Recargar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown(f"<small style='color:#4a5568'>Última carga: {datetime.now().strftime('%H:%M:%S')}</small>", unsafe_allow_html=True)

# ── Carga de datos ────────────────────────────────────────────────────────────
try:
    df = cargar_datos()
except Exception as e:
    st.error(f"❌ Error conectando a Google Sheets: {e}")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# VISTA: STOCK (sin merma)
# ══════════════════════════════════════════════════════════════════════════════
if vista == "📦  Stock":
    st.markdown("## 📦 Reporte de Stock")
    st.caption("Stock acumulado hasta la fecha de corte. No incluye merma.")

    # ── Métricas globales arriba ──
    # Stock = excluir filas con ESTADO='MERMA'
    df_sin_merma   = df[df["ESTADO"] != "MERMA"]
    sub_global     = df_sin_merma[df_sin_merma["FECHA"].dt.date <= date.today()]
    total_neto     = int(sub_global["TOTAL UNIT"].sum())
    total_entradas = int(sub_global[sub_global["TOTAL UNIT"] > 0]["TOTAL UNIT"].sum())
    total_salidas  = int(sub_global[sub_global["TOTAL UNIT"] < 0]["TOTAL UNIT"].sum() * -1)

    # Stock neto por estado (sin MERMA, sin estados en 0)
    por_estado = sub_global.groupby("ESTADO")["TOTAL UNIT"].sum()
    por_estado = por_estado[por_estado != 0]

    cols_metrics = st.columns(3 + len(por_estado))
    cols_metrics[0].metric("Total en stock",  f"{total_neto:,}")
    cols_metrics[1].metric("Entradas acum.",  f"{total_entradas:,}")
    cols_metrics[2].metric("Salidas acum.",   f"{total_salidas:,}")
    for i, (estado, unidades) in enumerate(por_estado.items()):
        cols_metrics[3 + i].metric(estado, f"{int(unidades):,}")

    st.divider()

    # ── Filtros ──
    with st.form("form_stock"):
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        with col1:
            fecha_corte = st.date_input("📅 Fecha de corte", value=date.today(),
                min_value=df["FECHA"].min().date(), max_value=date.today())
        with col2:
            buscar = st.text_input("🔎 Buscar SKU o descripción", placeholder="ej: NUTELLA")
        with col3:
            estados_opts = ["Todos"] + sorted(df["ESTADO"].dropna().unique().tolist())
            f_estado = st.selectbox("🏷️ Estado", estados_opts)
        with col4:
            st.write(""); st.write("")
            st.form_submit_button("🔍 Buscar", use_container_width=True)

    # ── Calcular y filtrar ──
    stock_df = calcular_stock(df[df["ESTADO"] != "MERMA"], fecha_corte)
    if buscar:
        mask = (stock_df["SKU MASEF"].str.contains(buscar, case=False) |
                stock_df["DESCRIPTION"].str.contains(buscar, case=False))
        stock_df = stock_df[mask]
    if f_estado != "Todos":
        stock_df = stock_df[stock_df["ESTADO"] == f_estado]

    # ── Tabla ──
    st.markdown(f"**Detalle de stock** — {len(stock_df)} SKUs")
    display = stock_df[["SKU MASEF", "DESCRIPTION", "CTN", "ESTADO", "FECHA VCTO", "Stock"]].rename(columns={
        "SKU MASEF": "SKU", "DESCRIPTION": "Descripción",
        "FECHA VCTO": "Vencimiento", "Stock": "Unidades en Stock",
    })
    max_stock = int(stock_df[stock_df["Stock"] > 0]["Stock"].max()) if len(stock_df) else 1
    st.dataframe(display, use_container_width=True, hide_index=True,
        column_config={"Unidades en Stock": st.column_config.ProgressColumn(
            "Unidades en Stock", min_value=0, max_value=max_stock, format="%d")})
    botones_descarga(display, "stock")

# ══════════════════════════════════════════════════════════════════════════════
# VISTA: TRAZABILIDAD
# ══════════════════════════════════════════════════════════════════════════════
elif vista == "🔍  Trazabilidad":
    st.markdown("## 🔍 Reporte de Trazabilidad")
    st.caption("Historial completo de movimientos.")

    # ── Métricas globales arriba ──
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total movimientos", f"{len(df):,}")
    m2.metric("SKUs únicos",       f"{df['SKU MASEF'].nunique():,}")
    m3.metric("CTNs únicos",       f"{df['CTN'].nunique():,}")
    m4.metric("Tipos movimiento",  f"{df['TIPO DE MOVIMIENTO'].nunique():,}")

    st.divider()

    # ── Filtros ──
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
            st.write(""); st.write("")
            st.form_submit_button("🔍 Buscar", use_container_width=True)

    result = df.copy()
    result["CLASE"] = result["TIPO DE MOVIMIENTO"].apply(
        lambda t: "ENTRADA" if t in MOVIMIENTOS_ENTRADA else "SALIDA")
    if f_ctn  != "Todos": result = result[result["CTN"] == f_ctn]
    if f_sku  != "Todos": result = result[result["SKU MASEF"] == f_sku]
    if f_tipo != "Todos": result = result[result["TIPO DE MOVIMIENTO"] == f_tipo]
    result = result[(result["FECHA"].dt.date >= f_desde) &
                    (result["FECHA"].dt.date <= f_hasta)].sort_values("FECHA", ascending=False)

    st.markdown(f"**Movimientos** — {len(result)} registros")
    cols_t = ["FECHA", "CTN", "SKU MASEF", "DESCRIPTION", "TIPO DE MOVIMIENTO",
              "CLASE", "TOTAL UNIT", "ESTADO", "FECHA VCTO"]
    rd = result[cols_t].copy()
    rd["FECHA"]      = rd["FECHA"].dt.strftime("%Y-%m-%d")
    rd["FECHA VCTO"] = rd["FECHA VCTO"].dt.strftime("%Y-%m-%d").where(rd["FECHA VCTO"].notna(), "")
    rd = rd.rename(columns={"SKU MASEF": "SKU", "DESCRIPTION": "Descripción",
        "TIPO DE MOVIMIENTO": "Tipo", "CLASE": "Entrada/Salida",
        "TOTAL UNIT": "Unidades", "FECHA VCTO": "Vencimiento"})
    st.dataframe(rd, use_container_width=True, hide_index=True)
    botones_descarga(rd, "trazabilidad")

# ══════════════════════════════════════════════════════════════════════════════
# VISTA: DESPACHOS (solo SALIDA)
# ══════════════════════════════════════════════════════════════════════════════
elif vista == "🚚  Despachos":
    st.markdown("## 🚚 Reporte de Despachos")
    st.caption("Movimientos de tipo SALIDA — incluye guía y cliente.")

    despachos = df[df["TIPO DE MOVIMIENTO"] == "SALIDA"].copy()

    # ── Métricas arriba ──
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total despachos",  f"{len(despachos):,}")
    m2.metric("SKUs despachados", f"{despachos['SKU MASEF'].nunique():,}")
    m3.metric("CTNs únicos",      f"{despachos['CTN'].nunique():,}")
    m4.metric("Unidades totales", f"{int(despachos['TOTAL UNIT'].abs().sum()):,}")

    st.divider()

    # ── Filtros ──
    with st.form("form_despachos"):
        col1, col2, col3 = st.columns(3)
        with col1:
            skus_d = ["Todos"] + sorted(despachos["SKU MASEF"].dropna().unique().tolist())
            fd_sku = st.selectbox("🏷️ SKU", skus_d)
        with col2:
            ctns_d = ["Todos"] + sorted(despachos["CTN"].dropna().unique().tolist())
            fd_ctn = st.selectbox("📦 CTN", ctns_d)
        with col3:
            tiendas = ["Todos"] + sorted(despachos["Tienda"].dropna().unique().tolist())
            fd_tienda = st.selectbox("🏪 Cliente / Tienda", tiendas)

        col4, col5, col6 = st.columns([2, 2, 1])
        with col4:
            fd_desde = st.date_input("📅 Desde", value=despachos["FECHA"].min().date())
        with col5:
            fd_hasta = st.date_input("📅 Hasta", value=date.today())
        with col6:
            st.write(""); st.write("")
            st.form_submit_button("🔍 Buscar", use_container_width=True)

    res_d = despachos.copy()
    if fd_sku    != "Todos": res_d = res_d[res_d["SKU MASEF"] == fd_sku]
    if fd_ctn    != "Todos": res_d = res_d[res_d["CTN"] == fd_ctn]
    if fd_tienda != "Todos": res_d = res_d[res_d["Tienda"] == fd_tienda]
    res_d = res_d[(res_d["FECHA"].dt.date >= fd_desde) &
                  (res_d["FECHA"].dt.date <= fd_hasta)].sort_values("FECHA", ascending=False)

    st.markdown(f"**Despachos** — {len(res_d)} registros")
    cols_d = ["FECHA", "SKU MASEF", "DESCRIPTION", "CTN", "ESTADO",
              "TOTAL UNIT", "GUIA", "Tienda", "FECHA VCTO"]
    rd2 = res_d[cols_d].copy()
    rd2["FECHA"]      = rd2["FECHA"].dt.strftime("%Y-%m-%d")
    rd2["FECHA VCTO"] = rd2["FECHA VCTO"].dt.strftime("%Y-%m-%d").where(rd2["FECHA VCTO"].notna(), "")
    rd2["TOTAL UNIT"] = rd2["TOTAL UNIT"].abs()
    rd2 = rd2.rename(columns={"SKU MASEF": "SKU", "DESCRIPTION": "Descripción",
        "TOTAL UNIT": "Unidades", "Tienda": "Cliente", "FECHA VCTO": "Vencimiento"})
    st.dataframe(rd2, use_container_width=True, hide_index=True)
    botones_descarga(rd2, "despachos")

# ══════════════════════════════════════════════════════════════════════════════
# VISTA: MERMA
# ══════════════════════════════════════════════════════════════════════════════
elif vista == "⚠️  Merma":
    st.markdown("## ⚠️ Reporte de Merma")
    st.caption("Unidades dadas de baja por merma acumuladas hasta la fecha de corte.")

    merma_df = df[df["TIPO DE MOVIMIENTO"] == "MERMA"].copy()

    # ── Métricas arriba ──
    m1, m2, m3 = st.columns(3)
    m1.metric("Total registros merma", f"{len(merma_df):,}")
    m2.metric("SKUs afectados",        f"{merma_df['SKU MASEF'].nunique():,}")
    m3.metric("Unidades totales merma",f"{int(merma_df['TOTAL UNIT'].abs().sum()):,}")

    st.divider()

    # ── Filtros ──
    with st.form("form_merma"):
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        with col1:
            fm_fecha = st.date_input("📅 Fecha de corte", value=date.today(),
                min_value=merma_df["FECHA"].min().date(), max_value=date.today())
        with col2:
            skus_m = ["Todos"] + sorted(merma_df["SKU MASEF"].dropna().unique().tolist())
            fm_sku = st.selectbox("🏷️ SKU", skus_m)
        with col3:
            estados_m = ["Todos"] + sorted(merma_df["ESTADO"].dropna().unique().tolist())
            fm_estado = st.selectbox("🏷️ Estado", estados_m)
        with col4:
            st.write(""); st.write("")
            st.form_submit_button("🔍 Buscar", use_container_width=True)

    res_m = merma_df[merma_df["FECHA"].dt.date <= fm_fecha].copy()
    if fm_sku    != "Todos": res_m = res_m[res_m["SKU MASEF"] == fm_sku]
    if fm_estado != "Todos": res_m = res_m[res_m["ESTADO"] == fm_estado]
    res_m = res_m.sort_values("FECHA", ascending=False)

    # Resumen por SKU
    resumen_m = res_m.groupby(["SKU MASEF", "DESCRIPTION", "ESTADO"])["TOTAL UNIT"].sum().abs().reset_index()
    resumen_m = resumen_m.rename(columns={"SKU MASEF": "SKU", "DESCRIPTION": "Descripción",
        "TOTAL UNIT": "Unidades merma"})
    resumen_m = resumen_m.sort_values("Unidades merma", ascending=False)

    st.markdown(f"**Resumen por SKU** — {len(resumen_m)} productos")
    max_merma = int(resumen_m["Unidades merma"].max()) if len(resumen_m) else 1
    st.dataframe(resumen_m, use_container_width=True, hide_index=True,
        column_config={"Unidades merma": st.column_config.ProgressColumn(
            "Unidades merma", min_value=0, max_value=max_merma, format="%d",
            help="Total de unidades dadas de baja por merma")})

    st.markdown("**Detalle de movimientos**")
    cols_m = ["FECHA", "SKU MASEF", "DESCRIPTION", "CTN", "ESTADO", "TOTAL UNIT", "GUIA", "FECHA VCTO"]
    rd3 = res_m[cols_m].copy()
    rd3["FECHA"]      = rd3["FECHA"].dt.strftime("%Y-%m-%d")
    rd3["FECHA VCTO"] = rd3["FECHA VCTO"].dt.strftime("%Y-%m-%d").where(rd3["FECHA VCTO"].notna(), "")
    rd3["TOTAL UNIT"] = rd3["TOTAL UNIT"].abs()
    rd3 = rd3.rename(columns={"SKU MASEF": "SKU", "DESCRIPTION": "Descripción",
        "TOTAL UNIT": "Unidades", "FECHA VCTO": "Vencimiento"})
    st.dataframe(rd3, use_container_width=True, hide_index=True)
    botones_descarga(resumen_m, "merma")
