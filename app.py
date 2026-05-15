import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="WMS Trazabilidad Pro", layout="wide", page_icon="🏢")

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #1f77b4;
        color: white;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    [data-testid="stSidebar"] {
        background-color: #262730;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: white;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN ---
@st.cache_resource
def conectar_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    except:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return gspread.authorize(creds).open("LOGISTICA_TRAZABILIDAD")

gc = conectar_gsheet()
ws_pl, ws_inv, ws_mov, ws_pick = gc.worksheet("packing_list"), gc.worksheet("inventario"), gc.worksheet("movimientos"), gc.worksheet("picking")

# --- LÓGICA DE LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None

def login():
    st.markdown("<h1 style='text-align: center; color: #1f77b4;'>🏢 WMS Login</h1>", unsafe_allow_html=True)
    with st.container(border=True):
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        col1, col2, col3 = st.columns([1,1,1])
        if col2.button("Entrar"):
            # Credenciales sencillas (puedes cambiarlas)
            if user == "admin" and password == "123":
                st.session_state.logged_in = True
                st.session_state.role = "Administrador"
            elif user == "operador" and password == "456":
                st.session_state.logged_in = True
                st.session_state.role = "Operativo"
            elif user == "cliente" and password == "789":
                st.session_state.logged_in = True
                st.session_state.role = "Cliente"
            else:
                st.error("❌ Usuario o contraseña incorrectos")
            st.rerun()

if not st.session_state.logged_in:
    login()
    st.stop()

# --- FUNCIONES CORE (ORIGINALES) ---
def formatear_fecha_lectura(df, columna, solo_fecha=False):
    if df.empty or columna not in df.columns: return df
    df[columna] = pd.to_datetime(df[columna], errors='coerce', dayfirst=True)
    fmt = '%d/%m/%Y' if solo_fecha else '%d/%m/%Y %H:%M:%S'
    df[f'{columna}_fmt'] = df[columna].dt.strftime(fmt).fillna("Formato Inválido")
    return df

def registrar_movimiento(tipo, sku, cont, est, fv, cant, ref, cliente="N/A"):
    fecha_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    ws_mov.append_row([fecha_str, tipo, str(sku).strip(), str(cont).strip(), est, cant, ref, cliente, str(fv)])

def actualizar_inventario(sku, cont, est, fv, cant):
    data = ws_inv.get_all_records()
    df_inv = pd.DataFrame(data)
    if not df_inv.empty: df_inv.columns = df_inv.columns.str.strip().str.lower()
    sku_s, cont_s, fv_s = str(sku).strip(), str(cont).strip(), str(fv)
    match = df_inv[(df_inv['sku'].astype(str)==sku_s) & (df_inv['contenedor'].astype(str)==cont_s) & (df_inv['estado']==est) & (df_inv['fecha_vencimiento'].astype(str)==fv_s)] if not df_inv.empty else pd.DataFrame()
    if match.empty:
        if cant > 0: ws_inv.append_row([sku_s, cont_s, est, fv_s, cant])
    else:
        idx = match.index[0] + 2
        val_actual = pd.to_numeric(match.iloc[0]['stock_actual'], errors='coerce') or 0
        ws_inv.update_cell(idx, 5, int(val_actual + cant))

# --- SIDEBAR DINÁMICO POR ROL ---
st.sidebar.markdown(f"### 👤 {st.session_state.role}")
st.sidebar.divider()

opciones = []
if st.session_state.role in ["Administrador", "Operativo"]:
    opciones.append("🚀 Operaciones")
opciones.append("📦 Reporte de Stock")
opciones.append("📊 Reporte trazabilidad")
opciones.append("📋 Reporte PL")
if st.session_state.role in ["Administrador", "Cliente"]:
    opciones.append("💡 Insights")

menu = st.sidebar.radio("MENÚ DE CONTROL", opciones)
if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state.logged_in = False
    st.rerun()

# --- 1. OPERACIONES ---
if menu == "🚀 Operaciones":
    st.header("🚀 Gestión de Movimientos")
    op = st.selectbox("Tipo de Movimiento:", ["📥 Ingreso Físico", "📤 Picking (Reserva)", "🚚 Despacho Directo", "♻️ Reclasificación"])
    
    if "Ingreso" in op:
        df_pl = pd.DataFrame(ws_pl.get_all_records())
        if not df_pl.empty:
            df_pl.columns = df_pl.columns.str.strip().str.lower()
            cont_sel = st.selectbox("Contenedor:", sorted(df_pl['contenedor'].unique().astype(str)))
            sku_sel = st.selectbox("SKU:", sorted(df_pl[df_pl['contenedor'].astype(str)==cont_sel]['sku'].unique().astype(str)))
            with st.form("f_ing"):
                c1, c2 = st.columns(2)
                est = c1.selectbox("Estado", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
                fv = c1.date_input("Vencimiento")
                cant = c2.number_input("Cantidad:", min_value=0)
                ref = c2.text_input("Referencia")
                if st.form_submit_button("Confirmar Ingreso"):
                    fv_s = fv.strftime('%d/%m/%Y')
                    actualizar_inventario(sku_sel, cont_sel, est, fv_s, cant)
                    registrar_movimiento("INGRESO_PL", sku_sel, cont_sel, est, fv_s, cant, ref)
                    st.success("✅ Guardado correctamente")

    elif "Picking" in op or "Despacho" in op:
        tipo = "PICKING" if "Picking" in op else "DESPACHO"
        cliente = st.text_input("Cliente/Destino:")
        df_inv = pd.DataFrame(ws_inv.get_all_records())
        if not df_inv.empty:
            df_inv.columns = df_inv.columns.str.strip().str.lower()
            df_inv['stock_actual'] = pd.to_numeric(df_inv['stock_actual'], errors='coerce').fillna(0)
            sku_p = st.selectbox("SKU:", sorted(df_inv[df_inv['stock_actual']>0]['sku'].unique().astype(str)))
            opciones_lote = df_inv[df_inv['sku'].astype(str)==sku_p]
            with st.form("f_sal"):
                sel = st.selectbox("Lote Origen:", [f"{r['contenedor']} | {r['estado']} | {r['fecha_vencimiento']}" for _, r in opciones_lote.iterrows()])
                cant_s = st.number_input("Cantidad:", min_value=1)
                if st.form_submit_button("Procesar Salida"):
                    idx = [f"{r['contenedor']} | {r['estado']} | {r['fecha_vencimiento']}" for _, r in opciones_lote.iterrows()].index(sel)
                    fila = opciones_lote.iloc[idx]
                    if tipo == "PICKING":
                        ws_pick.append_row([str(datetime.now().timestamp()), sku_p, str(fila['contenedor']), fila['estado'], str(fila['fecha_vencimiento']), cant_s, cliente, datetime.now().strftime('%d/%m/%Y')])
                    actualizar_inventario(sku_p, fila['contenedor'], fila['estado'], fila['fecha_vencimiento'], -cant_s)
                    registrar_movimiento(f"SALIDA_{tipo}", sku_p, fila['contenedor'], fila['estado'], fila['fecha_vencimiento'], cant_s, "ORDEN", cliente)
                    st.success("✅ Salida Registrada")

# --- 2. REPORTE DE STOCK ---
elif menu == "📦 Reporte de Stock":
    st.header("📦 Inventario en Tiempo Real")
    df_i = pd.DataFrame(ws_inv.get_all_records())
    if not df_i.empty:
        df_i.columns = df_i.columns.str.strip().str.lower()
        df_i = formatear_fecha_lectura(df_i, 'fecha_vencimiento', solo_fecha=True)
        with st.container(border=True):
            c1, c2 = st.columns(2)
            f_cont = c1.multiselect("Filtrar por Contenedor:", sorted(df_i['contenedor'].unique().astype(str)))
            f_sku = c2.text_input("Filtrar por SKU:")
            if st.button("🔍 Aplicar Filtros de Stock"):
                res = df_i[pd.to_numeric(df_i['stock_actual'], errors='coerce') > 0].copy()
                if f_cont: res = res[res['contenedor'].astype(str).isin(f_cont)]
                if f_sku: res = res[res['sku'].astype(str).str.contains(f_sku, case=False)]
                st.dataframe(res[['sku', 'contenedor', 'estado', 'fecha_vencimiento_fmt', 'stock_actual']], use_container_width=True)

# --- 3. HISTORIAL ---
elif menu == "📊 Historial":
    st.header("📊 Trazabilidad de Movimientos")
    df_m = pd.DataFrame(ws_mov.get_all_records())
    if not df_m.empty:
        df_m.columns = df_m.columns.str.strip().str.lower()
        df_m = formatear_fecha_lectura(df_m, 'fecha_hora')
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            f_ini, f_fin = c1.date_input("Desde:"), c2.date_input("Hasta:")
            f_s = c3.text_input("SKU:")
            if st.button("🔍 Consultar Historial"):
                df_m['dt'] = pd.to_datetime(df_m['fecha_hora'], errors='coerce', dayfirst=True)
                mask = (df_m['dt'].dt.date >= f_ini) & (df_m['dt'].dt.date <= f_fin)
                res = df_m[mask].copy()
                if f_s: res = res[res['sku'].astype(str).str.contains(f_s, case=False)]
                st.dataframe(res[['fecha_hora_fmt', 'tipo_mov', 'sku', 'contenedor', 'cantidad', 'referencia', 'cliente']], use_container_width=True)

# --- 4. PACKING LIST ---
elif menu == "📋 Packing List":
    st.header("📋 Cruce de Información (Packing List)")
    df_pl = pd.DataFrame(ws_pl.get_all_records())
    df_mov = pd.DataFrame(ws_mov.get_all_records())
    if not df_pl.empty:
        df_pl.columns = df_pl.columns.str.strip().str.lower()
        df_mov.columns = df_mov.columns.str.strip().str.lower()
        cont_f = st.selectbox("Seleccione Contenedor:", ["Ver Todos"] + sorted(df_pl['contenedor'].unique().astype(str)))
        if st.button("🔍 Generar Informe de Diferencias"):
            real = df_mov[df_mov['tipo_mov']=="INGRESO_PL"].copy()
            real['cantidad'] = pd.to_numeric(real['cantidad'], errors='coerce').fillna(0)
            sum_r = real.groupby(['sku', 'contenedor'])['cantidad'].sum().reset_index()
            sum_r.columns = ['sku', 'contenedor', 'cantidad_real']
            res = pd.merge(df_pl, sum_r, on=['sku', 'contenedor'], how='left').fillna(0)
            col_pl = 'cantidad' if 'cantidad' in res.columns else 'cantidad_pl'
            res['diferencia'] = pd.to_numeric(res['cantidad_real']) - pd.to_numeric(res[col_pl])
            if cont_f != "Ver Todos": res = res[res['contenedor'].astype(str) == cont_f]
            st.dataframe(res, use_container_width=True)

# --- 5. INSIGHTS ---
elif menu == "💡 Insights":
    st.header("💡 Inteligencia de Inventario")
    df_i = pd.DataFrame(ws_inv.get_all_records())
    if not df_i.empty:
        df_i.columns = df_i.columns.str.strip().str.lower()
        df_i = formatear_fecha_lectura(df_i, 'fecha_vencimiento', solo_fecha=True)
        df_i['dt'] = pd.to_datetime(df_i['fecha_vencimiento'], errors='coerce', dayfirst=True)
        df_i['stock_actual'] = pd.to_numeric(df_i['stock_actual'], errors='coerce').fillna(0)
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🚨 Vencimientos Próximos")
            prox = df_i[(df_i['dt'] <= (datetime.now() + timedelta(days=60))) & (df_i['stock_actual'] > 0)].copy()
            if not prox.empty:
                st.dataframe(prox.sort_values('dt')[['sku', 'contenedor', 'fecha_vencimiento_fmt', 'stock_actual']])
            else: st.info("Sin vencimientos críticos.")
        
        with c2:
            st.subheader("📦 Estados de Stock")
            res_est = df_i.groupby('estado')['stock_actual'].sum()
            st.bar_chart(res_est)
