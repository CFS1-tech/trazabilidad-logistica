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

# ── Estilos ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #0f1923;
}
[data-testid="stSidebar"] * {
    color: #e0e6f0 !important;
}
[data-testid="stSidebar"] .stRadio label {
    color: #a0aec0 !important;
    font-size: 14px;
}
[data-testid="stSidebar"] hr {
    border-color: #2d3748;
}

/* Métricas */
[data-testid="stMetric"] {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 16px 20px;
}
[data-testid="stMetricLabel"] { font-size: 12px !important; color: #64748b !important; }
[data-testid="stMetricValue"] { font-size: 26px !important; color: #0f172a !important; font-weight: 600 !important; }

/* Badges en tabla */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.03em;
}
.badge-in    { background: #dcfce7; color: #166534; }
.badge-out   { background: #fee2e2; color: #991b1b; }
.badge-ajin  { background: #dbeafe; color: #1e40af; }
.badge-ajout { background: #fef3c7; color: #92400e; }
.badge-merma { background: #f3e8ff; color: #6b21a8; }

/* Botón buscar */
.stButton > button {
    background-color: #185FA5 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}
.stButton > button:hover {
    background-color: #0C447C !important;
}

/* Form container */
[data-testid="stForm"] {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px;
}

/* Header */
h1 { color: #0f172a !important; font-weight: 700 !important; }
h2 { color: #1e293b !important; font-weight: 600 !important; font-size: 18px !important; }
</style>
""", unsafe_allow_html=True)

MOVIMIENTOS_ENTRADA = {"INGRESO", "AJUSTE-IN"}
MOVIMIENTOS_SALIDA  = {"SALIDA", "AJUSTE-OUT", "MERMA"}
SHEET_NAME          = "TRAZABILIDAD"

BADGE_MAP = {
    "INGRESO":    ("INGRESO",    "badge-in"),
    "SALIDA":     ("SALIDA",     "badge-out"),
    "AJUSTE-IN":  ("AJUSTE-IN",  "badge-ajin"),
    "AJUSTE-OUT": ("AJUSTE-OUT", "badge-ajout"),
    "MERMA":      ("MERMA",      "badge-merma"),
}

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

def calcular_stock(df: pd.DataFrame, fecha_corte) -> pd.DataFrame:
    corte = pd.to_datetime(fecha_corte)
    sub   = df[df["FECHA"].dt.date <= corte.date()].copy()
    stk_sku = sub.groupby(["SKU MASEF", "DESCRIPTION"])["TOTAL UNIT"].sum().rename("Stock").reset_index()
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
    st.markdown("### 📦 WMS MASEF")
    st.markdown("<small style='color:#64748b'>Warehouse Management System</small>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<small style='color:#64748b;text-transform:uppercase;letter-spacing:.08em'>REPORTES</small>", unsafe_allow_html=True)
    vista = st.radio("", ["📦  Stock", "🔍  Trazabilidad"], label_visibility="collapsed")
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
# VISTA: STOCK
# ══════════════════════════════════════════════════════════════════════════════
if vista == "📦  Stock":
    st.markdown("## 📦 Reporte de Stock")
    st.caption("Stock acumulado desde el inicio hasta la fecha de corte seleccionada.")

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
            st.write(""); st.write("")
            st.form_submit_button("🔍 Buscar", use_container_width=True)

    stock_df = calcular_stock(df, fecha_corte)
    if buscar:
        mask = (
            stock_df["SKU MASEF"].str.contains(buscar, case=False) |
            stock_df["DESCRIPTION"].str.contains(buscar, case=False)
        )
        stock_df = stock_df[mask]

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

    top10 = stock_df[stock_df["Stock"] > 0].head(10)
    if not top10.empty:
        fig = px.bar(
            top10, x="Stock", y="DESCRIPTION", orientation="h",
            title="Top 10 SKUs por stock",
            color="Stock", color_continuous_scale="Blues",
            labels={"DESCRIPTION": "", "Stock": "Unidades"},
        )
        fig.update_layout(
            height=350, showlegend=False, plot_bgcolor="white",
            paper_bgcolor="white", font=dict(family="sans-serif", size=12),
            yaxis={"categoryorder": "total ascending"},
            coloraxis_showscale=False,
            title=dict(font=dict(size=14, color="#1e293b")),
        )
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"**Detalle de stock** — {len(stock_df)} SKUs")
    display = stock_df[["SKU MASEF", "DESCRIPTION", "CTN", "ESTADO", "FECHA VCTO", "Stock"]].rename(columns={
        "SKU MASEF":   "SKU",
        "DESCRIPTION": "Descripción",
        "FECHA VCTO":  "Vencimiento",
        "Stock":       "Unidades en Stock",
    })
    max_stock = int(stock_df[stock_df["Stock"] > 0]["Stock"].max()) if len(stock_df) else 1
    st.dataframe(
        display, use_container_width=True, hide_index=True,
        column_config={
            "Unidades en Stock": st.column_config.ProgressColumn(
                "Unidades en Stock", min_value=0, max_value=max_stock, format="%d",
            ),
        },
    )

    col_csv, col_xlsx = st.columns(2)
    with col_csv:
        st.download_button("⬇️ Exportar CSV", display.to_csv(index=False).encode("utf-8"),
            f"stock_{fecha_corte}.csv", "text/csv", use_container_width=True)
    with col_xlsx:
        st.download_button("📊 Exportar Excel", to_excel(display),
            f"stock_{fecha_corte}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# VISTA: TRAZABILIDAD
# ══════════════════════════════════════════════════════════════════════════════
elif vista == "🔍  Trazabilidad":
    st.markdown("## 🔍 Reporte de Trazabilidad")
    st.caption("Historial de movimientos filtrado por contenedor, SKU y tipo.")

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

    def clasificar(tipo):
        if tipo in MOVIMIENTOS_ENTRADA: return "ENTRADA"
        elif tipo in MOVIMIENTOS_SALIDA: return "SALIDA"
        return tipo

    result["CLASE"] = result["TIPO DE MOVIMIENTO"].apply(clasificar)
    if f_ctn  != "Todos": result = result[result["CTN"] == f_ctn]
    if f_sku  != "Todos": result = result[result["SKU MASEF"] == f_sku]
    if f_tipo != "Todos": result = result[result["TIPO DE MOVIMIENTO"] == f_tipo]
    result = result[
        (result["FECHA"].dt.date >= f_desde) &
        (result["FECHA"].dt.date <= f_hasta)
    ].sort_values("FECHA", ascending=False)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Movimientos",    len(result))
    m2.metric("SKUs únicos",    result["SKU MASEF"].nunique())
    m3.metric("CTNs únicos",    result["CTN"].nunique())
    m4.metric("Total unidades", f"{result['TOTAL UNIT'].sum():,}")

    st.divider()

    if not result.empty:
        resumen = result.groupby("TIPO DE MOVIMIENTO")["TOTAL UNIT"].sum().abs().reset_index()
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
        fig2.update_layout(
            height=280, showlegend=False, plot_bgcolor="white",
            paper_bgcolor="white", font=dict(family="sans-serif", size=12),
            title=dict(font=dict(size=14, color="#1e293b")),
        )
        fig2.update_traces(marker_line_width=0)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown(f"**Movimientos** — {len(result)} registros")
    cols_mostrar = ["FECHA", "CTN", "SKU MASEF", "DESCRIPTION", "TIPO DE MOVIMIENTO", "CLASE", "TOTAL UNIT", "ESTADO", "FECHA VCTO"]
    result_display = result[cols_mostrar].copy()
    result_display["FECHA"]      = result_display["FECHA"].dt.strftime("%Y-%m-%d")
    result_display["FECHA VCTO"] = result_display["FECHA VCTO"].dt.strftime("%Y-%m-%d").where(result_display["FECHA VCTO"].notna(), "")

    traz_renamed = result_display.rename(columns={
        "SKU MASEF":          "SKU",
        "DESCRIPTION":        "Descripción",
        "TIPO DE MOVIMIENTO": "Tipo",
        "CLASE":              "Entrada/Salida",
        "TOTAL UNIT":         "Unidades",
        "FECHA VCTO":         "Vencimiento",
    })
    st.dataframe(traz_renamed, use_container_width=True, hide_index=True,
        column_config={
            "Entrada/Salida": st.column_config.TextColumn("Entrada/Salida", width="small"),
            "Tipo":           st.column_config.TextColumn("Tipo",           width="small"),
        }
    )

    col_csv, col_xlsx = st.columns(2)
    with col_csv:
        st.download_button("⬇️ Exportar CSV", result_display.to_csv(index=False).encode("utf-8"),
            f"trazabilidad_{f_desde}_{f_hasta}.csv", "text/csv", use_container_width=True)
    with col_xlsx:
        st.download_button("📊 Exportar Excel", to_excel(traz_renamed),
            f"trazabilidad_{f_desde}_{f_hasta}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)
