"""
app.py  —  WMS en Streamlit
"""

import streamlit as st
import streamlit.components.v1 as components
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

/* ── FILTRO PROVEEDOR fuera del form: fondo blanco igual al form ── */
.filtro-prov-wrap {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 16px 20px 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    margin-bottom: 12px;
}

/* ── DESPACHO OPERATIVO ── */
.desp-card {
    background:#ffffff; border:1px solid #e2e8f0; border-radius:10px;
    padding:14px 18px; margin-bottom:8px; box-shadow:0 1px 3px rgba(0,0,0,0.05);
    transition: border-color .15s, box-shadow .15s;
}
.desp-sku   { font-size:11px; font-weight:700; color:#185FA5; text-transform:uppercase; letter-spacing:.06em; }
.desp-desc  { font-size:14px; font-weight:600; color:#0f172a; margin:2px 0 4px; }
.desp-meta  { font-size:11px; color:#64748b; }
.desp-stock { font-size:13px; font-weight:700; color:#10b981; }
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
        col = col.astype(str).str.strip()

        # Intentar múltiples formatos en orden
        formatos = [
            "%d/%m/%Y",   # 24/03/2026  — formato principal de la sheet
            "%Y-%m-%d",   # 2026-03-24  — formato ISO
            "%d-%m-%Y",   # 24-03-2026
            "%m/%d/%Y",   # 03/24/2026  — formato US
        ]

        parsed = pd.Series(pd.NaT, index=col.index)

        pendientes = col.str.strip().ne("") & col.ne("nan")

        for fmt in formatos:
            mask = pendientes & parsed.isna()
            if not mask.any():
                break
            parsed[mask] = pd.to_datetime(col[mask], format=fmt, errors="coerce")

        # Último intento: parser automático con dayfirst=True
        mask_final = pendientes & parsed.isna()
        if mask_final.any():
            parsed[mask_final] = pd.to_datetime(
                col[mask_final], dayfirst=True, errors="coerce"
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
    # PASO 1: Combinaciones SKU+CTN con neto > 0
    # Filtramos por SKU+CTN para no descartar un
    # SKU completo cuando tiene salidas en exceso
    # en otro contenedor distinto.
    # ─────────────────────────────────────────────

    neto_por_sku_ctn = (
        sub
        .groupby(["SKU MASEF", "CTN"])["TOTAL UNIT"]
        .sum()
    )

    skus_ctns_con_stock = neto_por_sku_ctn[neto_por_sku_ctn > 0].reset_index()[["SKU MASEF", "CTN"]]
    skus_ctns_con_stock["_key"] = skus_ctns_con_stock["SKU MASEF"] + "||" + skus_ctns_con_stock["CTN"]

    # ─────────────────────────────────────────────
    # PASO 2: Filtrar solo filas de esas combos
    # ─────────────────────────────────────────────

    sub["_key"] = sub["SKU MASEF"] + "||" + sub["CTN"]
    sub_valido  = sub[sub["_key"].isin(skus_ctns_con_stock["_key"])].drop(columns=["_key"])

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


def formatear_fechas_excel(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte columnas de fecha a formato DD/MM/YYYY para exportación."""
    df = df.copy()
    for col in df.columns:
        if "FECHA" in col.upper() or "VENCIMIENTO" in col.upper() or "INGRESO" in col.upper():
            converted = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
            if converted.notna().any():
                df[col] = converted.dt.strftime("%d/%m/%Y").fillna(df[col].astype(str))
    return df

def to_excel(df_export: pd.DataFrame) -> bytes:

    buf = io.BytesIO()
    df_fmt = formatear_fechas_excel(df_export)

    with pd.ExcelWriter(
        buf,
        engine="openpyxl"
    ) as writer:

        df_fmt.to_excel(
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
            formatear_fechas_excel(df_display).to_csv(index=False).encode("utf-8"),
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
    "admin":      {"password": "Duquesa24",   "rol": "administrador"},
    "Masef_CFS":  {"password": "Masef2026",  "rol": "cliente"},
    "operario":   {"password": "Op2026",     "rol": "operario"},
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

VISTAS_REPORTES_ADMIN   = ["📊  Dashboard", "📦  Stock", "🔍  Trazabilidad", "🚚  Despachos", "📦  Packing List", "⚠️  Merma"]
VISTAS_REPORTES_CLIENTE = ["📊  Dashboard", "📦  Stock", "🔍  Trazabilidad", "🚚  Despachos", "📦  Packing List"]
VISTAS_OPERACIONES      = ["🛒  Despacho Operativo", "📥  Carga Packing List", "🔄  Cambio de Estado CTN", "⚠️  Salida de Merma"]

reportes_opts    = VISTAS_REPORTES_ADMIN if ROL in ("administrador", "operario") else VISTAS_REPORTES_CLIENTE
operaciones_opts = VISTAS_OPERACIONES    if ROL in ("administrador", "operario") else []

# ── Inicializar estado de navegación ──────────────────────────────────────────
if "nav_vista"       not in st.session_state:
    st.session_state["nav_vista"]       = "📊  Dashboard"
if "nav_rep_abierto" not in st.session_state:
    st.session_state["nav_rep_abierto"] = True
if "nav_op_abierto"  not in st.session_state:
    st.session_state["nav_op_abierto"]  = False

# ── Construir listas de botones del menú en orden de aparición ────────────────
# Esto nos permite saber exactamente qué tipo es cada botón por posición
_menu_buttons = []   # lista de dicts: {label, tipo: "section"|"item"|"active"}

_menu_buttons.append({"tipo": "section"})  # Reportes

if st.session_state["nav_rep_abierto"]:
    for o in reportes_opts:
        t = "active" if st.session_state["nav_vista"] == o else "item"
        _menu_buttons.append({"tipo": t})

if operaciones_opts:
    _menu_buttons.append({"tipo": "section"})  # Operaciones
    if st.session_state["nav_op_abierto"]:
        for o in operaciones_opts:
            t = "active" if st.session_state["nav_vista"] == o else "item"
            _menu_buttons.append({"tipo": t})

# Generar CSS apuntando a cada botón por nth-child dentro del sidebar
# Los botones del nav son los primeros botones del sidebar (tras el usuario)
# Usamos nth-of-type sobre los stButton dentro del sidebar
_css_rules = []
for _i, _b in enumerate(_menu_buttons):
    # nth-child es 1-based; dentro del sidebar hay botones previos (sistema al final)
    # apuntamos por data-testid del stButton específico usando ~nth~ sobre el contenedor
    _n = _i + 1
    if _b["tipo"] == "section":
        _css_rules.append(f"""
[data-testid="stSidebar"] section div[data-testid="stButton"]:nth-of-type({_n}) button {{
    background: linear-gradient(135deg, #0f2236 0%, #1a3352 100%) !important;
    color: #e2e8f0 !important;
    border: 1px solid #2a4a6b !important;
    border-radius: 8px !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: .1em !important;
    padding: 9px 14px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,.35) !important;
    transform: none !important;
    margin-bottom: 2px !important;
}}""")
    elif _b["tipo"] == "item":
        _css_rules.append(f"""
[data-testid="stSidebar"] section div[data-testid="stButton"]:nth-of-type({_n}) button {{
    background: transparent !important;
    color: #7a92ad !important;
    border: none !important;
    border-left: 2px solid #1e3a5f !important;
    border-radius: 0 5px 5px 0 !important;
    font-size: 12px !important;
    font-weight: 400 !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
    padding: 6px 8px 6px 18px !important;
    box-shadow: none !important;
    transform: none !important;
    margin-left: 10px !important;
    width: calc(100% - 10px) !important;
}}
[data-testid="stSidebar"] section div[data-testid="stButton"]:nth-of-type({_n}) button:hover {{
    background: rgba(255,255,255,0.05) !important;
    color: #cbd5e1 !important;
    border-left: 2px solid #3b82f6 !important;
}}""")
    elif _b["tipo"] == "active":
        _css_rules.append(f"""
[data-testid="stSidebar"] section div[data-testid="stButton"]:nth-of-type({_n}) button {{
    background: rgba(24,95,165,0.2) !important;
    color: #93c5fd !important;
    border: none !important;
    border-left: 3px solid #3b82f6 !important;
    border-radius: 0 5px 5px 0 !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
    padding: 6px 8px 6px 17px !important;
    box-shadow: none !important;
    transform: none !important;
    margin-left: 10px !important;
    width: calc(100% - 10px) !important;
}}""")

_css_nav = "<style>" + "\n".join(_css_rules) + "\n</style>"

with st.sidebar:

    # ── Logo ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="padding:16px 4px 8px;text-align:center">
      <div style="font-size:36px">📦</div>
      <div style="font-size:18px;font-weight:700;color:#e2e8f0;letter-spacing:-.01em">WMS</div>
      <div style="font-size:10px;color:#64748b;text-transform:uppercase;
                  letter-spacing:.1em;margin-top:2px">Warehouse Management</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Usuario ────────────────────────────────────────────────────────────────
    rol_color = "#3b82f6" if ROL == "administrador" else "#10b981"
    st.markdown(
        f"""<div style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);
                        border-radius:8px;padding:10px 12px;margin:8px 0 14px">
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

    # Inyectar CSS generado antes de los botones
    st.markdown(_css_nav, unsafe_allow_html=True)

    # ── Sección REPORTES ───────────────────────────────────────────────────────
    rep_icon = "▼" if st.session_state["nav_rep_abierto"] else "▶"
    if st.button(f"{rep_icon}  📋  Reportes", use_container_width=True, key="btn_sec_rep"):
        st.session_state["nav_rep_abierto"] = not st.session_state["nav_rep_abierto"]
        st.rerun()

    if st.session_state["nav_rep_abierto"]:
        for opcion in reportes_opts:
            if st.button(opcion, use_container_width=True, key=f"nav_{opcion}"):
                st.session_state["nav_vista"] = opcion
                st.rerun()

    # ── Sección OPERACIONES ────────────────────────────────────────────────────
    if operaciones_opts:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        op_icon = "▼" if st.session_state["nav_op_abierto"] else "▶"
        if st.button(f"{op_icon}  ⚙️  Operaciones", use_container_width=True, key="btn_sec_op"):
            st.session_state["nav_op_abierto"] = not st.session_state["nav_op_abierto"]
            st.rerun()

        if st.session_state["nav_op_abierto"]:
            for opcion in operaciones_opts:
                if st.button(opcion, use_container_width=True, key=f"nav_{opcion}"):
                    st.session_state["nav_vista"] = opcion
                    st.rerun()

    # ── Sistema ────────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:9px;font-weight:700;color:#475569;"
        "text-transform:uppercase;letter-spacing:.12em;padding:14px 4px 6px;"
        "border-top:1px solid #1e3a5f;margin-top:10px'>Sistema</div>",
        unsafe_allow_html=True
    )

    if st.button("🔄  Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if st.button("🚪  Cerrar sesión", use_container_width=True):
        do_logout()
        st.rerun()

    st.markdown(
        f"<div style='font-size:10px;color:#475569;padding:10px 4px 4px;"
        f"border-top:1px solid #1e3a5f;margin-top:6px'>"
        f"⏱ Datos al {datetime.now().strftime('%H:%M:%S')}</div>",
        unsafe_allow_html=True
    )

# ── Vista activa ──────────────────────────────────────────────────────────────
vista = st.session_state["nav_vista"]

todas_las_vistas = reportes_opts + operaciones_opts
if vista not in todas_las_vistas:
    vista = reportes_opts[0]
    st.session_state["nav_vista"] = vista

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
col_proveedor_pk = next(
    (c for c in packing_df.columns if "PROVEEDOR" in c.upper() or "SUPPLIER" in c.upper() or "VENDOR" in c.upper()),
    None
)

# ── Tabla auxiliar del packing list: CTN + SKU → extras ──────────────────────
def _build_pk_aux(cols_extra: list) -> pd.DataFrame:
    """Construye un DF del packing list con las columnas extra solicitadas."""
    cols_base = ["CTN", col_sku_pk]
    cols_ok   = cols_base + [c for c in cols_extra if c and c in packing_df.columns]
    aux = packing_df[cols_ok].copy().rename(columns={col_sku_pk: "SKU MASEF"})
    aux["CTN"]       = aux["CTN"].astype(str).str.strip()
    aux["SKU MASEF"] = aux["SKU MASEF"].astype(str).str.strip()
    return aux.drop_duplicates(subset=["CTN", "SKU MASEF"])


# ══════════════════════════════════════════════════════════════════════════════
# VISTA: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

if vista == "📊  Dashboard":

    st.markdown(f"""
    <div class="wms-header">
      <div style="font-size:32px">📊</div>
      <div>
        <h1>Dashboard Operativo</h1>
        <p>Indicadores clave del almacén en tiempo real</p>
      </div>
      <span class="wms-badge">Hoy {date.today().strftime("%d/%m/%Y")}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Preparar datos base ──────────────────────────────────────────────────
    hoy        = date.today()
    hace30     = pd.Timestamp(hoy) - pd.Timedelta(days=30)
    hace7      = pd.Timestamp(hoy) - pd.Timedelta(days=7)

    df_hoy     = df[df["FECHA"].dt.date <= hoy].copy()
    df_sin_merma = df_hoy[df_hoy["ESTADO"] != "MERMA"].copy()

    # Stock neto global
    neto_global = df_sin_merma.groupby("SKU MASEF")["TOTAL UNIT"].sum()
    stock_total = int(neto_global[neto_global > 0].sum())
    skus_en_stock = int((neto_global > 0).sum())

    # Movimientos últimos 30 días
    df_30 = df[df["FECHA"] >= hace30].copy()
    salidas_30 = int(df_30[df_30["TOTAL UNIT"] < 0]["TOTAL UNIT"].sum() * -1)
    entradas_30 = int(df_30[df_30["TOTAL UNIT"] > 0]["TOTAL UNIT"].sum())

    # Movimientos últimos 7 días
    df_7 = df[df["FECHA"] >= hace7].copy()
    salidas_7  = int(df_7[df_7["TOTAL UNIT"] < 0]["TOTAL UNIT"].sum() * -1)

    # SKUs sin movimiento en 30 días
    skus_activos_30 = df_30["SKU MASEF"].unique()
    skus_stock_list = neto_global[neto_global > 0].index
    skus_sin_mov = int(len([s for s in skus_stock_list if s not in skus_activos_30]))

    # ── KPIs fila 1 ──────────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:11px;font-weight:700;color:#64748b;"
        "text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px'>"
        "📌 Resumen General</div>",
        unsafe_allow_html=True
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📦 Unidades en Stock",      f"{stock_total:,}")
    k2.metric("🏷️ SKUs activos",           f"{skus_en_stock:,}")
    k3.metric("📤 Salidas (30 días)",       f"{salidas_30:,}")
    k4.metric("📥 Entradas (30 días)",      f"{entradas_30:,}")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    k5, k6, k7, k8 = st.columns(4)
    k5.metric("⚡ Salidas (7 días)",        f"{salidas_7:,}")
    k6.metric("🔕 SKUs sin mov. (30d)",     f"{skus_sin_mov:,}")

    k7.metric("⏳ SKUs sin mov. (30d)",     f"{skus_sin_mov:,}")

    # CTNs activos
    ctns_activos = int(df_sin_merma[df_sin_merma["TOTAL UNIT"] > 0]["CTN"].nunique())
    k8.metric("🚢 Contenedores en stock",   f"{ctns_activos:,}")

    st.divider()

    # ── FILA DE GRÁFICOS 1 ───────────────────────────────────────────────────
    col_izq, col_der = st.columns([3, 2])

    with col_izq:
        st.markdown(
            "<div style='font-size:11px;font-weight:700;color:#64748b;"
            "text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px'>"
            "🔥 Top 10 — Mayor Rotación (salidas 30 días)</div>",
            unsafe_allow_html=True
        )

        # Top SKUs por salidas en 30 días
        sal30 = df_30[df_30["TOTAL UNIT"] < 0].copy()
        sal30["SKU MASEF"] = sal30["SKU MASEF"].astype(str).str.strip()

        # Mapa descripción
        desc_map = (
            df[["SKU MASEF", "DESCRIPTION"]]
            .dropna()
            .query("DESCRIPTION != '' and DESCRIPTION != 'nan'")
            .drop_duplicates(subset=["SKU MASEF"])
            .set_index("SKU MASEF")["DESCRIPTION"]
        )

        top_rot = (
            sal30.groupby("SKU MASEF")["TOTAL UNIT"]
            .sum()
            .abs()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        top_rot.columns = ["SKU", "Salidas"]
        top_rot["Descripción"] = top_rot["SKU"].map(desc_map).fillna(top_rot["SKU"])
        top_rot["Label"] = top_rot.apply(
            lambda r: r["Descripción"][:30] + "…" if len(r["Descripción"]) > 30 else r["Descripción"],
            axis=1
        )

        if len(top_rot):
            fig_rot = px.bar(
                top_rot,
                x="Salidas",
                y="Label",
                orientation="h",
                color="Salidas",
                color_continuous_scale=["#bfdbfe", "#185FA5", "#0d1b2a"],
                text="Salidas",
            )
            fig_rot.update_traces(textposition="outside", textfont_size=11)
            fig_rot.update_layout(
                height=360,
                margin=dict(l=0, r=30, t=10, b=10),
                paper_bgcolor="white",
                plot_bgcolor="white",
                showlegend=False,
                coloraxis_showscale=False,
                yaxis=dict(title="", tickfont=dict(size=11)),
                xaxis=dict(title="Unidades despachadas", tickfont=dict(size=10)),
            )
            fig_rot.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_rot, use_container_width=True)
        else:
            st.info("Sin salidas registradas en los últimos 30 días.")

    with col_der:
        st.markdown(
            "<div style='font-size:11px;font-weight:700;color:#64748b;"
            "text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px'>"
            "🏷️ Distribución de Stock por Estado</div>",
            unsafe_allow_html=True
        )

        stock_estado = calcular_stock(df[df["ESTADO"] != "MERMA"], hoy)
        por_estado_pie = (
            stock_estado.groupby("ESTADO")["Stock"]
            .sum()
            .reset_index()
        )
        por_estado_pie.columns = ["Estado", "Unidades"]

        if len(por_estado_pie):
            fig_pie = px.pie(
                por_estado_pie,
                names="Estado",
                values="Unidades",
                color_discrete_sequence=["#185FA5","#3b82f6","#60a5fa","#93c5fd","#bfdbfe"],
                hole=0.5,
            )
            fig_pie.update_traces(
                textinfo="percent+label",
                textfont_size=11,
                pull=[0.03] * len(por_estado_pie)
            )
            fig_pie.update_layout(
                height=360,
                margin=dict(l=0, r=0, t=10, b=10),
                paper_bgcolor="white",
                showlegend=True,
                legend=dict(font=dict(size=10), orientation="h", y=-0.1),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    # ── FILA DE GRÁFICOS 2 ───────────────────────────────────────────────────
    col_a, col_b = st.columns([2, 3])

    with col_a:
        st.markdown(
            "<div style='font-size:11px;font-weight:700;color:#64748b;"
            "text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px'>"
            "📦 Top 10 — Mayor Stock Actual</div>",
            unsafe_allow_html=True
        )

        stock_df_dash = calcular_stock(df[df["ESTADO"] != "MERMA"], hoy)
        top_stock = (
            stock_df_dash.groupby("SKU MASEF")["Stock"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
        )
        top_stock["Descripción"] = top_stock["SKU MASEF"].map(desc_map).fillna(top_stock["SKU MASEF"])
        top_stock["Label"] = top_stock["Descripción"].apply(
            lambda x: x[:25] + "…" if len(x) > 25 else x
        )

        if len(top_stock):
            fig_stk = px.bar(
                top_stock,
                x="Stock",
                y="Label",
                orientation="h",
                color="Stock",
                color_continuous_scale=["#d1fae5","#10b981","#064e3b"],
                text="Stock",
            )
            fig_stk.update_traces(textposition="outside", textfont_size=10)
            fig_stk.update_layout(
                height=340,
                margin=dict(l=0, r=30, t=10, b=10),
                paper_bgcolor="white",
                plot_bgcolor="white",
                showlegend=False,
                coloraxis_showscale=False,
                yaxis=dict(title="", tickfont=dict(size=10)),
                xaxis=dict(title="Unidades", tickfont=dict(size=10)),
            )
            fig_stk.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_stk, use_container_width=True)

    with col_b:
        st.markdown(
            "<div style='font-size:11px;font-weight:700;color:#64748b;"
            "text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px'>"
            "📈 Evolución de Entradas vs Salidas (últimos 60 días)</div>",
            unsafe_allow_html=True
        )

        hace60 = pd.Timestamp(hoy) - pd.Timedelta(days=60)
        df_60  = df[df["FECHA"] >= hace60].copy()
        df_60["DIA"] = df_60["FECHA"].dt.date

        ent_dia = (
            df_60[df_60["TOTAL UNIT"] > 0]
            .groupby("DIA")["TOTAL UNIT"].sum()
            .reset_index()
            .rename(columns={"TOTAL UNIT": "Entradas", "DIA": "Fecha"})
        )
        sal_dia = (
            df_60[df_60["TOTAL UNIT"] < 0]
            .groupby("DIA")["TOTAL UNIT"].sum()
            .abs()
            .reset_index()
            .rename(columns={"TOTAL UNIT": "Salidas", "DIA": "Fecha"})
        )

        evol = ent_dia.merge(sal_dia, on="Fecha", how="outer").fillna(0).sort_values("Fecha")
        evol["Fecha"] = pd.to_datetime(evol["Fecha"])

        if len(evol):
            fig_ev = px.line(
                evol,
                x="Fecha",
                y=["Entradas", "Salidas"],
                color_discrete_map={"Entradas": "#185FA5", "Salidas": "#ef4444"},
                markers=True,
            )
            fig_ev.update_traces(line_width=2, marker_size=5)
            fig_ev.update_layout(
                height=340,
                margin=dict(l=0, r=20, t=10, b=10),
                paper_bgcolor="white",
                plot_bgcolor="#fafafa",
                legend=dict(
                    title="",
                    orientation="h",
                    y=1.08,
                    font=dict(size=11)
                ),
                xaxis=dict(title="", tickfont=dict(size=10), showgrid=False),
                yaxis=dict(title="Unidades", tickfont=dict(size=10), gridcolor="#f1f5f9"),
            )
            st.plotly_chart(fig_ev, use_container_width=True)

    st.divider()

    # ── ALERTAS ──────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:11px;font-weight:700;color:#64748b;"
        "text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px'>"
        "🚨 Alertas del Sistema</div>",
        unsafe_allow_html=True
    )

    alertas = []

    # SKUs sin movimiento en 30 días
    if skus_sin_mov > 0:
        alertas.append(("🔵", "Baja rotación",
                        f"{skus_sin_mov} SKU(s) en stock sin movimiento en los últimos 30 días.", "#eff6ff", "#1d4ed8"))

    # Stock bajo (< 50 unidades)
    stock_bajo = neto_global[(neto_global > 0) & (neto_global < 50)]
    if len(stock_bajo):
        alertas.append(("🔴", "Stock crítico",
                        f"{len(stock_bajo)} SKU(s) con menos de 50 unidades disponibles.", "#fef2f2", "#b91c1c"))

    if not alertas:
        st.markdown("""
        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
                    padding:16px 20px;color:#166534;font-size:13px;font-weight:500">
          ✅ Sin alertas activas. El almacén opera con normalidad.
        </div>
        """, unsafe_allow_html=True)
    else:
        cols_alerta = st.columns(len(alertas))
        for i, (icon, titulo, msg, bg, color) in enumerate(alertas):
            cols_alerta[i].markdown(
                f"""<div style="background:{bg};border-left:4px solid {color};
                                border-radius:8px;padding:14px 16px;height:100%">
                      <div style="font-size:11px;font-weight:700;color:{color};
                                  text-transform:uppercase;letter-spacing:.06em;
                                  margin-bottom:4px">{icon} {titulo}</div>
                      <div style="font-size:13px;color:#1e293b;font-weight:500">{msg}</div>
                    </div>""",
                unsafe_allow_html=True
            )

# ══════════════════════════════════════════════════════════════════════════════
# VISTA: STOCK
# ══════════════════════════════════════════════════════════════════════════════

elif vista == "📦  Stock":

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

    # ── Filtro Proveedor (fuera del form para reactividad) ──
    if col_proveedor_pk:
        provs_stock_opts = ["Todos"] + sorted(
            packing_df[col_proveedor_pk]
            .dropna().astype(str).str.strip()
            .unique().tolist()
        )
        st.markdown('<div class="filtro-prov-wrap">', unsafe_allow_html=True)
        f_prov_stock = st.selectbox("🏭 Proveedor", provs_stock_opts, key="prov_stock")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        f_prov_stock = "Todos"

    # CTNs disponibles según proveedor seleccionado
    if f_prov_stock != "Todos" and col_proveedor_pk:
        ctns_del_prov = (
            packing_df[packing_df[col_proveedor_pk].astype(str).str.strip() == f_prov_stock]
            [col_ctn_pk].astype(str).str.strip().unique().tolist()
        )
        ctns_opts_stock = ["Todos"] + sorted(
            c for c in df["CTN"].dropna().astype(str).unique() if c in ctns_del_prov
        )
    else:
        ctns_opts_stock = ["Todos"] + sorted(df["CTN"].dropna().astype(str).unique().tolist())

    # ── Filtros ──
    with st.form("form_stock"):

        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])

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

            f_ctn_stock = st.selectbox(
                "📦 Contenedor",
                ctns_opts_stock
            )

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

    # ── Filtro CTN ──
    if f_ctn_stock != "Todos":

        stock_df = stock_df[
            stock_df["CTN"] == f_ctn_stock
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

    # ── Merge con PACKINGLIST para traer CASE PACK IN (presentación) + PROVEEDOR ──
    pk_presentacion = _build_pk_aux(["CASE PACK IN", col_proveedor_pk])
    if "CASE PACK IN" in pk_presentacion.columns:
        pk_presentacion["CASE PACK IN"] = pd.to_numeric(
            pk_presentacion["CASE PACK IN"], errors="coerce"
        )

    stock_df = stock_df.merge(pk_presentacion, on=["CTN", "SKU MASEF"], how="left")

    # ── Filtro Proveedor ──
    if f_prov_stock != "Todos" and col_proveedor_pk and col_proveedor_pk in stock_df.columns:
        stock_df = stock_df[
            stock_df[col_proveedor_pk].astype(str).str.strip() == f_prov_stock
        ]

    # ── Columnas para display ──
    cols_display_stock = ["SKU MASEF", "DESCRIPTION", "CTN", "ESTADO", "FECHA VCTO"]
    rename_stock = {
        "SKU MASEF":   "SKU",
        "DESCRIPTION": "Descripción",
        "FECHA VCTO":  "Vencimiento",
        "Stock":       "Unidades en Stock",
    }
    if col_proveedor_pk and col_proveedor_pk in stock_df.columns:
        cols_display_stock.append(col_proveedor_pk)
        rename_stock[col_proveedor_pk] = "Proveedor"
    if "CASE PACK IN" in stock_df.columns:
        cols_display_stock.append("CASE PACK IN")
        rename_stock["CASE PACK IN"] = "Presentación"
    cols_display_stock.append("Stock")

    display = stock_df[cols_display_stock].rename(columns=rename_stock)

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

    # ── Filtro Proveedor (fuera del form para reactividad) ──
    if col_proveedor_pk:
        provs_traz_opts = ["Todos"] + sorted(
            packing_df[col_proveedor_pk]
            .dropna().astype(str).str.strip()
            .unique().tolist()
        )
        st.markdown('<div class="filtro-prov-wrap">', unsafe_allow_html=True)
        f_prov_traz = st.selectbox("🏭 Proveedor", provs_traz_opts, key="prov_traz")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        f_prov_traz = "Todos"

    # CTNs disponibles según proveedor seleccionado
    if f_prov_traz != "Todos" and col_proveedor_pk:
        ctns_del_prov_traz = (
            packing_df[packing_df[col_proveedor_pk].astype(str).str.strip() == f_prov_traz]
            [col_ctn_pk].astype(str).str.strip().unique().tolist()
        )
        ctns_opts_traz = ["Todos"] + sorted(
            c for c in df["CTN"].dropna().astype(str).unique() if c in ctns_del_prov_traz
        )
    else:
        ctns_opts_traz = ["Todos"] + sorted(df["CTN"].dropna().astype(str).unique().tolist())

    with st.form("form_trazabilidad"):

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            f_ctn = st.selectbox("📦 Contenedor", ctns_opts_traz)

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

        with col4:

            estados_traz = ["Todos"] + sorted(
                df["ESTADO"]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            f_estado_traz = st.selectbox("🏷️ Estado", estados_traz)

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

    if f_estado_traz != "Todos":
        traz = traz[traz["ESTADO"] == f_estado_traz]

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

    # ── Merge con PACKINGLIST para traer CASE PACK IN (presentación) + PROVEEDOR ──
    pk_pres_traz = _build_pk_aux(["CASE PACK IN", col_proveedor_pk])
    if "CASE PACK IN" in pk_pres_traz.columns:
        pk_pres_traz["CASE PACK IN"] = pd.to_numeric(pk_pres_traz["CASE PACK IN"], errors="coerce")

    traz["CTN"]       = traz["CTN"].astype(str).str.strip()
    traz["SKU MASEF"] = traz["SKU MASEF"].astype(str).str.strip()

    traz = traz.merge(pk_pres_traz, on=["CTN", "SKU MASEF"], how="left")

    # ── Filtro Proveedor ──
    if f_prov_traz != "Todos" and col_proveedor_pk and col_proveedor_pk in traz.columns:
        traz = traz[traz[col_proveedor_pk].astype(str).str.strip() == f_prov_traz]

    traz_display = traz.copy()

    for col in traz_display.columns:

        if "FECHA" in col.upper():

            try:
                traz_display[col] = pd.to_datetime(
                    traz_display[col], errors="coerce"
                ).dt.strftime("%Y-%m-%d")
            except:
                pass

    # Reordenar: Presentación y Proveedor justo después de SKU MASEF
    rename_traz = {}
    cols_t = list(traz_display.columns)
    insert_after = cols_t.index("SKU MASEF") + 1 if "SKU MASEF" in cols_t else len(cols_t)
    for col_extra, label in [("CASE PACK IN", "Presentación"), (col_proveedor_pk, "Proveedor")]:
        if col_extra and col_extra in cols_t:
            cols_t.remove(col_extra)
            cols_t.insert(insert_after, col_extra)
            rename_traz[col_extra] = label
            insert_after += 1
    traz_display = traz_display[cols_t].rename(columns=rename_traz)

    st.dataframe(
        traz_display,
        use_container_width=True,
        hide_index=True
    )

    botones_descarga(traz_display, "trazabilidad")


# ══════════════════════════════════════════════════════════════════════════════
# VISTA: DESPACHOS
# ══════════════════════════════════════════════════════════════════════════════

elif vista == "🚚  Despachos":

    st.markdown(f"""
    <div class="wms-header">
      <div style="font-size:32px">🚚</div>
      <div>
        <h1>Reporte de Despachos</h1>
        <p>Movimientos de tipo SALIDA registrados en el sistema</p>
      </div>
      <span class="wms-badge">Salidas</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Filtro Proveedor (fuera del form para reactividad) ──
    if col_proveedor_pk:
        provs_desp_opts = ["Todos"] + sorted(
            packing_df[col_proveedor_pk]
            .dropna().astype(str).str.strip()
            .unique().tolist()
        )
        st.markdown('<div class="filtro-prov-wrap">', unsafe_allow_html=True)
        f_prov_desp = st.selectbox("🏭 Proveedor", provs_desp_opts, key="prov_desp")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        f_prov_desp = "Todos"

    # CTNs disponibles según proveedor seleccionado
    if f_prov_desp != "Todos" and col_proveedor_pk:
        ctns_del_prov_desp = (
            packing_df[packing_df[col_proveedor_pk].astype(str).str.strip() == f_prov_desp]
            [col_ctn_pk].astype(str).str.strip().unique().tolist()
        )
        ctns_opts_desp = ["Todos"] + sorted(
            c for c in df["CTN"].dropna().astype(str).unique() if c in ctns_del_prov_desp
        )
    else:
        ctns_opts_desp = ["Todos"] + sorted(df["CTN"].dropna().astype(str).unique().tolist())

    # ── Filtros ──
    with st.form("form_despachos"):

        col1, col2, col3 = st.columns(3)

        with col1:
            f_ctn_d = st.selectbox("📦 Contenedor", ctns_opts_desp)

        with col2:
            skus_d = ["Todos"] + sorted(
                df["SKU MASEF"].dropna().astype(str).unique().tolist()
            )
            f_sku_d = st.selectbox("🏷️ SKU", skus_d)

        with col3:
            guias_d = ["Todos"] + sorted(
                df[df["TIPO DE MOVIMIENTO"] == "SALIDA"]["GUIA"]
                .dropna().astype(str)
                .unique().tolist()
            )
            f_guia_d = st.selectbox("📄 Guía", guias_d)

        col4, col5 = st.columns(2)

        with col4:
            fecha_desde_d = st.date_input(
                "📅 Desde",
                value=df["FECHA"].min().date()
            )

        with col5:
            fecha_hasta_d = st.date_input(
                "📅 Hasta",
                value=date.today()
            )

        st.form_submit_button("🔍 Buscar", use_container_width=True)

    # ── Filtrar solo SALIDAS ──
    desp = df[df["TIPO DE MOVIMIENTO"] == "SALIDA"].copy()

    if f_ctn_d != "Todos":
        desp = desp[desp["CTN"] == f_ctn_d]

    if f_sku_d != "Todos":
        desp = desp[desp["SKU MASEF"] == f_sku_d]

    if f_guia_d != "Todos":
        desp = desp[desp["GUIA"].astype(str) == f_guia_d]

    desp = desp[
        (desp["FECHA"].dt.date >= fecha_desde_d) &
        (desp["FECHA"].dt.date <= fecha_hasta_d)
    ]

    desp = desp.sort_values("FECHA", ascending=False)

    # Quitar columna OBS
    cols_excluir = [c for c in desp.columns if c.upper() in ["OBS", "OBSERVACION", "OBSERVACIONES"]]
    desp = desp.drop(columns=cols_excluir, errors="ignore")

    # ── Merge con PACKINGLIST para traer CASE PACK IN (presentación) + PROVEEDOR ──
    pk_pres_desp = _build_pk_aux(["CASE PACK IN", col_proveedor_pk])
    if "CASE PACK IN" in pk_pres_desp.columns:
        pk_pres_desp["CASE PACK IN"] = pd.to_numeric(pk_pres_desp["CASE PACK IN"], errors="coerce")

    desp["CTN"]       = desp["CTN"].astype(str).str.strip()
    desp["SKU MASEF"] = desp["SKU MASEF"].astype(str).str.strip()

    desp = desp.merge(pk_pres_desp, on=["CTN", "SKU MASEF"], how="left")

    # ── Filtro Proveedor ──
    if f_prov_desp != "Todos" and col_proveedor_pk and col_proveedor_pk in desp.columns:
        desp = desp[desp[col_proveedor_pk].astype(str).str.strip() == f_prov_desp]

    # ── Métricas ──
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🚚 Despachos",         f"{len(desp):,}")
    m2.metric("🏷️ SKUs despachados",  f"{desp['SKU MASEF'].nunique():,}")
    m3.metric("📄 Guías",             f"{desp['GUIA'].nunique():,}" if "GUIA" in desp.columns else "—")
    m4.metric("📦 Unidades salidas",  f"{int(desp['TOTAL UNIT'].sum() * -1):,}")

    st.divider()

    # ── Tabla con fechas formateadas ──
    desp_display = desp.copy()
    for col in desp_display.columns:
        if "FECHA" in col.upper():
            try:
                desp_display[col] = pd.to_datetime(
                    desp_display[col], errors="coerce"
                ).dt.strftime("%d/%m/%Y").fillna("")
            except:
                pass

    # Reordenar: Presentación y Proveedor justo después de SKU MASEF
    rename_desp = {}
    cols_d = list(desp_display.columns)
    insert_after_d = cols_d.index("SKU MASEF") + 1 if "SKU MASEF" in cols_d else len(cols_d)
    for col_extra, label in [("CASE PACK IN", "Presentación"), (col_proveedor_pk, "Proveedor")]:
        if col_extra and col_extra in cols_d:
            cols_d.remove(col_extra)
            cols_d.insert(insert_after_d, col_extra)
            rename_desp[col_extra] = label
            insert_after_d += 1
    desp_display = desp_display[cols_d].rename(columns=rename_desp)

    st.markdown(
        f"""<div style='display:flex;align-items:center;justify-content:space-between;
                        margin-bottom:8px'>
              <span style='font-size:13px;font-weight:700;color:#1e293b'>
                Detalle de despachos
              </span>
              <span style='background:#eff6ff;color:#185FA5;font-size:11px;
                           font-weight:700;padding:3px 10px;border-radius:12px;
                           border:1px solid #bfdbfe'>
                {len(desp_display)} registros
              </span>
            </div>""",
        unsafe_allow_html=True
    )

    st.dataframe(desp_display, use_container_width=True, hide_index=True)

    # ── Solo Excel ──
    st.markdown(
        "<div style='font-size:10px;font-weight:700;color:#94a3b8;"
        "text-transform:uppercase;letter-spacing:.08em;margin:16px 0 6px'>Exportar</div>",
        unsafe_allow_html=True
    )
    col_x, col_sp = st.columns([1, 4])
    with col_x:
        st.download_button(
            "📊 Excel",
            to_excel(desp_display),
            f"despachos_{date.today().strftime('%d-%m-%Y')}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

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

        # ── Fila 2: Proveedor ──
        if col_proveedor_pk:
            provs_pk_opts = ["Todos"] + sorted(
                packing_df[col_proveedor_pk]
                .dropna().astype(str).str.strip()
                .unique().tolist()
            )
            f_prov_pk = st.selectbox("🏭 Proveedor", provs_pk_opts)
        else:
            f_prov_pk = "Todos"

        st.form_submit_button(
            "🔍 Buscar",
            use_container_width=True
        )

    pk = packing_df.copy()

    if f_ctn != "Todos":
        pk = pk[pk[col_ctn].astype(str) == str(f_ctn)]

    if f_sku != "Todos":
        pk = pk[pk[col_sku].astype(str) == str(f_sku)]

    if f_prov_pk != "Todos" and col_proveedor_pk and col_proveedor_pk in pk.columns:
        pk = pk[pk[col_proveedor_pk].astype(str).str.strip() == f_prov_pk]

    # Detectar columna OBS y asegurarse que se muestre
    col_obs_pk = next(
        (c for c in pk.columns if c.upper() in ["OBS", "OBSERVACION", "OBSERVACIONES", "OBSERVACIÓN"]),
        None
    )

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

    # ── Filtro Proveedor (fuera del form para reactividad) ──
    if col_proveedor_pk:
        provs_merma_opts = ["Todos"] + sorted(
            packing_df[col_proveedor_pk]
            .dropna().astype(str).str.strip()
            .unique().tolist()
        )
        st.markdown('<div class="filtro-prov-wrap">', unsafe_allow_html=True)
        f_prov_merma = st.selectbox("🏭 Proveedor", provs_merma_opts, key="prov_merma")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        f_prov_merma = "Todos"

    # CTNs de merma filtrados por proveedor
    ctns_merma_base = (
        df[df["ESTADO"] == "MERMA"]["CTN"]
        .dropna().astype(str).unique().tolist()
    )
    if f_prov_merma != "Todos" and col_proveedor_pk:
        ctns_del_prov_merma = (
            packing_df[packing_df[col_proveedor_pk].astype(str).str.strip() == f_prov_merma]
            [col_ctn_pk].astype(str).str.strip().unique().tolist()
        )
        ctns_merma_opts = ["Todos"] + sorted(c for c in ctns_merma_base if c in ctns_del_prov_merma)
    else:
        ctns_merma_opts = ["Todos"] + sorted(ctns_merma_base)

    # ── Filtros en form ──
    with st.form("form_merma"):

        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])

        with col1:
            fecha_corte_merma = st.date_input(
                "📅 Fecha de corte",
                value=date.today()
            )

        with col2:
            buscar_merma = st.text_input(
                "🔎 Buscar SKU o descripción"
            )

        with col3:
            estados_merma_opts = ["Todos"] + sorted(
                df[df["ESTADO"] == "MERMA"]["ESTADO"]
                .dropna().astype(str).unique().tolist()
            )
            f_estado_merma = st.selectbox("🏷️ Estado", estados_merma_opts)

        with col4:
            f_ctn_merma = st.selectbox("📦 Contenedor", ctns_merma_opts)

        st.form_submit_button("🔍 Buscar", use_container_width=True)

    # ── SOLO MERMA ──
    merma_df = calcular_stock(
        df[df["ESTADO"] == "MERMA"],
        fecha_corte_merma
    )

    if buscar_merma:
        mask = (
            merma_df["SKU MASEF"].str.contains(buscar_merma, case=False, na=False)
            | merma_df["DESCRIPTION"].str.contains(buscar_merma, case=False, na=False)
        )
        merma_df = merma_df[mask]

    if f_estado_merma != "Todos":
        merma_df = merma_df[merma_df["ESTADO"] == f_estado_merma]

    if f_ctn_merma != "Todos":
        merma_df = merma_df[merma_df["CTN"] == f_ctn_merma]

    # ── Merge con PACKINGLIST para traer PROVEEDOR ──
    pk_merma = _build_pk_aux([col_proveedor_pk])
    merma_df["CTN"]       = merma_df["CTN"].astype(str).str.strip()
    merma_df["SKU MASEF"] = merma_df["SKU MASEF"].astype(str).str.strip()
    merma_df = merma_df.merge(pk_merma, on=["CTN", "SKU MASEF"], how="left")

    if f_prov_merma != "Todos" and col_proveedor_pk and col_proveedor_pk in merma_df.columns:
        merma_df = merma_df[merma_df[col_proveedor_pk].astype(str).str.strip() == f_prov_merma]

    total_merma = int(merma_df["Stock"].sum()) if len(merma_df) else 0

    m1, m2 = st.columns(2)
    m1.metric("Total merma",    f"{total_merma:,}")
    m2.metric("SKUs con merma", f"{len(merma_df):,}")

    st.divider()

    cols_merma_display = ["SKU MASEF", "DESCRIPTION", "CTN", "ESTADO", "FECHA VCTO"]
    rename_merma = {
        "SKU MASEF":   "SKU",
        "DESCRIPTION": "Descripción",
        "FECHA VCTO":  "Vencimiento",
        "Stock":       "Unidades",
    }
    if col_proveedor_pk and col_proveedor_pk in merma_df.columns:
        cols_merma_display.append(col_proveedor_pk)
        rename_merma[col_proveedor_pk] = "Proveedor"
    cols_merma_display.append("Stock")

    display = merma_df[cols_merma_display].rename(columns=rename_merma)

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
# VISTA: DESPACHO OPERATIVO
# ══════════════════════════════════════════════════════════════════════════════

elif vista == "🛒  Despacho Operativo":

    st.markdown(f"""
    <div class="wms-header">
      <div style="font-size:32px">🛒</div>
      <div>
        <h1>Despacho Operativo</h1>
        <p>Registrar salidas de stock directamente al sistema</p>
      </div>
      <span class="wms-badge">Operación</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Inicializar session state ──────────────────────────────────────────────
    for _k, _v in [
        ("desp_op_paso",    1),        # 1 = cabecera, 2 = búsqueda/carrito
        ("desp_op_fecha",   date.today()),
        ("desp_op_guia",    ""),
        ("desp_op_cliente", ""),
        ("desp_op_obs",     ""),
        ("desp_op_items",   []),
        ("desp_op_exito",   False),
    ]:
        if _k not in st.session_state:
            st.session_state[_k] = _v

    # ── Función reset total ────────────────────────────────────────────────────
    def reset_desp_op():
        st.session_state["desp_op_paso"]    = 1
        st.session_state["desp_op_fecha"]   = date.today()
        st.session_state["desp_op_guia"]    = ""
        st.session_state["desp_op_cliente"] = ""
        st.session_state["desp_op_obs"]     = ""
        st.session_state["desp_op_items"]   = []
        st.session_state["desp_op_exito"]   = False

    # ── Función insertar en Sheets ─────────────────────────────────────────────
    def insertar_salidas(filas: list) -> bool:
        try:
            client  = get_client()
            sh      = client.open_by_key(st.secrets["spreadsheet_id"])
            ws      = sh.worksheet(SHEET_NAME)
            ws.append_rows(filas, value_input_option="USER_ENTERED")
            return True
        except Exception as e:
            st.error(f"❌ Error al guardar en Google Sheets: {e}")
            return False

    # ══════════════════════════════════════════════════════════════════════════
    # PASO 1 — Datos del pedido
    # ══════════════════════════════════════════════════════════════════════════
    if st.session_state["desp_op_paso"] == 1:

        st.markdown("""
        <div style="background:#eff6ff;border-left:4px solid #185FA5;border-radius:6px;
                    padding:10px 16px;font-size:13px;color:#1e40af;margin-bottom:16px">
          <b>Paso 1 de 2</b> — Completa los datos del despacho y luego continúa para agregar productos.
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            "<div style='font-size:11px;font-weight:700;color:#64748b;"
            "text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px'>"
            "📋 Datos del despacho</div>",
            unsafe_allow_html=True
        )

        with st.form("form_desp_cabecera"):
            c1, c2 = st.columns(2)
            with c1:
                inp_fecha   = st.date_input("📅 Fecha de salida",        value=st.session_state["desp_op_fecha"])
                inp_cliente = st.text_input("👤 Cliente",                 value=st.session_state["desp_op_cliente"], placeholder="Nombre del cliente")
            with c2:
                inp_guia    = st.text_input("📄 N° de Guía / Referencia", value=st.session_state["desp_op_guia"],    placeholder="Ej: GR-2026-001")
                inp_obs     = st.text_input("💬 Observación (opcional)",  value=st.session_state["desp_op_obs"],     placeholder="Ej: Pedido urgente")

            continuar = st.form_submit_button("➡️  Continuar — Agregar productos", use_container_width=True)

        if continuar:
            if not inp_guia.strip():
                st.warning("⚠️ Debes ingresar un N° de Guía / Referencia.")
            elif not inp_cliente.strip():
                st.warning("⚠️ Debes ingresar el nombre del cliente.")
            else:
                st.session_state["desp_op_fecha"]   = inp_fecha
                st.session_state["desp_op_guia"]    = inp_guia.strip()
                st.session_state["desp_op_cliente"] = inp_cliente.strip()
                st.session_state["desp_op_obs"]     = inp_obs.strip()
                st.session_state["desp_op_paso"]    = 2
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # PASO 2 — Búsqueda de productos + carrito
    # ══════════════════════════════════════════════════════════════════════════
    else:

        # ── Banner resumen del pedido (fijo, siempre visible) ─────────────────
        items_count = len(st.session_state["desp_op_items"])
        total_u     = sum(i["cantidad"] for i in st.session_state["desp_op_items"])
        st.markdown(f"""
        <div style="background:#0d1b2a;border-radius:10px;padding:14px 20px;
                    margin-bottom:16px;display:flex;gap:24px;align-items:center;
                    box-shadow:0 2px 8px rgba(0,0,0,0.15)">
          <div>
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.08em">Guía</div>
            <div style="font-size:14px;font-weight:700;color:#e2e8f0">{st.session_state['desp_op_guia']}</div>
          </div>
          <div>
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.08em">Cliente</div>
            <div style="font-size:14px;font-weight:700;color:#e2e8f0">{st.session_state['desp_op_cliente']}</div>
          </div>
          <div>
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.08em">Fecha</div>
            <div style="font-size:14px;font-weight:700;color:#e2e8f0">{st.session_state['desp_op_fecha'].strftime('%d/%m/%Y')}</div>
          </div>
          <div style="margin-left:auto;text-align:right">
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.08em">Productos / Unidades</div>
            <div style="font-size:16px;font-weight:700;color:#60a5fa">{items_count} ítems &nbsp;·&nbsp; {total_u:,} u.</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Calcular stock actual ─────────────────────────────────────────────
        stock_op = calcular_stock(df[df["ESTADO"] != "MERMA"], date.today())
        pk_op    = _build_pk_aux(["CASE PACK IN", col_proveedor_pk])
        stock_op["CTN"]       = stock_op["CTN"].astype(str).str.strip()
        stock_op["SKU MASEF"] = stock_op["SKU MASEF"].astype(str).str.strip()
        stock_op = stock_op.merge(pk_op, on=["CTN", "SKU MASEF"], how="left")

        # ── Buscador ──────────────────────────────────────────────────────────
        st.markdown(
            "<div style='font-size:11px;font-weight:700;color:#64748b;"
            "text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px'>"
            "🔎 Buscar y agregar productos</div>",
            unsafe_allow_html=True
        )

        buscar_op = st.text_input(
            "",
            placeholder="Escribe el código SKU o la descripción del producto…",
            key="buscar_op",
            label_visibility="collapsed"
        )

        # ── Resultados ────────────────────────────────────────────────────────
        if buscar_op.strip():
            mask_op = (
                stock_op["SKU MASEF"].str.contains(buscar_op, case=False, na=False)
                | stock_op["DESCRIPTION"].str.contains(buscar_op, case=False, na=False)
            )
            resultados = stock_op[mask_op].copy()

            if resultados.empty:
                st.info("Sin resultados para esa búsqueda.")
            else:
                st.markdown(
                    f"<div style='font-size:12px;color:#64748b;margin-bottom:10px'>"
                    f"{len(resultados)} resultado(s)</div>",
                    unsafe_allow_html=True
                )

                for _, row in resultados.iterrows():
                    sku        = str(row["SKU MASEF"])
                    desc       = str(row.get("DESCRIPTION", ""))
                    ctn        = str(row["CTN"])
                    estado     = str(row["ESTADO"])
                    stock_disp = int(row["Stock"])
                    vcto       = str(row.get("FECHA VCTO", "")) or "—"
                    prov       = str(row.get(col_proveedor_pk, "")) if col_proveedor_pk else ""
                    item_key   = f"{sku}||{ctn}||{estado}||{vcto}"

                    ya_en_carrito = any(
                        it["key"] == item_key for it in st.session_state["desp_op_items"]
                    )

                    st.markdown(f"""
                    <div class="desp-card">
                      <div class="desp-sku">{sku}</div>
                      <div class="desp-desc">{desc}</div>
                      <div class="desp-meta">
                        📦 CTN: <b>{ctn}</b> &nbsp;|&nbsp;
                        🏷️ Estado: <b>{estado}</b> &nbsp;|&nbsp;
                        📅 Vcto: <b>{vcto}</b>
                        {"&nbsp;|&nbsp; 🏭 " + prov if prov and prov not in ("nan","") else ""}
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    rc1, rc2, rc3 = st.columns([3, 1, 1])
                    with rc1:
                        st.markdown(
                            f"<div class='desp-stock' style='margin-top:6px'>"
                            f"✅ Stock disponible: <b>{stock_disp:,}</b> unidades</div>",
                            unsafe_allow_html=True
                        )
                    with rc2:
                        cantidad = st.number_input(
                            "Cantidad", min_value=1, max_value=stock_disp,
                            value=1, step=1,
                            key=f"cant_{item_key}",
                            label_visibility="collapsed"
                        )
                    with rc3:
                        if ya_en_carrito:
                            st.button("✅ Agregado", key=f"btn_{item_key}", disabled=True, use_container_width=True)
                        else:
                            if st.button("➕ Agregar", key=f"btn_{item_key}", use_container_width=True):
                                st.session_state["desp_op_items"].append({
                                    "key":         item_key,
                                    "SKU MASEF":   sku,
                                    "DESCRIPTION": desc,
                                    "CTN":         ctn,
                                    "ESTADO":      estado,
                                    "FECHA VCTO":  vcto if vcto != "—" else "",
                                    "cantidad":    cantidad,
                                })
                                st.rerun()

        # ── Carrito ───────────────────────────────────────────────────────────
        if st.session_state["desp_op_items"]:
            st.divider()
            st.markdown(
                f"<div style='font-size:11px;font-weight:700;color:#64748b;"
                f"text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px'>"
                f"🛒 Carrito — {len(st.session_state['desp_op_items'])} ítem(s)</div>",
                unsafe_allow_html=True
            )

            total_units = 0
            to_remove   = None

            for idx, item in enumerate(st.session_state["desp_op_items"]):
                ci1, ci2, ci3, ci4 = st.columns([4, 1, 1, 1])
                with ci1:
                    st.markdown(
                        f"<div style='font-size:13px;font-weight:600;color:#0f172a'>{item['DESCRIPTION']}</div>"
                        f"<div style='font-size:11px;color:#64748b'>"
                        f"{item['SKU MASEF']} — CTN {item['CTN']} — {item['ESTADO']}</div>",
                        unsafe_allow_html=True
                    )
                with ci2:
                    nueva_cant = st.number_input(
                        "Cant.", min_value=1, value=item["cantidad"], step=1,
                        key=f"edit_cant_{idx}", label_visibility="collapsed"
                    )
                    st.session_state["desp_op_items"][idx]["cantidad"] = nueva_cant
                with ci3:
                    st.markdown(
                        f"<div style='font-size:13px;font-weight:700;color:#185FA5;margin-top:6px'>"
                        f"−{nueva_cant:,} u.</div>",
                        unsafe_allow_html=True
                    )
                with ci4:
                    if st.button("🗑️", key=f"rm_{idx}", help="Quitar", use_container_width=True):
                        to_remove = idx
                total_units += nueva_cant

            if to_remove is not None:
                st.session_state["desp_op_items"].pop(to_remove)
                st.rerun()

            st.markdown(
                f"<div style='text-align:right;font-size:15px;font-weight:700;color:#0f172a;"
                f"background:#f8fafc;border-radius:8px;padding:10px 16px;margin:8px 0'>"
                f"Total a despachar: {total_units:,} unidades</div>",
                unsafe_allow_html=True
            )

            # ── Botones acción ────────────────────────────────────────────────
            col_conf, col_volver, col_can = st.columns([3, 1, 1])

            with col_conf:
                if st.button("✅  Confirmar y registrar salida", use_container_width=True, type="primary"):

                    # Guard: evitar doble inserción
                    if st.session_state.get("desp_op_procesando"):
                        st.warning("⏳ Ya se está procesando, espera un momento.")
                    else:
                        st.session_state["desp_op_procesando"] = True

                        try:
                            client_tmp = get_client()
                            sh_tmp     = client_tmp.open_by_key(st.secrets["spreadsheet_id"])
                            ws_tmp     = sh_tmp.worksheet(SHEET_NAME)
                            headers    = ws_tmp.row_values(1)
                        except Exception as e:
                            st.error(f"❌ No se pudo leer la hoja: {e}")
                            headers = []
                            st.session_state["desp_op_procesando"] = False

                        if headers:
                            # FECHA siempre DD/MM/YYYY como texto plano
                            fecha_str   = st.session_state["desp_op_fecha"].strftime("%d/%m/%Y")
                            guia_str    = st.session_state["desp_op_guia"]
                            cliente_str = st.session_state["desp_op_cliente"]
                            obs_str     = st.session_state["desp_op_obs"]
                            filas_a_insertar = []

                            for item in st.session_state["desp_op_items"]:
                                # Normalizar FECHA VCTO a DD/MM/YYYY
                                vcto_raw = item.get("FECHA VCTO", "")
                                if vcto_raw and vcto_raw not in ("", "—", "nan"):
                                    try:
                                        vcto_str = pd.to_datetime(vcto_raw, dayfirst=False, errors="coerce")
                                        vcto_str = vcto_str.strftime("%d/%m/%Y") if not pd.isna(vcto_str) else vcto_raw
                                    except:
                                        vcto_str = vcto_raw
                                else:
                                    vcto_str = ""

                                fila = []
                                for h in headers:
                                    h_up = h.upper().strip()
                                    if h_up == "FECHA":
                                        fila.append(fecha_str)
                                    elif h_up == "CTN":
                                        fila.append(item["CTN"])
                                    elif h_up in ("SKU MASEF", "SKU"):
                                        fila.append(item["SKU MASEF"])
                                    elif h_up in ("DESCRIPTION", "DESCRIPCION", "DESCRIPCIÓN"):
                                        fila.append(item["DESCRIPTION"])
                                    elif h_up == "ESTADO":
                                        fila.append(item["ESTADO"])
                                    elif h_up in ("FECHA VCTO", "FECHA VENCIMIENTO", "VENCIMIENTO"):
                                        fila.append(vcto_str)
                                    elif h_up in ("TIPO DE MOVIMIENTO", "TIPO MOVIMIENTO", "MOVIMIENTO"):
                                        fila.append("SALIDA")
                                    elif h_up in ("TOTAL UNIT", "CANTIDAD", "UNITS"):
                                        fila.append(-abs(item["cantidad"]))
                                    elif h_up in ("GUIA", "GUÍA", "N° GUIA", "NUMERO GUIA"):
                                        fila.append(guia_str)
                                    elif h_up in ("CLIENTE", "CLIENT", "TIENDA"):
                                        fila.append(cliente_str)
                                    elif h_up in ("OBS", "OBSERVACION", "OBSERVACIONES", "OBSERVACIÓN"):
                                        fila.append(obs_str)
                                    else:
                                        fila.append("")
                                filas_a_insertar.append(fila)

                            ok = insertar_salidas(filas_a_insertar)
                            st.session_state["desp_op_procesando"] = False
                            if ok:
                                st.cache_data.clear()
                                reset_desp_op()
                                st.session_state["desp_op_exito"] = True
                                st.rerun()

            with col_volver:
                if st.button("✏️  Editar cabecera", use_container_width=True):
                    st.session_state["desp_op_paso"] = 1
                    st.rerun()

            with col_can:
                if st.button("🗑️  Cancelar todo", use_container_width=True):
                    reset_desp_op()
                    st.rerun()

        else:
            # Sin ítems en carrito — opción de volver
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button("← Volver a datos del despacho", use_container_width=False):
                st.session_state["desp_op_paso"] = 1
                st.rerun()

    # ── Mensaje de éxito (se muestra en Paso 1, tras el reset) ────────────────
    if st.session_state.get("desp_op_exito") and st.session_state["desp_op_paso"] == 1:
        st.session_state["desp_op_exito"] = False
        st.success("✅ Salida registrada correctamente. El stock ha sido actualizado.")


# ══════════════════════════════════════════════════════════════════════════════
# VISTA: CARGA PACKING LIST
# ══════════════════════════════════════════════════════════════════════════════

elif vista == "📥  Carga Packing List":

    st.markdown(f"""
    <div class="wms-header">
      <div style="font-size:32px">📥</div>
      <div>
        <h1>Carga de Packing List</h1>
        <p>Importa un Excel con el detalle del contenedor para registrarlo en el sistema</p>
      </div>
      <span class="wms-badge">Ingreso</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Cabeceras de la sheet PACKINGLIST ─────────────────────────────────────
    COLS_INPUT = [
        "SKU MASEF", "DESCRIPCIÓN", "Proveedor", "CTN",
        "CASE QTY PL", "CASE PACK PL", "QTY PL",
        "CASE QTY IN", "CASE PACK IN", "QTY IN",
        "FECH ING", "OBS"
    ]
    COLS_SHEET = COLS_INPUT + ["DIF CAJAS", "DIF UNI", "ESTADO"]

    # ── Descargable: plantilla con ejemplo ────────────────────────────────────
    def generar_plantilla() -> bytes:
        ejemplo = {
            "SKU MASEF":    ["1030013"],
            "DESCRIPCIÓN":  ["NUTELLA B READY 22 GR 0.7OZ"],
            "Proveedor":    ["Importación"],
            "CTN":          ["12341"],
            "CASE QTY PL":  [50],
            "CASE PACK PL": [36],
            "QTY PL":       [1800],
            "CASE QTY IN":  [49],
            "CASE PACK IN": [36],
            "QTY IN":       [1796],
            "FECH ING":     ["24/3/2026"],
            "OBS":          ["4un faltante post maquila"],
        }
        df_tmpl = pd.DataFrame(ejemplo)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df_tmpl.to_excel(w, index=False, sheet_name="PackingList")
        return buf.getvalue()

    col_dl, col_sp = st.columns([1, 3])
    with col_dl:
        st.download_button(
            "📄  Descargar plantilla",
            generar_plantilla(),
            "plantilla_packinglist.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.divider()

    # ── Carga del archivo ─────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:11px;font-weight:700;color:#64748b;"
        "text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px'>"
        "📂 Selecciona el archivo Excel a cargar</div>",
        unsafe_allow_html=True
    )

    archivo = st.file_uploader(
        "", type=["xlsx", "xls"],
        label_visibility="collapsed",
        key="uploader_pl"
    )

    if archivo:
        try:
            df_up = pd.read_excel(archivo, dtype=str)
            df_up.columns = df_up.columns.str.strip()
        except Exception as e:
            st.error(f"❌ Error leyendo el archivo: {e}")
            st.stop()

        # Verificar columnas mínimas requeridas
        cols_faltantes = [c for c in COLS_INPUT if c not in df_up.columns]
        if cols_faltantes:
            st.error(f"❌ Faltan columnas en el archivo: {cols_faltantes}")
            st.stop()

        # Calcular diferencias y agregar columnas automáticas
        df_up["CASE QTY PL"] = pd.to_numeric(df_up["CASE QTY PL"], errors="coerce").fillna(0)
        df_up["CASE QTY IN"] = pd.to_numeric(df_up["CASE QTY IN"], errors="coerce").fillna(0)
        df_up["QTY PL"]      = pd.to_numeric(df_up["QTY PL"],      errors="coerce").fillna(0)
        df_up["QTY IN"]      = pd.to_numeric(df_up["QTY IN"],       errors="coerce").fillna(0)

        df_up["DIF CAJAS"] = (df_up["CASE QTY IN"] - df_up["CASE QTY PL"]).astype(int)
        df_up["DIF UNI"]   = (df_up["QTY IN"]      - df_up["QTY PL"]).astype(int)
        df_up["ESTADO"]    = "EN REVISION"

        # Preview
        st.markdown(
            f"<div style='font-size:12px;color:#64748b;margin-bottom:8px'>"
            f"Vista previa — {len(df_up)} fila(s) detectadas</div>",
            unsafe_allow_html=True
        )
        st.dataframe(df_up, use_container_width=True, hide_index=True)

        # Métricas rápidas
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Filas",       f"{len(df_up):,}")
        m2.metric("CTNs únicos", f"{df_up['CTN'].nunique():,}")
        m3.metric("DIF CAJAS",   f"{int(df_up['DIF CAJAS'].sum()):+,}")
        m4.metric("DIF UNI",     f"{int(df_up['DIF UNI'].sum()):+,}")

        st.divider()

        # ── Confirmar carga ───────────────────────────────────────────────────
        if "pl_carga_ok" not in st.session_state:
            st.session_state["pl_carga_ok"] = False

        if st.button("✅  Confirmar e insertar en sistema", use_container_width=True, type="primary"):
            try:
                client_pl = get_client()
                sh_pl     = client_pl.open_by_key(st.secrets["spreadsheet_id"])
                ws_pl     = sh_pl.worksheet("PACKINGLIST")
                headers_pl = ws_pl.row_values(1)

                # Construir filas respetando el orden de columnas de la sheet
                filas_pl = []
                for _, row in df_up.iterrows():
                    fila = []
                    for h in headers_pl:
                        h_strip = h.strip()
                        if h_strip in df_up.columns:
                            val = row[h_strip]
                            fila.append("" if pd.isna(val) else str(val) if not isinstance(val, (int, float)) else val)
                        else:
                            fila.append("")
                    filas_pl.append(fila)

                ws_pl.append_rows(filas_pl, value_input_option="USER_ENTERED")
                st.cache_data.clear()
                st.session_state["pl_carga_ok"] = True
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error al insertar en Google Sheets: {e}")

        if st.session_state.get("pl_carga_ok"):
            st.session_state["pl_carga_ok"] = False
            st.success("✅ Packing List cargado correctamente. Los datos ya están en el sistema.")


# ══════════════════════════════════════════════════════════════════════════════
# VISTA: CAMBIO DE ESTADO CTN
# ══════════════════════════════════════════════════════════════════════════════

elif vista == "🔄  Cambio de Estado CTN":

    st.markdown(f"""
    <div class="wms-header">
      <div style="font-size:32px">🔄</div>
      <div>
        <h1>Cambio de Estado — CTN</h1>
        <p>Selecciona un contenedor y actualiza su estado en el Packing List</p>
      </div>
      <span class="wms-badge">Gestión</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Cargar datos actuales del packinglist ─────────────────────────────────
    try:
        client_est = get_client()
        sh_est     = client_est.open_by_key(st.secrets["spreadsheet_id"])
        ws_est     = sh_est.worksheet("PACKINGLIST")
        data_est   = ws_est.get_all_records()
        headers_est = ws_est.row_values(1)
        df_est     = pd.DataFrame(data_est)
    except Exception as e:
        st.error(f"❌ Error conectando a Google Sheets: {e}")
        st.stop()

    if df_est.empty:
        st.info("El Packing List está vacío.")
        st.stop()

    # Detectar columnas clave
    col_ctn_est    = next((c for c in df_est.columns if "CTN" in c.upper()), None)
    col_estado_est = next((c for c in df_est.columns if "ESTADO" in c.upper()), None)
    col_sku_est    = next((c for c in df_est.columns if "SKU" in c.upper()), None)

    if not col_ctn_est or not col_estado_est:
        st.error("❌ No se encontraron las columnas CTN o ESTADO en el Packing List.")
        st.stop()

    # ── Filtrar solo CTNs que NO están completamente REVISADOS ──────────────────
    ctns_todos = df_est[col_ctn_est].astype(str).unique().tolist()
    ctns_pendientes = []
    for ctn in ctns_todos:
        estados_ctn = df_est[df_est[col_ctn_est].astype(str) == ctn][col_estado_est].astype(str).unique().tolist()
        if not all(e.strip().upper() == "REVISADO" for e in estados_ctn):
            ctns_pendientes.append(ctn)
    ctns_pendientes = sorted(ctns_pendientes)

    if not ctns_pendientes:
        st.success("✅ Todos los contenedores están en estado REVISADO.")
        st.stop()

    # ── Selector de CTN ───────────────────────────────────────────────────────
    with st.form("form_estado_ctn"):
        fc1, fc2 = st.columns(2)

        with fc1:
            f_ctn_sel = st.selectbox(
                "📦 Seleccionar CTN (solo pendientes de revisión)",
                ctns_pendientes
            )
        with fc2:
            f_estado_filtro = st.selectbox(
                "🏷️ Filtrar por estado actual",
                ["Todos"] + sorted(df_est[col_estado_est].dropna().astype(str).unique().tolist())
            )

        st.form_submit_button("🔍 Ver detalle del CTN", use_container_width=True)

    # ── Detalle del CTN seleccionado ──────────────────────────────────────────
    df_ctn = df_est[df_est[col_ctn_est].astype(str) == f_ctn_sel].copy()
    if f_estado_filtro != "Todos":
        df_ctn = df_ctn[df_ctn[col_estado_est].astype(str) == f_estado_filtro]

    estado_actual_ctn = df_est[
        df_est[col_ctn_est].astype(str) == f_ctn_sel
    ][col_estado_est].iloc[0] if len(df_ctn) else "—"

    m1, m2, m3 = st.columns(3)
    m1.metric("📦 CTN",           f_ctn_sel)
    m2.metric("🏷️ Estado actual", str(estado_actual_ctn))
    m3.metric("📋 Filas en CTN",  f"{len(df_ctn):,}")

    st.divider()

    if len(df_ctn) == 0:
        st.info("No hay registros para este CTN con el filtro seleccionado.")
    else:
        st.dataframe(df_ctn, use_container_width=True, hide_index=True)

        st.divider()

        st.markdown(
            f"<div style='background:#eff6ff;border-left:4px solid #185FA5;border-radius:6px;"
            f"padding:10px 16px;font-size:13px;color:#1e40af;margin-bottom:12px'>"
            f"Se marcará el CTN <b>{f_ctn_sel}</b> como <b>REVISADO</b> en todas sus filas "
            f"({len(df_est[df_est[col_ctn_est].astype(str) == f_ctn_sel])} registros)."
            f"</div>",
            unsafe_allow_html=True
        )

        if "estado_ctn_ok" not in st.session_state:
            st.session_state["estado_ctn_ok"] = False

        col_ok, col_sp2 = st.columns([1, 2])
        with col_ok:
            if st.button("✅  Marcar como REVISADO y guardar", use_container_width=True, type="primary"):
                try:
                    col_idx_est = headers_est.index(col_estado_est) + 1
                    col_ctn_idx = headers_est.index(col_ctn_est)
                    todas_filas = ws_est.get_all_values()

                    batch = []
                    for i, fila in enumerate(todas_filas[1:], start=2):
                        if len(fila) > col_ctn_idx and str(fila[col_ctn_idx]).strip() == str(f_ctn_sel):
                            from gspread.utils import rowcol_to_a1
                            celda = rowcol_to_a1(i, col_idx_est)
                            batch.append({"range": celda, "values": [["REVISADO"]]})

                    if batch:
                        ws_est.batch_update(batch, value_input_option="USER_ENTERED")
                        st.cache_data.clear()
                        st.session_state["estado_ctn_ok"] = True
                        st.rerun()
                    else:
                        st.warning("No se encontraron celdas para actualizar.")

                except Exception as e:
                    st.error(f"❌ Error al actualizar: {e}")

        if st.session_state.get("estado_ctn_ok"):
            st.session_state["estado_ctn_ok"] = False
            st.success(f"✅ CTN {f_ctn_sel} marcado como REVISADO correctamente.")

# ══════════════════════════════════════════════════════════════════════════════
# VISTA: SALIDA DE MERMA
# ══════════════════════════════════════════════════════════════════════════════

elif vista == "⚠️  Salida de Merma":

    st.markdown(f"""
    <div class="wms-header">
      <div style="font-size:32px">⚠️</div>
      <div>
        <h1>Salida de Merma</h1>
        <p>Registrar salidas de productos en estado MERMA</p>
      </div>
      <span class="wms-badge">Operación</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Inicializar session state ──────────────────────────────────────────────
    for _k, _v in [
        ("merma_op_paso",         1),
        ("merma_op_fecha",        date.today()),
        ("merma_op_guia",         ""),
        ("merma_op_obs",          ""),
        ("merma_op_ctn",          ""),
        ("merma_op_seleccion",    {}),   # {item_key: cantidad}
        ("merma_op_exito",        False),
        ("merma_op_procesando",   False),
    ]:
        if _k not in st.session_state:
            st.session_state[_k] = _v

    def reset_merma_op():
        st.session_state["merma_op_paso"]       = 1
        st.session_state["merma_op_fecha"]      = date.today()
        st.session_state["merma_op_guia"]       = ""
        st.session_state["merma_op_obs"]        = ""
        st.session_state["merma_op_ctn"]        = ""
        st.session_state["merma_op_seleccion"]  = {}
        st.session_state["merma_op_exito"]      = False
        st.session_state["merma_op_procesando"] = False

    def insertar_merma(filas: list) -> bool:
        try:
            client  = get_client()
            sh      = client.open_by_key(st.secrets["spreadsheet_id"])
            ws      = sh.worksheet(SHEET_NAME)
            ws.append_rows(filas, value_input_option="USER_ENTERED")
            return True
        except Exception as e:
            st.error(f"❌ Error al guardar en Google Sheets: {e}")
            return False

    # ── Obtener CTNs que tienen MERMA ─────────────────────────────────────────
    stock_merma_global = calcular_stock(df[df["ESTADO"] == "MERMA"], date.today())
    ctns_con_merma = sorted(stock_merma_global["CTN"].dropna().astype(str).unique().tolist())

    if not ctns_con_merma:
        st.info("No hay productos en estado MERMA registrados en el sistema.")
        st.stop()

    # ══════════════════════════════════════════════════════════════════════════
    # PASO 1 — Cabecera
    # ══════════════════════════════════════════════════════════════════════════
    if st.session_state["merma_op_paso"] == 1:

        st.markdown("""
        <div style="background:#fef3c7;border-left:4px solid #f59e0b;border-radius:6px;
                    padding:10px 16px;font-size:13px;color:#92400e;margin-bottom:16px">
          <b>Paso 1 de 2</b> — Completa los datos de la salida y selecciona el contenedor.
        </div>
        """, unsafe_allow_html=True)

        with st.form("form_merma_cabecera"):
            c1, c2 = st.columns(2)
            with c1:
                inp_fecha = st.date_input(
                    "📅 Fecha de salida",
                    value=st.session_state["merma_op_fecha"]
                )
                inp_ctn = st.selectbox(
                    "📦 Contenedor (CTN)",
                    ctns_con_merma,
                    index=ctns_con_merma.index(st.session_state["merma_op_ctn"])
                    if st.session_state["merma_op_ctn"] in ctns_con_merma else 0
                )
            with c2:
                inp_guia = st.text_input(
                    "📄 N° de Guía / Referencia",
                    value=st.session_state["merma_op_guia"],
                    placeholder="Ej: MR-2026-001"
                )
                inp_obs = st.text_input(
                    "💬 Observación (opcional)",
                    value=st.session_state["merma_op_obs"],
                    placeholder="Ej: Destrucción programada"
                )

            continuar = st.form_submit_button(
                "➡️  Continuar — Ver merma del CTN",
                use_container_width=True
            )

        if continuar:
            if not inp_guia.strip():
                st.warning("⚠️ Debes ingresar un N° de Guía / Referencia.")
            else:
                st.session_state["merma_op_fecha"] = inp_fecha
                st.session_state["merma_op_guia"]  = inp_guia.strip()
                st.session_state["merma_op_obs"]   = inp_obs.strip()
                st.session_state["merma_op_ctn"]   = str(inp_ctn)
                st.session_state["merma_op_paso"]  = 2
                st.session_state["merma_op_seleccion"] = {}
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # PASO 2 — Selección de ítems
    # ══════════════════════════════════════════════════════════════════════════
    else:
        ctn_sel    = st.session_state["merma_op_ctn"]
        fecha_sel  = st.session_state["merma_op_fecha"]
        guia_sel   = st.session_state["merma_op_guia"]
        obs_sel    = st.session_state["merma_op_obs"]

        # ── Banner fijo ───────────────────────────────────────────────────────
        items_sel = len([v for v in st.session_state["merma_op_seleccion"].values() if v > 0])
        total_sel = sum(st.session_state["merma_op_seleccion"].values())

        st.markdown(f"""
        <div style="background:#0d1b2a;border-radius:10px;padding:14px 20px;
                    margin-bottom:16px;display:flex;gap:24px;align-items:center;
                    box-shadow:0 2px 8px rgba(0,0,0,0.15)">
          <div>
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.08em">Guía</div>
            <div style="font-size:14px;font-weight:700;color:#e2e8f0">{guia_sel}</div>
          </div>
          <div>
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.08em">CTN</div>
            <div style="font-size:14px;font-weight:700;color:#e2e8f0">{ctn_sel}</div>
          </div>
          <div>
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.08em">Fecha</div>
            <div style="font-size:14px;font-weight:700;color:#e2e8f0">{fecha_sel.strftime('%d/%m/%Y')}</div>
          </div>
          <div style="margin-left:auto;text-align:right">
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.08em">Seleccionados / Unidades</div>
            <div style="font-size:16px;font-weight:700;color:#fbbf24">{items_sel} ítems &nbsp;·&nbsp; {total_sel:,} u.</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Lista de merma del CTN ────────────────────────────────────────────
        merma_ctn = stock_merma_global[
            stock_merma_global["CTN"].astype(str) == ctn_sel
        ].copy()

        if merma_ctn.empty:
            st.info(f"No hay merma registrada para el CTN {ctn_sel}.")
        else:
            st.markdown(
                f"<div style='font-size:11px;font-weight:700;color:#64748b;"
                f"text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px'>"
                f"⚠️ Merma disponible en CTN {ctn_sel} — {len(merma_ctn)} ítem(s)</div>",
                unsafe_allow_html=True
            )

            for _, row in merma_ctn.iterrows():
                sku       = str(row["SKU MASEF"])
                desc      = str(row.get("DESCRIPTION", ""))
                estado    = str(row["ESTADO"])
                stock_d   = int(row["Stock"])
                vcto      = str(row.get("FECHA VCTO", "")) or "—"
                item_key  = f"{sku}||{ctn_sel}||{estado}||{vcto}"

                seleccion_actual = st.session_state["merma_op_seleccion"].get(item_key, 0)
                marcado = seleccion_actual > 0

                # Card del ítem
                bg_card = "rgba(245,158,11,0.08)" if marcado else "#ffffff"
                border  = "1.5px solid #f59e0b"  if marcado else "1px solid #e2e8f0"
                st.markdown(f"""
                <div style="background:{bg_card};border:{border};border-radius:10px;
                            padding:14px 18px;margin-bottom:6px;
                            box-shadow:0 1px 3px rgba(0,0,0,0.05)">
                  <div style="font-size:11px;font-weight:700;color:#d97706;
                              text-transform:uppercase;letter-spacing:.06em">{sku}</div>
                  <div style="font-size:14px;font-weight:600;color:#0f172a;margin:2px 0 4px">{desc}</div>
                  <div style="font-size:11px;color:#64748b">
                    🏷️ Estado: <b>{estado}</b> &nbsp;|&nbsp;
                    📅 Vcto: <b>{vcto}</b> &nbsp;|&nbsp;
                    <span style="color:#ef4444;font-weight:700">Stock merma: {stock_d:,} u.</span>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                col_chk, col_qty = st.columns([3, 1])
                with col_chk:
                    incluir = st.checkbox(
                        f"Incluir en salida",
                        value=marcado,
                        key=f"chk_merma_{item_key}"
                    )
                with col_qty:
                    if incluir:
                        cant = st.number_input(
                            "Cantidad",
                            min_value=1,
                            max_value=stock_d,
                            value=max(1, seleccion_actual),
                            step=1,
                            key=f"qty_merma_{item_key}",
                            label_visibility="collapsed"
                        )
                        st.session_state["merma_op_seleccion"][item_key] = cant
                    else:
                        st.session_state["merma_op_seleccion"][item_key] = 0
                        st.markdown(
                            "<div style='font-size:11px;color:#94a3b8;margin-top:8px'>—</div>",
                            unsafe_allow_html=True
                        )

            # ── Resumen y confirmación ────────────────────────────────────────
            items_a_guardar = {
                k: v for k, v in st.session_state["merma_op_seleccion"].items() if v > 0
            }

            st.divider()

            if items_a_guardar:
                total_guardar = sum(items_a_guardar.values())
                st.markdown(
                    f"<div style='background:#fef3c7;border-left:4px solid #f59e0b;"
                    f"border-radius:6px;padding:10px 16px;font-size:13px;color:#92400e;margin-bottom:12px'>"
                    f"Se registrarán <b>{len(items_a_guardar)} ítem(s)</b> con un total de "
                    f"<b>{total_guardar:,} unidades</b> como salida de merma.</div>",
                    unsafe_allow_html=True
                )

            col_ok, col_volver, col_can = st.columns([3, 1, 1])

            with col_ok:
                btn_label = f"✅  Registrar salida de merma ({len(items_a_guardar)} ítem(s))"
                btn_disabled = len(items_a_guardar) == 0
                if st.button(btn_label, use_container_width=True,
                             type="primary", disabled=btn_disabled):

                    if st.session_state.get("merma_op_procesando"):
                        st.warning("⏳ Ya se está procesando, espera un momento.")
                    else:
                        st.session_state["merma_op_procesando"] = True
                        try:
                            client_m  = get_client()
                            sh_m      = client_m.open_by_key(st.secrets["spreadsheet_id"])
                            ws_m      = sh_m.worksheet(SHEET_NAME)
                            headers_m = ws_m.row_values(1)
                        except Exception as e:
                            st.error(f"❌ No se pudo leer la hoja: {e}")
                            headers_m = []
                            st.session_state["merma_op_procesando"] = False

                        if headers_m:
                            fecha_str = fecha_sel.strftime("%d/%m/%Y")
                            filas_merma = []

                            for item_key, cantidad in items_a_guardar.items():
                                partes  = item_key.split("||")
                                sku_m   = partes[0]
                                ctn_m   = partes[1]
                                est_m   = partes[2]
                                vcto_m  = partes[3] if len(partes) > 3 else ""

                                # Normalizar fecha vcto
                                if vcto_m and vcto_m not in ("—", "nan", ""):
                                    try:
                                        vcto_fmt = pd.to_datetime(vcto_m, dayfirst=False, errors="coerce")
                                        vcto_m   = vcto_fmt.strftime("%d/%m/%Y") if not pd.isna(vcto_fmt) else vcto_m
                                    except:
                                        pass

                                # Buscar descripción
                                desc_m = ""
                                filt = df[
                                    (df["SKU MASEF"].astype(str).str.strip() == sku_m) &
                                    (df["CTN"].astype(str).str.strip() == ctn_m)
                                ]
                                if not filt.empty:
                                    desc_m = str(filt["DESCRIPTION"].iloc[0])

                                fila = []
                                for h in headers_m:
                                    h_up = h.upper().strip()
                                    if h_up == "FECHA":
                                        fila.append(fecha_str)
                                    elif h_up == "CTN":
                                        fila.append(ctn_m)
                                    elif h_up in ("SKU MASEF", "SKU"):
                                        fila.append(sku_m)
                                    elif h_up in ("DESCRIPTION", "DESCRIPCION", "DESCRIPCIÓN"):
                                        fila.append(desc_m)
                                    elif h_up == "ESTADO":
                                        fila.append("MERMA")
                                    elif h_up in ("FECHA VCTO", "FECHA VENCIMIENTO", "VENCIMIENTO"):
                                        fila.append(vcto_m)
                                    elif h_up in ("TIPO DE MOVIMIENTO", "TIPO MOVIMIENTO", "MOVIMIENTO"):
                                        fila.append("SALIDA")
                                    elif h_up in ("TOTAL UNIT", "CANTIDAD", "UNITS"):
                                        fila.append(-abs(cantidad))
                                    elif h_up in ("GUIA", "GUÍA", "N° GUIA", "NUMERO GUIA"):
                                        fila.append(guia_sel)
                                    elif h_up in ("OBS", "OBSERVACION", "OBSERVACIONES", "OBSERVACIÓN"):
                                        fila.append(obs_sel)
                                    else:
                                        fila.append("")
                                filas_merma.append(fila)

                            ok = insertar_merma(filas_merma)
                            st.session_state["merma_op_procesando"] = False
                            if ok:
                                st.cache_data.clear()
                                reset_merma_op()
                                st.session_state["merma_op_exito"] = True
                                st.rerun()

            with col_volver:
                if st.button("✏️  Editar cabecera", use_container_width=True):
                    st.session_state["merma_op_paso"] = 1
                    st.rerun()

            with col_can:
                if st.button("🗑️  Cancelar", use_container_width=True):
                    reset_merma_op()
                    st.rerun()

    # ── Mensaje de éxito ──────────────────────────────────────────────────────
    if st.session_state.get("merma_op_exito") and st.session_state["merma_op_paso"] == 1:
        st.session_state["merma_op_exito"] = False
        st.success("✅ Salida de merma registrada correctamente. El stock ha sido actualizado.")
