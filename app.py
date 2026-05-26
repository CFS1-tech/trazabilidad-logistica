"""
app.py  —  WMS en Streamlit
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
import io
from google.oauth2.service_account import Credentials
from datetime import date, datetime

st.set_page_config(
    page_title="WMS",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* ── GLOBAL ── */
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 100%; }
[data-testid="stAppViewContainer"] { background: #f0f2f6; }

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1b2a 0%, #1a2f4a 100%) !important;
    border-right: 1px solid #1e3a5f;
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
[data-testid="stSidebar"] hr { border-color: #1e3a5f !important; }
[data-testid="stSidebar"] .stRadio label {
    padding: 8px 12px !important;
    border-radius: 6px !important;
    margin: 2px 0 !important;
    transition: background 0.2s !important;
    display: block !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,0.07) !important; }
[data-testid="stSidebar"] [data-baseweb="radio"] input:checked + div + label,
[data-testid="stSidebar"] .stRadio [aria-checked="true"] + label {
    background: rgba(24,95,165,0.35) !important;
    color: #93c5fd !important;
}

/* ── MÉTRICAS ── */
[data-testid="stMetric"] {
    background: #ffffff !important;
    border: none !important;
    border-left: 4px solid #185FA5 !important;
    border-radius: 8px !important;
    padding: 18px 22px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08) !important;
}
[data-testid="stMetricLabel"] {
    font-size: 11px !important;
    font-weight: 600 !important;
    color: #64748b !important;
    text-transform: uppercase !important;
    letter-spacing: .06em !important;
}
[data-testid="stMetricValue"] {
    font-size: 28px !important;
    font-weight: 700 !important;
    color: #0f172a !important;
}

/* ── BOTONES ── */
.stButton > button {
    background: linear-gradient(135deg, #185FA5 0%, #1a6fc4 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 8px 16px !important;
    transition: all 0.2s !important;
    box-shadow: 0 2px 4px rgba(24,95,165,0.3) !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #0C447C 0%, #185FA5 100%) !important;
    box-shadow: 0 4px 8px rgba(24,95,165,0.4) !important;
    transform: translateY(-1px) !important;
}

/* ── BOTONES DESCARGA ── */
[data-testid="stDownloadButton"] > button {
    background: #ffffff !important;
    color: #185FA5 !important;
    border: 1.5px solid #185FA5 !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 12px !important;
}
[data-testid="stDownloadButton"] > button:hover {
    background: #185FA5 !important;
    color: white !important;
}

/* ── FORMULARIOS ── */
[data-testid="stForm"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
    padding: 20px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
}

/* ── INPUTS ── */
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] > div,
[data-testid="stDateInput"] input {
    border-radius: 6px !important;
    border-color: #cbd5e1 !important;
    font-size: 13px !important;
}

/* ── DATAFRAME ── */
[data-testid="stDataFrame"] {
    border-radius: 10px !important;
    overflow: hidden !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
}

/* ── DIVIDER ── */
hr { border-color: #e2e8f0 !important; margin: 1rem 0 !important; }

/* ── PÁGINA HEADER ── */
.wms-header {
    background: linear-gradient(135deg, #0d1b2a 0%, #185FA5 100%);
    border-radius: 10px;
    padding: 20px 28px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 4px 12px rgba(24,95,165,0.25);
}
.wms-header h1 {
    color: white !important;
    font-size: 20px !important;
    font-weight: 700 !important;
    margin: 0 !important;
    letter-spacing: -.01em !important;
}
.wms-header p {
    color: #93c5fd !important;
    font-size: 12px !important;
    margin: 2px 0 0 0 !important;
}
.wms-badge {
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 11px;
    color: white !important;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .06em;
    margin-left: auto;
}

/* ── SECCIÓN LABEL ── */
.section-label {
    font-size: 10px;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: .1em;
    margin-bottom: 8px;
}

/* ── ALERT / INFO BOXES ── */
.wms-info {
    background: #eff6ff;
    border-left: 4px solid #3b82f6;
    border-radius: 6px;
    padding: 10px 16px;
    font-size: 13px;
    color: #1e40af;
    margin-bottom: 12px;
}
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

    st.markdown(
        "<div style='font-size:10px;font-weight:700;color:#94a3b8;"
        "text-transform:uppercase;letter-spacing:.08em;margin:16px 0 6px'>Exportar</div>",
        unsafe_allow_html=True
    )

    col_csv, col_xlsx, col_space = st.columns([1, 1, 3])

    with col_csv:
        st.download_button(
            "⬇️ CSV",
            df_display.to_csv(index=False).encode("utf-8"),
            f"{nombre}_{date.today()}.csv",
            "text/csv",
            use_container_width=True
        )

    with col_xlsx:
        st.download_button(
            "📊 Excel",
            to_excel(df_display),
            f"{nombre}_{date.today()}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# ── Login ─────────────────────────────────────────────────────────────────────

USUARIOS = {
    "admin":    {"password": "admin123",  "rol": "administrador"},
    "cliente":  {"password": "cliente123","rol": "cliente"},
}

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["rol"]         = None
    st.session_state["usuario"]     = None

def do_login(usuario, password):
    u = USUARIOS.get(usuario)
    if u and u["password"] == password:
        st.session_state["autenticado"] = True
        st.session_state["rol"]         = u["rol"]
        st.session_state["usuario"]     = usuario
        return True
    return False

def do_logout():
    st.session_state["autenticado"] = False
    st.session_state["rol"]         = None
    st.session_state["usuario"]     = None

if not st.session_state["autenticado"]:

    st.markdown("""
    <div style="max-width:420px;margin:60px auto 0 auto">
      <div style="background:linear-gradient(135deg,#0d1b2a 0%,#185FA5 100%);
                  border-radius:14px;padding:36px 32px 28px;text-align:center;
                  box-shadow:0 8px 32px rgba(24,95,165,0.3);margin-bottom:24px">
        <div style="font-size:48px;margin-bottom:12px">📦</div>
        <h1 style="color:white;font-size:24px;font-weight:700;margin:0;letter-spacing:-.02em">
          Warehouse Management System
        </h1>
        <p style="color:#93c5fd;font-size:13px;margin:8px 0 0">
          Ingresa tus credenciales para continuar
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        with st.form("form_login"):
            st.markdown(
                "<p style='font-size:11px;font-weight:700;color:#64748b;"
                "text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px'>Usuario</p>",
                unsafe_allow_html=True
            )
            usuario  = st.text_input("", placeholder="Ingresa tu usuario", label_visibility="collapsed")
            st.markdown(
                "<p style='font-size:11px;font-weight:700;color:#64748b;"
                "text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px'>Contraseña</p>",
                unsafe_allow_html=True
            )
            password = st.text_input("", placeholder="••••••••", type="password", label_visibility="collapsed")
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            ok = st.form_submit_button("🔐  Ingresar al sistema", use_container_width=True)

        if ok:
            if do_login(usuario.strip(), password.strip()):
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos.")

    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────

ROL = st.session_state["rol"]

VISTAS_ADMIN  = ["📦  Stock", "🔍  Trazabilidad", "📦  Packing List", "⚠️  Merma"]
VISTAS_CLIENTE = ["📦  Stock", "🔍  Trazabilidad", "📦  Packing List"]

opciones_vista = VISTAS_ADMIN if ROL == "administrador" else VISTAS_CLIENTE

with st.sidebar:

    # Logo / Título
    st.markdown("""
    <div style="padding:20px 4px 8px;text-align:center">
      <div style="font-size:36px">📦</div>
      <div style="font-size:18px;font-weight:700;color:#e2e8f0;letter-spacing:-.01em">WMS</div>
      <div style="font-size:10px;color:#64748b;text-transform:uppercase;
                  letter-spacing:.1em;margin-top:2px">Warehouse Management</div>
    </div>
    """, unsafe_allow_html=True)

    # Usuario
    rol_color = "#3b82f6" if ROL == "administrador" else "#10b981"
    st.markdown(
        f"""<div style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);
                        border-radius:8px;padding:10px 12px;margin:8px 0 16px">
              <div style="font-size:11px;color:#94a3b8;margin-bottom:2px">Sesión activa</div>
              <div style="display:flex;align-items:center;gap:8px">
                <span style="font-size:13px;color:#e2e8f0;font-weight:600">
                  👤 {st.session_state['usuario']}
                </span>
                <span style="background:{rol_color};color:white;font-size:9px;
                             font-weight:700;padding:2px 8px;border-radius:10px;
                             text-transform:uppercase;letter-spacing:.06em">{ROL}</span>
              </div>
            </div>""",
        unsafe_allow_html=True
    )

    st.markdown(
        "<div style='font-size:9px;font-weight:700;color:#475569;"
        "text-transform:uppercase;letter-spacing:.12em;padding:0 4px 6px'>Módulos</div>",
        unsafe_allow_html=True
    )

    vista = st.radio("", opciones_vista, label_visibility="collapsed")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:9px;font-weight:700;color:#475569;"
        "text-transform:uppercase;letter-spacing:.12em;padding:0 4px 6px'>Sistema</div>",
        unsafe_allow_html=True
    )

    if st.button("🔄  Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if st.button("🚪  Cerrar sesión", use_container_width=True):
        do_logout()
        st.rerun()

    st.markdown(
        f"<div style='font-size:10px;color:#475569;padding:12px 4px 4px;"
        f"border-top:1px solid #1e3a5f;margin-top:8px'>"
        f"⏱ Datos al {datetime.now().strftime('%H:%M:%S')}</div>",
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

# ── Columnas clave del packing list (detección global) ───────────────────────
col_ctn_pk = next(
    (c for c in packing_df.columns if "CTN" in c.upper() or "CONTENEDOR" in c.upper()),
    packing_df.columns[0]
)
col_sku_pk = next(
    (c for c in packing_df.columns if "SKU" in c.upper()),
    packing_df.columns[0]
)

# ══════════════════════════════════════════════════════════════════════════════
# VISTA: STOCK
# ══════════════════════════════════════════════════════════════════════════════

if vista == "📦  Stock":

    st.markdown(f"""
    <div class="wms-header">
      <div style="font-size:32px">📦</div>
      <div>
        <h1>Reporte de Stock</h1>
        <p>Stock acumulado hasta la fecha de corte seleccionada</p>
      </div>
      <span class="wms-badge">En tiempo real</span>
    </div>
    """, unsafe_allow_html=True)

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
        f"""<div style='display:flex;align-items:center;justify-content:space-between;
                        margin-bottom:8px'>
              <span style='font-size:13px;font-weight:700;color:#1e293b'>
                Detalle de stock
              </span>
              <span style='background:#eff6ff;color:#185FA5;font-size:11px;
                           font-weight:700;padding:3px 10px;border-radius:12px;
                           border:1px solid #bfdbfe'>
                {{len(stock_df)}} registros
              </span>
            </div>""",
        unsafe_allow_html=True
    )

    # ── Merge con PACKINGLIST para traer CASE PACK IN (presentación) ──
    pk_presentacion = (
        packing_df[["CTN", col_sku_pk, "CASE PACK IN"]]
        .copy()
        .rename(columns={col_sku_pk: "SKU MASEF"})
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

    st.markdown(f"""
    <div class="wms-header">
      <div style="font-size:32px">🔍</div>
      <div>
        <h1>Trazabilidad de Movimientos</h1>
        <p>Historial completo de entradas, salidas y ajustes</p>
      </div>
      <span class="wms-badge">Auditoría</span>
    </div>
    """, unsafe_allow_html=True)

    with st.form("form_trazabilidad"):

        col1, col2, col3 = st.columns(3)

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

            tipos_mov = ["Todos"] + sorted(
                df["TIPO DE MOVIMIENTO"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            f_tipo = st.selectbox("🔄 Tipo de movimiento", tipos_mov)

        col5, col6 = st.columns(2)

        with col5:

            fecha_desde = st.date_input(
                "📅 Desde",
                value=df["FECHA"].min().date()
            )

        with col6:

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

    if f_tipo != "Todos":
        traz = traz[traz["TIPO DE MOVIMIENTO"] == f_tipo]

    traz = traz[
        (traz["FECHA"].dt.date >= fecha_desde)
        &
        (traz["FECHA"].dt.date <= fecha_hasta)
    ]

    traz = traz.sort_values("FECHA", ascending=False)

    m1, m2, m3 = st.columns(3)

    m1.metric("📋 Movimientos",    f"{len(traz):,}")
    m2.metric("🏷️ SKUs únicos",   f"{traz['SKU MASEF'].nunique():,}")
    m3.metric("📦 Contenedores",   f"{traz['CTN'].nunique():,}")

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

    st.markdown(f"""
    <div class="wms-header">
      <div style="font-size:32px">📋</div>
      <div>
        <h1>Packing List</h1>
        <p>Detalle de contenedores y unidades por SKU</p>
      </div>
      <span class="wms-badge">Recepción</span>
    </div>
    """, unsafe_allow_html=True)

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

    st.markdown(f"""
    <div class="wms-header">
      <div style="font-size:32px">⚠️</div>
      <div>
        <h1>Reporte de Merma</h1>
        <p>Productos dañados, vencidos o con pérdida registrada</p>
      </div>
      <span class="wms-badge">Alertas</span>
    </div>
    """, unsafe_allow_html=True)

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
