import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema WMS Trazabilidad", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS ---
def conectar_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # Credenciales desde st.secrets (para Streamlit Cloud)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    except:
        # Credenciales locales (archivo json)
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    
    client = gspread.authorize(creds)
    return client.open("LOGISTICA_TRAZABILIDAD")

# Inicializar hojas
sheet = conectar_gsheet()
ws_pl = sheet.worksheet("packing_list")
ws_inv = sheet.worksheet("inventario")
ws_mov = sheet.worksheet("movimientos")

# --- FUNCIONES CORE ---
def registrar_movimiento(tipo, sku, cont, est, fv, cant, ref, cliente="N/A"):
    ws_mov.append_row([str(datetime.now()), tipo, str(sku), str(cont), est, cant, ref, cliente, str(fv)])

def actualizar_inventario(sku, cont, est, fv, cant):
    df_inv = pd.DataFrame(ws_inv.get_all_records())
    fv_str = str(fv)
    
    # Buscamos coincidencia exacta por SKU, Contenedor, Estado y FV
    match = df_inv[
        (df_inv['sku'].astype(str) == str(sku)) & 
        (df_inv['contenedor'].astype(str) == str(cont)) & 
        (df_inv['estado'] == est) & 
        (df_inv['fecha_vencimiento'].astype(str) == fv_str)
    ]
    
    if match.empty:
        ws_inv.append_row([str(sku), str(cont), est, fv_str, cant])
    else:
        row_idx = match.index[0] + 2
        new_val = int(match.iloc[0]['stock_actual']) + cant
        ws_inv.update_cell(row_idx, 5, new_val)

# --- INTERFAZ ---
st.sidebar.title("Módulos WMS")
menu = st.sidebar.radio("Ir a:", [
    "📥 Ingreso Físico", 
    "🔄 Reclasificación", 
    "📤 Despachos", 
    "📋 Estado Packing List", 
    "📊 Reportes"
])

# --- MODULO 1: INGRESO FÍSICO ---
if menu == "📥 Ingreso Físico":
    st.header("Registro de Ingreso Físico")
    with st.form("form_ingreso"):
        c1, c2 = st.columns(2)
        sku = c1.text_input("SKU / COD II")
        cont = c1.text_input("N° Contenedor")
        est = c2.selectbox("Estado de Ingreso", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
        fv = c2.date_input("Fecha de Vencimiento")
        cant = st.number_input("Cantidad Real Recibida", min_value=1)
        ref = st.text_input("N° Guía / Referencia")
        if st.form_submit_button("Confirmar Ingreso"):
            actualizar_inventario(sku, cont, est, fv, cant)
            registrar_movimiento("INGRESO_PL", sku, cont, est, fv, cant, ref)
            st.success("✅ Ingreso registrado exitosamente.")

# --- MODULO 2: RECLASIFICACIÓN ---
elif menu == "🔄 Reclasificación":
    st.header("Cambio de Estado de Producto")
    with st.form("form_recla"):
        sku = st.text_input("SKU / COD II")
        cont = st.text_input("N° Contenedor")
        fv = st.date_input("Fecha Vencimiento del Lote")
        c1, c2 = st.columns(2)
        est_orig = c1.selectbox("De Estado:", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
        est_dest = c2.selectbox("A Estado:", ["Merma", "Bandejas", "Disponible", "Distribuidores"])
        cant = st.number_input("Cantidad a mover", min_value=1)
        if st.form_submit_button("Ejecutar Cambio"):
            actualizar_inventario(sku, cont, est_orig, fv, -cant)
            actualizar_inventario(sku, cont, est_dest, fv, cant)
            registrar_movimiento("RECLASIFICACION", sku, cont, est_dest, fv, cant, f"De {est_orig}")
            st.success("🔄 Estado actualizado en inventario.")

# --- MODULO 3: DESPACHOS ---
elif menu == "📤 Despachos":
    st.header("Salida / Despacho a Clientes")
    with st.form("form_despacho"):
        c1, c2 = st.columns(2)
        sku = c1.text_input("SKU / COD II")
        cont = c1.text_input("N° Contenedor")
        est = c2.selectbox("Estado de Origen", ["Disponible", "Distribuidores"])
        fv = c2.date_input("Fecha Vencimiento")
        cant = st.number_input("Cantidad a Despachar", min_value=1)
        cliente = st.text_input("Cliente Destino")
        guia = st.text_input("N° Guía de Salida")
        if st.form_submit_button("Procesar Salida"):
            actualizar_inventario(sku, cont, est, fv, -cant)
            registrar_movimiento("SALIDA_DESPACHO", sku, cont, est, fv, cant, guia, cliente)
            st.success(f"📦 Despacho realizado para {cliente}")

# --- MODULO 4: VISTA DE ESTADO PACKING LIST (TU PEDIDO) ---
elif menu == "📋 Estado Packing List":
    st.header("Control de Recepción vs Packing List")
    
    df_pl = pd.DataFrame(ws_pl.get_all_records())
    df_mov = pd.DataFrame(ws_mov.get_all_records())
    
    if df_pl.empty:
        st.warning("El Packing List está vacío. Por favor cargue datos en la pestaña 'packing_list'.")
    else:
        # Filtro por contenedor
        lista_contenedores = ["Todos"] + sorted(list(df_pl['contenedor'].astype(str).unique()))
        f_cont = st.selectbox("Filtrar por N° Contenedor:", lista_contenedores)
        
        # Procesar QTY IN (Suma de ingresos)
        df_real = df_mov[df_mov['tipo_mov'].isin(['INGRESO_PL', 'AUTO_INGRESO'])]
        if not df_real.empty:
            df_real_sum = df_real.groupby(['sku', 'contenedor'])['cantidad'].sum().reset_index()
            df_real_sum.columns = ['sku', 'contenedor', 'QTY IN']
        else:
            df_real_sum = pd.DataFrame(columns=['sku', 'contenedor', 'QTY IN'])
        
        # Unir y calcular
        df_pl['sku'] = df_pl['sku'].astype(str)
        df_pl['contenedor'] = df_pl['contenedor'].astype(str)
        df_real_sum['sku'] = df_real_sum['sku'].astype(str)
        df_real_sum['contenedor'] = df_real_sum['contenedor'].astype(str)
        
        merged = pd.merge(df_pl, df_real_sum, on=['sku', 'contenedor'], how='left').fillna(0)
        merged['DIF'] = merged['QTY IN'] - merged['cantidad_pl']
        
        # Formatear vista final
        final_view = merged[[
            'sku', 'descripcion', 'contenedor', 'cantidad_pl', 'QTY IN', 'DIF', 'fecha_ingreso', 'estado'
        ]]
        final_view.columns = ['COD II', 'DESCRIPCIÓN', 'NRO CONT', 'QTY PL', 'QTY IN', 'DIF', 'FECH INC', 'ESTADO']
        
        if f_cont != "Todos":
            final_view = final_view[final_view['NRO CONT'] == f_cont]
        
        # Estilos: Rojo para diferencias negativas
        st.dataframe(final_view.style.applymap(
            lambda x: 'color: red' if isinstance(x, (int, float)) and x < 0 else None,
            subset=['DIF']
        ), use_container_width=True)

# --- MODULO 5: REPORTES GENERALES ---
elif menu == "📊 Reportes":
    st.header("Reportes de Trazabilidad Total")
    df_mov = pd.DataFrame(ws_mov.get_all_records())
    
    if df_mov.empty:
        st.info("No hay movimientos registrados.")
    else:
        st.subheader("Kardex de Movimientos")
        # Filtros de reporte
        c1, c2 = st.columns(2)
        f_c = c1.selectbox("Contenedor", ["Todos"] + list(df_mov['contenedor'].unique()))
        f_s = c2.selectbox("SKU", ["Todos"] + list(df_mov['sku'].unique()))
        
        df_rep = df_mov.copy()
        if f_c != "Todos": df_rep = df_rep[df_rep['contenedor'] == str(f_c)]
        if f_s != "Todos": df_rep = df_rep[df_rep['sku'] == str(f_s)]
        
        st.dataframe(df_rep.sort_values(by="fecha_hora", ascending=False), use_container_width=True)
