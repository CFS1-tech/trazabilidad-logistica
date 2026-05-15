import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="WMS Trazabilidad Pro", layout="wide", page_icon="🏢")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        background-color: #1f77b4;
        color: white;
        font-weight: bold;
    }
    [data-testid="stSidebar"] { background-color: #262730; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: white; font-size: 1.1em;
    }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #1f77b4; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN Y LECTURA CON CACHÉ ---
@st.cache_resource
def conectar_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    except:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return gspread.authorize(creds).open("LOGISTICA_TRAZABILIDAD")

@st.cache_data(ttl=60)
def leer_datos(nombre_hoja):
    try:
        client = conectar_gsheet()
        ws = client.worksheet(nombre_hoja)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"Error al leer {nombre_hoja}: {e}")
        return pd.DataFrame()

# Instancias para ESCRITURA
gc_write = conectar_gsheet()
ws_inv_w = gc_write.worksheet("inventario")
ws_mov_w = gc_write.worksheet("movimientos")
ws_pick_w = gc_write.worksheet("picking")

# --- LÓGICA DE LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None

def login():
    st.markdown("<h1 style='text-align: center; color: #1f77b4;'>🏢 Acceso WMS</h1>", unsafe_allow_html=True)
    with st.columns([1,2,1])[1]:
        with st.container(border=True):
            user = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            if st.button("Entrar al Sistema"):
                if user == "admin" and password == "123":
                    st.session_state.logged_in, st.session_state.role = True, "Administrador"
                elif user == "operador" and password == "456":
                    st.session_state.logged_in, st.session_state.role = True, "Operativo"
                elif user == "cliente" and password == "789":
                    st.session_state.logged_in, st.session_state.role = True, "Cliente"
                else:
                    st.error("❌ Credenciales incorrectas")
                if st.session_state.logged_in: st.rerun()

if not st.session_state.logged_in:
    login()
    st.stop()

# --- FUNCIONES DE SOPORTE ---
def formatear_fechas(df, col):
    if df.empty or col not in df.columns: return df
    df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
    df[f'{col}_fmt'] = df[col].dt.strftime('%d/%m/%Y').fillna("N/A")
    return df

def registrar_movimiento(tipo, sku, cont, est, fv, cant, ref, cliente="N/A"):
    fecha_s = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    ws_mov_w.append_row([fecha_s, tipo, str(sku).strip(), str(cont).strip(), est, cant, ref, cliente, str(fv)])
    st.cache_data.clear()

def actualizar_inventario(sku, cont, est, fv, cant):
    df_inv = leer_datos("inventario")
    sku_s, cont_s, fv_s = str(sku).strip(), str(cont).strip(), str(fv).strip()
    match = pd.DataFrame()
    if not df_inv.empty:
        match = df_inv[(df_inv['sku'].astype(str)==sku_s) & 
                       (df_inv['contenedor'].astype(str)==cont_s) & 
                       (df_inv['estado'].astype(str).str.lower()==est.lower()) & 
                       (df_inv['fecha_vencimiento'].astype(str)==fv_s)]
    if match.empty:
        if cant > 0: ws_inv_w.append_row([sku_s, cont_s, est, fv_s, cant])
    else:
        idx = match.index[0] + 2
        val_actual = pd.to_numeric(match.iloc[0]['stock_actual'], errors='coerce') or 0
        ws_inv_w.update_cell(idx, 5, int(val_actual + cant))
    st.cache_data.clear()

# --- MENÚ ---
st.sidebar.markdown(f"### 👤 {st.session_state.role}")
opciones = []
if st.session_state.role in ["Administrador", "Operativo"]: opciones.append("🚀 Operaciones")
opciones.extend(["📦 Reporte de Stock", "🗑️ Reporte de Merma", "📊 Reporte trazabilidad", "📋 Reporte PL", "💡 Insights"])

menu = st.sidebar.radio("NAVEGACIÓN", opciones)
if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state.logged_in = False
    st.cache_data.clear()
    st.rerun()

# --- SECCIONES ---
if menu == "🚀 Operaciones":
    st.header("🚀 Gestión de Bodega")
    op = st.selectbox("Acción:", ["📥 Ingreso Físico", "📝 Picking (Preparación)", "📤 Salida (Despacho)", "♻️ Reclasificación"])
    
    if op == "📥 Ingreso Físico":
        df_pl = leer_datos("packing_list")
        if not df_pl.empty:
            c_sel = st.selectbox("Contenedor:", sorted(df_pl['contenedor'].unique().astype(str)))
            s_sel = st.selectbox("SKU:", sorted(df_pl[df_pl['contenedor'].astype(str)==c_sel]['sku'].unique().astype(str)))
            with st.form("f_ing"):
                est = st.selectbox("Estado", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
                fv = st.date_input("Vencimiento")
                cant = st.number_input("Cantidad:", min_value=1)
                ref = st.text_input("Referencia/Guía")
                if st.form_submit_button("Confirmar Ingreso"):
                    fv_s = fv.strftime('%d/%m/%Y')
                    actualizar_inventario(s_sel, c_sel, est, fv_s, cant)
                    registrar_movimiento("INGRESO_PL", s_sel, c_sel, est, fv_s, cant, ref)
                    st.success("✅ Ingreso Guardado")

    elif op == "📝 Picking (Preparación)":
        df_i = leer_datos("inventario")
        if not df_i.empty:
            df_disp = df_i[pd.to_numeric(df_i['stock_actual']) > 0]
            s_sel = st.selectbox("SKU:", sorted(df_disp['sku'].unique().astype(str)))
            c_sel = st.selectbox("Contenedor:", sorted(df_disp[df_disp['sku'].astype(str)==s_sel]['contenedor'].unique().astype(str)))
            df_f = df_disp[(df_disp['sku'].astype(str)==s_sel) & (df_disp['contenedor'].astype(str)==c_sel)]
            est_p = st.selectbox("Estado:", df_f['estado'].unique())
            fv_p = st.selectbox("FV:", df_f['fecha_vencimiento'].unique())
            with st.form("f_pick"):
                cant = st.number_input("Cantidad:", min_value=1)
                cliente = st.text_input("Cliente")
                pedido = st.text_input("Pedido")
                if st.form_submit_button("Registrar"):
                    actualizar_inventario(s_sel, c_sel, est_p, fv_p, -cant)
                    ws_pick_w.append_row([datetime.now().strftime('%d/%m/%Y %H:%M:%S'), str(s_sel), str(c_sel), cant, cliente, pedido, est_p, fv_p])
                    registrar_movimiento("PICKING", s_sel, c_sel, est_p, fv_p, cant, f"Pedido: {pedido}", cliente)
                    st.success("✅ Picking OK")

    elif op == "📤 Salida (Despacho)":
        df_i = leer_datos("inventario")
        if not df_i.empty:
            df_disp = df_i[pd.to_numeric(df_i['stock_actual']) > 0]
            s_sel = st.selectbox("SKU:", sorted(df_disp['sku'].unique().astype(str)))
            c_sel = st.selectbox("Contenedor:", sorted(df_disp[df_disp['sku'].astype(str)==s_sel]['contenedor'].unique().astype(str)))
            df_f = df_disp[(df_disp['sku'].astype(str)==s_sel) & (df_disp['contenedor'].astype(str)==c_sel)]
            est_s = st.selectbox("Estado:", df_f['estado'].unique())
            fv_s = st.selectbox("FV:", df_f['fecha_vencimiento'].unique())
            with st.form("f_sal"):
                cant = st.number_input("Cantidad:", min_value=1)
                cliente = st.text_input("Destino")
                doc = st.text_input("Guía")
                if st.form_submit_button("Confirmar"):
                    actualizar_inventario(s_sel, c_sel, est_s, fv_s, -cant)
                    registrar_movimiento("SALIDA", s_sel, c_sel, est_s, fv_s, cant, doc, cliente)
                    st.success("✅ Despacho OK")

    elif op == "♻️ Reclasificación":
        df_i = leer_datos("inventario")
        if not df_i.empty:
            df_disp = df_i[pd.to_numeric(df_i['stock_actual']) > 0]
            s_sel = st.selectbox("SKU:", sorted(df_disp['sku'].unique().astype(str)))
            c_sel = st.selectbox("Contenedor:", sorted(df_disp[df_disp['sku'].astype(str)==s_sel]['contenedor'].unique().astype(str)))
            df_f = df_disp[(df_disp['sku'].astype(str)==s_sel) & (df_disp['contenedor'].astype(str)==c_sel)]
            est_orig = st.selectbox("Estado Actual:", df_f['estado'].unique())
            fv_orig = st.selectbox("FV:", df_f['fecha_vencimiento'].unique())
            with st.form("f_re"):
                est_dest = st.selectbox("Nuevo Estado:", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
                cant = st.number_input("Cantidad:", min_value=1)
                if st.form_submit_button("Cambiar"):
                    actualizar_inventario(s_sel, c_sel, est_orig, fv_orig, -cant)
                    actualizar_inventario(s_sel, c_sel, est_dest, fv_orig, cant)
                    registrar_movimiento("RECLASIFICACION", s_sel, c_sel, est_dest, fv_orig, cant, f"De {est_orig} a {est_dest}")
                    st.success("✅ Actualizado")

elif menu == "📦 Reporte de Stock":
    st.header("📦 Inventario Actual")
    df_i = leer_datos("inventario")
    if not df_i.empty:
        df_i = formatear_fechas(df_i, 'fecha_vencimiento')
        c1, c2 = st.columns(2)
        f_cont = c1.multiselect("Contenedor:", sorted(df_i['contenedor'].unique().astype(str)))
        f_sku = c2.text_input("SKU:")
        if st.button("🔍 Buscar"):
            res = df_i[pd.to_numeric(df_i['stock_actual']) > 0].copy()
            if f_cont: res = res[res['contenedor'].astype(str).isin(f_cont)]
            if f_sku: res = res[res['sku'].astype(str).str.contains(f_sku, case=False)]
            st.dataframe(res[['sku', 'contenedor', 'estado', 'fecha_vencimiento_fmt', 'stock_actual']], use_container_width=True)

elif menu == "🗑️ Reporte de Merma":
    st.header("🗑️ Historial de Mermas")
    df_m = leer_datos("movimientos")
    if not df_m.empty:
        df_m['estado_l'] = df_m['estado'].astype(str).str.strip().str.lower()
        f_cont_m = st.multiselect("Contenedor:", sorted(df_m['contenedor'].unique().astype(str)))
        if st.button("🔍 Ver"):
            res = df_m[(df_m['estado_l'] == "merma") & (df_m['tipo_mov'].str.contains("INGRESO", na=False))].copy()
            if f_cont_m: res = res[res['contenedor'].astype(str).isin(f_cont_m)]
            st.warning(f"Total: {int(pd.to_numeric(res['cantidad']).sum())} unidades")
            st.dataframe(res[['fecha_hora', 'sku', 'contenedor', 'cantidad', 'referencia']], use_container_width=True)

elif menu == "📊 Historial":
    st.header("📊 Trazabilidad")
    df_m = leer_datos("movimientos")
    if not df_m.empty:
        c1, c2, c3 = st.columns(3)
        f_ini, f_fin = c1.date_input("Desde:", datetime.now()-timedelta(days=30)), c2.date_input("Hasta:", datetime.now())
        f_cont_h = c3.multiselect("Contenedor:", sorted(df_m['contenedor'].unique().astype(str)))
        f_sku_h = st.text_input("SKU:")
        if st.button("🔍 Filtrar"):
            df_m['dt'] = pd.to_datetime(df_m['fecha_hora'], errors='coerce', dayfirst=True)
            mask = (df_m['dt'].dt.date >= f_ini) & (df_m['dt'].dt.date <= f_fin)
            res = df_m[mask].copy()
            if f_cont_h: res = res[res['contenedor'].astype(str).isin(f_cont_h)]
            if f_sku_h: res = res[res['sku'].astype(str).str.contains(f_sku_h, case=False)]
            st.dataframe(res[['fecha_hora', 'tipo_mov', 'sku', 'contenedor','estado','fecha_vencimiento', 'cantidad', 'referencia', 'cliente']], use_container_width=True)

elif menu == "📋 Packing List":
    st.header("📋 Cruce vs PL")
    df_pl = leer_datos("packing_list")
    df_mov = leer_datos("movimientos")
    if not df_pl.empty:
        cont_f = st.selectbox("Contenedor:", ["Todos"] + sorted(df_pl['contenedor'].unique().astype(str)))
        if st.button("🔍 Comparar"):
            real = df_mov[df_mov['tipo_mov']=="INGRESO_PL"].copy()
            real['cantidad'] = pd.to_numeric(real['cantidad'], errors='coerce').fillna(0)
            sum_r = real.groupby(['sku', 'contenedor'])['cantidad'].sum().reset_index()
            sum_r.columns = ['sku', 'contenedor', 'cantidad_real']
            res = pd.merge(df_pl, sum_r, on=['sku', 'contenedor'], how='left').fillna(0)
            col_q = 'cantidad' if 'cantidad' in res.columns else 'cantidad_pl'
            res['diferencia'] = res['cantidad_real'] - pd.to_numeric(res[col_q])
            if cont_f != "Todos": res = res[res['contenedor'].astype(str) == cont_f]
            st.dataframe(res, use_container_width=True)

elif menu == "💡 Insights":
    st.header("💡 Dashboard Estratégico")
    df_i = leer_datos("inventario")
    if not df_i.empty:
        df_i['stock_actual'] = pd.to_numeric(df_i['stock_actual'], errors='coerce').fillna(0)
        df_i['dt_venc'] = pd.to_datetime(df_i['fecha_vencimiento'], errors='coerce', dayfirst=True)
        
        # Filtro Sidebar
        cont_filter = st.sidebar.selectbox("Filtrar por:", ["Todos"] + sorted(df_i['contenedor'].unique().astype(str)))
        df_dash = df_i.copy() if cont_filter == "Todos" else df_i[df_i['contenedor'].astype(str) == cont_filter]

        # KPIs superiores
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Stock Total", f"{int(df_dash['stock_actual'].sum()):,} uds")
        k2.metric("SKUs Activos", df_dash['sku'].nunique())
        k3.metric("Stock Merma", int(df_dash[df_dash['estado'].str.lower() == 'merma']['stock_actual'].sum()))
        venc_60 = df_dash[(df_dash['dt_venc'] <= (datetime.now() + timedelta(days=60))) & (df_dash['stock_actual'] > 0)].shape[0]
        k4.metric("Alertas Vencimiento", venc_60)

        # Gráficos de barra
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Distribución por Estado")
            st.bar_chart(df_dash.groupby('estado')['stock_actual'].sum())
        with g2:
            st.subheader("Top 10 Contenedores")
            st.bar_chart(df_dash.groupby('contenedor')['stock_actual'].sum().sort_values(ascending=False).head(10))

        # Tabla de Vencimientos con estilo corregido
        st.subheader("🚨 Vencimientos Próximos (Días)")
        hoy = datetime.now()
        df_v = df_dash[df_dash['stock_actual'] > 0].sort_values('dt_venc').copy()
        
        if not df_v.empty:
            df_v['Días'] = (df_v['dt_venc'] - hoy).dt.days
            display_venc = df_v[['sku', 'contenedor', 'estado', 'fecha_vencimiento', 'stock_actual', 'Días']].head(15)
            
            # Definición de colores
            def apply_venc_color(s):
                colors = []
                for val in s:
                    if pd.isna(val): colors.append('')
                    elif val < 0: colors.append('background-color: #ff4b4b; color: black') # Rojo
                    elif val < 30: colors.append('background-color: #ffa500; color: black') # Naranja
                    elif val < 60: colors.append('background-color: #f9d71c; color: black') # Amarillo
                    else: colors.append('')
                return colors

            # Aplicamos el estilo solo a la columna 'Días' para evitar errores de tipo con fechas
            st.dataframe(display_venc.style.apply(apply_venc_color, subset=['Días']), use_container_width=True)
        else:
            st.success("No hay stock próximo a vencer.")
