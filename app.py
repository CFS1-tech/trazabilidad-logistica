"""
app.py  —  WMS MASEF en Streamlit
Desplegable directo en Streamlit Community Cloud.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, datetime

# ── Configuración de página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="WMS MASEF",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constantes ────────────────────────────────────────────────────────────────
MOVIMIENTOS_ENTRADA = {"INGRESO", "AJUSTE-IN"}
MOVIMIENTOS_SALIDA  = {"SALIDA", "AJUSTE-OUT", "MERMA"}
SHEET_NAME          = "TRAZABILIDAD"

BADGE_COLORS = {
    "INGRESO":    ("🟢", "green"),
    "SALIDA":     ("🔴", "red"),
    "AJUSTE-IN":  ("🔵", "blue"),
    "AJUSTE-OUT": ("🟠", "orange"),
    "MERMA":      ("🟣", "violet"),
}

# ── Conexión Google Sheets ────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    # En Streamlit Cloud las credenciales van en st.secrets
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )
    return gspread.authorize(creds)


@st.cache_data(ttl=300)  # cache 5 minutos
def cargar_datos() -> pd.DataFrame:
    client = get_client()
    spreadsheet_id = st.secrets["spreadsheet_id"]
    sh  = client.open_by_key(spreadsheet_id)
    ws  = sh.worksheet(SHEET_NAME)
    df  = pd.DataFrame(ws.get_all_records())

    df["FECHA"]      = pd.to_datetime(df["FECHA"], errors="coerce")
    df["FECHA VCTO"] = pd.to_datetime(df["FECHA VCTO"], errors="coerce")
    df["TOTAL UNIT"] = pd.to_numeric(df["TOTAL UNIT"], errors="coerce").fillna(0).astype(int)
    df["SKU MASEF"]  = df["SKU MASEF"].astype(str)
    df["CTN"]        = df["CTN"].astype(str)

    return df.dropna(subset=["FECHA"])


# ── Lógica de reportes ────────────────────────────────────────────────────────
def calcular_stock(df: pd.DataFrame, fecha_corte) -> pd.DataFrame:
    sub = df[df["FECHA"] <= pd.to_datetime(fecha_corte)].copy()

    def delta(row):
        if row["TIPO DE MOVIMIENTO"] in MOVIMIENTOS_ENTRADA:
            return row["TOTAL UNIT"]
        elif row["TIPO DE MOVIMIENTO"] in MOVIMIENTOS_SALIDA:
            return -row["TOTAL UNIT"]
        return 0

    sub["delta"] = sub.apply(delta, axis=1)

    ent = (sub[sub["TIPO DE MOVIMIENTO"].isin(MOVIMIENTOS_ENTRADA)]
           .groupby(["SKU MASEF", "DESCRIPTION"])["TOTAL UNIT"].sum().rename("Ingresos"))
    sal = (sub[sub["TIPO DE MOVIMIENTO"].isin(MOVIMIENTOS_SALIDA)]
           .groupby(["SKU MASEF", "DESCRIPTION"])["TOTAL UNIT"].sum().rename("Salidas"))
    stk = sub.groupby(["SKU MASEF", "DESCRIPTION"])["delta"].sum().rename("Stock")

    result = pd.concat([ent, sal, stk], axis=1).fillna(0).astype(int).reset_index()
    return result[result["Stock"] > 0].sort_values("Stock", ascending=False)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/warehouse.png", width=60)
    st.title("WMS MASEF")
    st.caption("Warehouse Management System")
    st.divider()

    vista = st.radio(
        "Reportes",
        ["📦 Stock", "🔍 Trazabilidad"],
        label_visibility="collapsed",
    )

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
    st.info("Verifica que `st.secrets` tenga `gcp_service_account` y `spreadsheet_id`.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# VISTA: STOCK
# ══════════════════════════════════════════════════════════════════════════════
if vista == "📦 Stock":
    st.header("📦 Reporte de Stock")
    st.caption("Stock acumulado desde el inicio hasta la fecha de corte seleccionada.")

    # Filtros
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

    # Calcular stock
    stock_df = calcular_stock(df, fecha_corte)
    if buscar:
        mask = (
            stock_df["SKU MASEF"].str.contains(buscar, case=False) |
            stock_df["DESCRIPTION"].str.contains(buscar, case=False)
        )
        stock_df = stock_df[mask]

    # Métricas
    sub_corte = df[df["FECHA"] <= pd.to_datetime(fecha_corte)]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("SKUs con stock",    stock_df["SKU MASEF"].nunique())
    m2.metric("Total unidades",    f"{stock_df['Stock'].sum():,}")
    m3.metric("Ingresos acum.",    f"{sub_corte[sub_corte['TIPO DE MOVIMIENTO']=='INGRESO']['TOTAL UNIT'].sum():,}")
    m4.metric("Salidas acum.",     f"{sub_corte[sub_corte['TIPO DE MOVIMIENTO']=='SALIDA']['TOTAL UNIT'].sum():,}")

    st.divider()

    # Gráfico top 10
    top10 = stock_df.head(10)
    if not top10.empty:
        fig = px.bar(
            top10,
            x="Stock",
            y="DESCRIPTION",
            orientation="h",
            title="Top 10 SKUs por stock",
            color="Stock",
            color_continuous_scale="Blues",
            labels={"DESCRIPTION": "", "Stock": "Unidades"},
        )
        fig.update_layout(
            height=350,
            showlegend=False,
            yaxis={"categoryorder": "total ascending"},
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Tabla
    st.subheader(f"Detalle por SKU ({len(stock_df)} productos)")
    st.dataframe(
        stock_df.rename(columns={
            "SKU MASEF":   "SKU",
            "DESCRIPTION": "Descripción",
        }),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Stock":     st.column_config.ProgressColumn("Stock", min_value=0, max_value=int(stock_df["Stock"].max()) if len(stock_df) else 1),
            "Ingresos":  st.column_config.NumberColumn("Ingresos", format="%d"),
            "Salidas":   st.column_config.NumberColumn("Salidas",  format="%d"),
        },
    )

    # Exportar
    csv = stock_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV", csv, f"stock_{fecha_corte}.csv", "text/csv")


# ══════════════════════════════════════════════════════════════════════════════
# VISTA: TRAZABILIDAD
# ══════════════════════════════════════════════════════════════════════════════
elif vista == "🔍 Trazabilidad":
    st.header("🔍 Reporte de Trazabilidad")
    st.caption("Historial de movimientos filtrado por contenedor, SKU y tipo.")

    # Filtros
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

    col4, col5 = st.columns(2)
    with col4:
        f_desde = st.date_input("📅 Desde", value=df["FECHA"].min().date())
    with col5:
        f_hasta = st.date_input("📅 Hasta", value=date.today())

    # Aplicar filtros
    result = df.copy()
    if f_ctn  != "Todos": result = result[result["CTN"] == f_ctn]
    if f_sku  != "Todos": result = result[result["SKU MASEF"] == f_sku]
    if f_tipo != "Todos": result = result[result["TIPO DE MOVIMIENTO"] == f_tipo]
    result = result[
        (result["FECHA"] >= pd.to_datetime(f_desde)) &
        (result["FECHA"] <= pd.to_datetime(f_hasta))
    ].sort_values("FECHA", ascending=False)

    # Métricas
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Movimientos",  len(result))
    m2.metric("SKUs únicos",  result["SKU MASEF"].nunique())
    m3.metric("CTNs únicos",  result["CTN"].nunique())
    m4.metric("Total unidades", f"{result['TOTAL UNIT'].sum():,}")

    st.divider()

    # Gráfico por tipo
    if not result.empty:
        resumen = result.groupby("TIPO DE MOVIMIENTO")["TOTAL UNIT"].sum().reset_index()
        fig2 = px.bar(
            resumen,
            x="TIPO DE MOVIMIENTO",
            y="TOTAL UNIT",
            title="Unidades por tipo de movimiento",
            color="TIPO DE MOVIMIENTO",
            color_discrete_map={
                "INGRESO":    "#2196F3",
                "SALIDA":     "#F44336",
                "AJUSTE-IN":  "#4CAF50",
                "AJUSTE-OUT": "#FF9800",
                "MERMA":      "#9C27B0",
            },
            labels={"TOTAL UNIT": "Unidades", "TIPO DE MOVIMIENTO": ""},
        )
        fig2.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    # Tabla
    st.subheader(f"Movimientos ({len(result)} registros)")
    cols_mostrar = ["FECHA", "CTN", "SKU MASEF", "DESCRIPTION", "TIPO DE MOVIMIENTO", "TOTAL UNIT", "ESTADO", "FECHA VCTO"]
    result_display = result[cols_mostrar].copy()
    result_display["FECHA"] = result_display["FECHA"].dt.strftime("%Y-%m-%d")
    result_display["FECHA VCTO"] = result_display["FECHA VCTO"].dt.strftime("%Y-%m-%d").where(result_display["FECHA VCTO"].notna(), "")

    st.dataframe(
        result_display.rename(columns={
            "SKU MASEF":         "SKU",
            "DESCRIPTION":       "Descripción",
            "TIPO DE MOVIMIENTO":"Movimiento",
            "TOTAL UNIT":        "Unidades",
            "FECHA VCTO":        "Vencimiento",
        }),
        use_container_width=True,
        hide_index=True,
    )

    # Exportar
    csv = result_display.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV", csv, f"trazabilidad_{f_desde}_{f_hasta}.csv", "text/csv")
