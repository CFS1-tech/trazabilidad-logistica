import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="WMS Trazabilidad", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def conectar_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    except:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    return client.open("LOGISTICA_TRAZABILIDAD")

# Inicialización de conexión y hojas
try:
    gc = conectar_gsheet()
    ws_pl = gc.worksheet("packing_list")
    ws_inv = gc.worksheet("inventario")
    ws_mov = gc.worksheet("movimientos")
except Exception as e:
    st.error(f"Error de conexión: {e}. Revisa el archivo 'LOGISTICA_TRAZABILIDAD' y sus pestañas.")

# --- FUNCIONES CORE ---
def registrar_movimiento(tipo, sku, cont, est, fv, cant, ref, cliente="N/A"):
    ws_mov.append_row([str(datetime.now()), tipo, str(sku).strip(), str(cont).strip(), est, cant, ref, cliente, str(fv)])

def actualizar_inventario(sku, cont, est, fv, cant):
    # Obtener datos y normalizar columnas para evitar KeyErrors
    data = ws_inv.get_all_records()
    df_inv = pd.DataFrame(data)
    if not df_inv.empty:
        df_inv.columns = df_inv.columns.str.strip().str.lower()
    
    fv_str = str(fv)
    sku_str = str(sku).strip()
    cont_str = str(cont).strip()

    if not df_inv.empty:
        match = df_inv[
            (df_inv['sku'].astype(str) == sku_str) & 
            (df_inv['contenedor'].astype(str) == cont_str) & 
            (df_inv['estado'] == est) & 
            (df_inv['fecha_vencimiento'].astype(str) == fv_str)
        ]
    else:
        match = pd.DataFrame()

    if match.empty:
        ws_inv.append_row([sku_str, cont_str, est, fv_str, cant])
    else:
        row_idx = match.index[0] + 2
        new_val = int(match.iloc[0]['stock_actual']) + cant
        ws_inv.update_cell(row_idx, 5, new_val)

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("MENÚ PRINCIPAL", [
    "📥 Ingreso Físico", 
    "🔄 Reclasificación", 
    "📤 Despacho", 
    "📋 Estado Packing List", 
    "📊 Reportes"
])

# --- MÓDULO 1: INGRESO ---
if menu == "📥 Ingreso Físico":
    st.header("Registro de Ingreso Real")
    with st.form("ingreso"):
        c1, c2 = st.columns(2)
        sku = c1.text_input("SKU / COD II")
        cont = c1.text_input("N° Contenedor")
        est = c2.selectbox("Estado", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
        fv = c2.date_input("Fecha Vencimiento")
        cant = st.number_input("Cantidad Recibida", min_value=1)
        ref = st.text_input("Referencia / Guía")
        if st.form_submit_button("Confirmar Ingreso"):
            if sku and cont:
                actualizar_inventario(sku, cont, est, fv, cant)
                registrar_movimiento("INGRESO_PL", sku, cont, est, fv, cant, ref)
                st.success("✅ Registrado en Inventario y Movimientos.")
            else:
                st.error("SKU y Contenedor son obligatorios.")

# --- MÓDULO 2: RECLASIFICACIÓN ---
elif menu == "🔄 Reclasificación":
    st.header("Cambio de Estado Interno")
    with st.form("recla"):
        sku = st.text_input("SKU")
        cont = st.text_input("Contenedor")
        fv = st.date_input("Fecha Vencimiento Original")
        c1, c2 = st.columns(2)
        est_orig = c1.selectbox("De:", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
        est_dest = c2.selectbox("A:", ["Merma", "Bandejas", "Disponible", "Distribuidores"])
        cant = st.number_input("Cantidad", min_value=1)
        if st.form_submit_button("Mover Stock"):
            actualizar_inventario(sku, cont, est_orig, fv, -cant)
            actualizar_inventario(sku, cont, est_dest, fv, cant)
            registrar_movimiento("RECLASIFICACION", sku, cont, est_dest, fv, cant, f"Desde {est_orig}")
            st.success("🔄 Stock actualizado.")

# --- MÓDULO 3: DESPACHO ---
elif menu == "📤 Despacho":
    st.header("Salida a Cliente")
    with st.form("despacho"):
        sku = st.text_input("SKU")
        cont = st.text_input("Contenedor")
        fv = st.date_input("Fecha Vencimiento")
        est = st.selectbox("Estado Origen", ["Disponible", "Distribuidores"])
        cant = st.number_input("Cantidad", min_value=1)
        cli = st.text_input("Cliente")
        guia = st.text_input("Guía de Salida")
        if st.form_submit_button("Ejecutar Salida"):
            actualizar_inventario(sku, cont, est, fv, -cant)
            registrar_movimiento("SALIDA_DESPACHO", sku, cont, est, fv, cant, guia, cli)
            st.success(f"📦 Salida registrada para {cli}")

# --- MÓDULO 4: ESTADO PACKING LIST (LA VISTA QUE PEDISTE) ---
elif menu == "📋 Estado Packing List":
    st.header("Estado de Recepción por Contenedor")
    
    # Cargar y limpiar Packing List
    df_pl = pd.DataFrame(ws_pl.get_all_records())
    if not df_pl.empty:
        df_pl.columns = df_pl.columns.str.strip().str.lower()
    
    # Cargar y limpiar Movimientos
    df_mov = pd.DataFrame(ws_mov.get_all_records())
    if not df_mov.empty:
        df_mov.columns = df_mov.columns.str.strip().str.lower()
    else:
        df_mov = pd.DataFrame(columns=['fecha_hora', 'tipo_mov', 'sku', 'contenedor', 'estado', 'cantidad', 'referencia', 'cliente', 'fecha_vencimiento'])

    if df_pl.empty:
        st.warning("Hoja 'packing_list' sin datos.")
    else:
        f_cont = st.selectbox("Seleccionar Contenedor:", ["Todos"] + sorted(list(df_pl['contenedor'].astype(str).unique())))
        
        # Calcular Ingresos Reales
        df_real = df_mov[df_mov['tipo_mov'].isin(['INGRESO_PL', 'AUTO_INGRESO'])]
        if not df_real.empty:
            df_real_sum = df_real.groupby(['sku', 'contenedor'])['cantidad'].sum().reset_index()
            df_real_sum.columns = ['sku', 'contenedor', 'qty_in']
        else:
            df_real_sum = pd.DataFrame(columns=['sku', 'contenedor', 'qty_in'])
        
        # Cruce de datos
        df_pl['sku'] = df_pl['sku'].astype(str)
        df_pl['contenedor'] = df_pl['contenedor'].astype(str)
        df_real_sum['sku'] = df_real_sum['sku'].astype(str)
        df_real_sum['contenedor'] = df_real_sum['contenedor'].astype(str)
        
        res = pd.merge(df_pl, df_real_sum, on=['sku', 'contenedor'], how='left').fillna(0)
        res['dif'] = res['qty_in'] - res['cantidad_pl']
        
        # Formatear columnas finales (Estilo de tu imagen)
        view = res[['sku', 'descripcion', 'contenedor', 'cantidad_pl', 'qty_in', 'dif', 'fecha_ingreso', 'estado']]
        view.columns = ['COD II', 'DESCRIPCIÓN', 'NRO CONT', 'QTY PL', 'QTY IN', 'DIF', 'FECH INC', 'ESTADO']
        
        if f_cont != "Todos":
            view = view[view['NRO CONT'] == f_cont]
        
        st.dataframe(view.style.applymap(
            lambda x: 'color: red' if isinstance(x, (int, float)) and x < 0 else None, subset=['DIF']
        ), use_container_width=True)

# --- MÓDULO 5: REPORTES ---
elif menu == "📊 Reportes":
    st.header("Reporte de Movimientos")
    df_mov = pd.DataFrame(ws_mov.get_all_records())
    if not df_mov.empty:
        df_mov.columns = df_mov.columns.str.strip().str.lower()
        st.dataframe(df_mov.sort_values(by="fecha_hora", ascending=False), use_container_width=True)
    else:
        st.info("No hay historial.")
