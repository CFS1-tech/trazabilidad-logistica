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
            ~sub["TIPO DE MOVIMIENTO"].isin(
                excluir_tipos
            )
        ]

    stk = (
        sub
        .groupby(
            ["SKU MASEF", "DESCRIPTION"]
        )["TOTAL UNIT"]
        .sum()
        .rename("Stock")
        .reset_index()
    )

    ultima = (
        sub
        .sort_values("FECHA")
        .groupby(
            ["SKU MASEF", "DESCRIPTION"]
        )[["CTN", "ESTADO", "FECHA VCTO"]]
        .last()
        .reset_index()
    )

    result = stk.merge(
        ultima,
        on=["SKU MASEF", "DESCRIPTION"],
        how="left"
    )

    result["Stock"] = result["Stock"].astype(int)

    result = result[
        result["Stock"] > 0
    ].sort_values(
        "Stock",
        ascending=False
    )

    result["FECHA VCTO"] = (
        pd.to_datetime(
            result["FECHA VCTO"],
            errors="coerce"
        )
        .dt.strftime("%Y-%m-%d")
        .fillna("")
    )

    return result.reset_index(drop=True)

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

    vista = st.radio(
        "",
        [
            "📦  Stock",
            "🔍  Trazabilidad",
            "🚚  Despachos",
            "⚠️  Merma",
        ],
        label_visibility="collapsed"
    )

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

    # STOCK REAL
    sub_global = df[
        df["FECHA"].dt.date <= date.today()
    ].copy()

    total_entradas = int(
        sub_global[
            sub_global["TOTAL UNIT"] > 0
        ]["TOTAL UNIT"].sum()
    )

    total_salidas = int(
        sub_global[
            sub_global["TOTAL UNIT"] < 0
        ]["TOTAL UNIT"].sum() * -1
    )

    df_sm = df.copy()

    neto_sku = (
        df_sm
        .groupby("SKU MASEF")["TOTAL UNIT"]
        .sum()
    )

    skus_positivos = neto_sku[
        neto_sku > 0
    ].index

    total_neto = int(
        neto_sku[
            neto_sku > 0
        ].sum()
    )

    df_positivos = df_sm[
        df_sm["SKU MASEF"].isin(
            skus_positivos
        )
    ]

    # SOLO ocultar visualmente MERMA
    df_positivos = df_positivos[
        df_positivos["ESTADO"] != "MERMA"
    ]

    por_estado = (
        df_positivos
        .groupby("ESTADO")["TOTAL UNIT"]
        .sum()
    )

    por_estado = por_estado[
        por_estado > 0
    ]

    cols_metrics = st.columns(
        1 + len(por_estado)
    )

    cols_metrics[0].metric(
        "Total en stock",
        f"{total_neto:,}"
    )

    for i, (estado, unidades) in enumerate(
        por_estado.items()
    ):

        cols_metrics[1 + i].metric(
            estado,
            f"{int(unidades):,}"
        )

    st.divider()

    with st.form("form_stock"):

        col1, col2, col3, col4 = st.columns(
            [2, 2, 2, 1]
        )

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

    # CALCULAR STOCK REAL
    stock_df = calcular_stock(
        df,
        fecha_corte
    )

    # SOLO ocultar MERMA visualmente
    stock_df = stock_df[
        stock_df["ESTADO"] != "MERMA"
    ]

    if buscar:

        mask = (
            stock_df["SKU MASEF"].str.contains(
                buscar,
                case=False,
                na=False
            )
            |
            stock_df["DESCRIPTION"].str.contains(
                buscar,
                case=False,
                na=False
            )
        )

        stock_df = stock_df[mask]

    if f_estado != "Todos":

        stock_df = stock_df[
            stock_df["ESTADO"] == f_estado
        ]

    st.markdown(
        f"**Detalle de stock** — {len(stock_df)} SKUs"
    )

    display = stock_df[
        [
            "SKU MASEF",
            "DESCRIPTION",
            "CTN",
            "ESTADO",
            "FECHA VCTO",
            "Stock",
        ]
    ].rename(columns={

        "SKU MASEF": "SKU",
        "DESCRIPTION": "Descripción",
        "FECHA VCTO": "Vencimiento",
        "Stock": "Unidades en Stock",

    })

    max_stock = (
        int(stock_df["Stock"].max())
        if len(stock_df)
        else 1
    )

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={

            "Unidades en Stock":
            st.column_config.ProgressColumn(
                "Unidades en Stock",
                min_value=0,
                max_value=max_stock,
                format="%d"
            )

        }
    )

    botones_descarga(
        display,
        "stock"
    )
