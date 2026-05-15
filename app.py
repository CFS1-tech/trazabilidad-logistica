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
        # Para Streamlit Cloud usando Secrets
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    except:
        # Para uso local
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    
    client = gspread.authorize(creds)
    return client.open("LOGISTICA_TRAZABILIDAD")

try:
    sheet = conectar_gsheet()
    ws_pl = sheet.worksheet("packing_list")
    ws_inv = sheet.worksheet("inventario")
    ws_mov = sheet.worksheet("movimientos")
except Exception as e:
    st.error(f"Error de conexión: {e}. Revisa el nombre de la hoja y las credenciales.")

# --- FUNCIONES CORE ---

def registrar_movimiento(tipo, sku, cont, est, fv, cant, ref, cliente="N/A"):
    ws_mov.append_row([str(datetime.now()), tipo, sku, str(cont), est, cant, ref, cliente, str(fv)])

def actualizar_inventario(sku, cont, est, fv, cant):
    df_inv = pd.DataFrame(ws_inv.get_all_records())
    fv_str = str(fv)
    
    # Buscamos coincidencia exacta por el "trío obligatorio" + SKU
    match = df_inv[
        (df_inv['sku'] == sku) & 
        (df_inv['contenedor'] == str(cont)) & 
        (df_inv['estado'] == est) & 
        (df_inv['fecha_vencimiento'] == fv_str)
    ]
    
    if match.empty:
        # Si no existe, crea el registro (Flexibilidad para ingresos nuevos o estados nuevos)
        ws_inv.append_row([sku, str(cont), est, fv_str, cant])
    else:
        # Si existe, actualiza la celda de stock_actual
        row_idx = match.index[0] + 2
        new_val = int(match.iloc[0]['stock_actual']) + cant
        ws_inv.update_cell(row_idx, 5, new_val)

# --- INTERFAZ ---
st.sidebar.title("Módulos")
menu = st.sidebar.radio("Ir a:", ["📥 Ingreso Físico", "🔄 Reclasificación", "📤 Despachos", "📊 Reportes"])

# --- INGRESO FÍSICO ---
if menu == "📥 Ingreso Físico":
    st.header("Registro de Ingreso Físico")
    with st.form("form_ingreso"):
        c1, c2 = st.columns(2)
        sku = c1.text_input("SKU")
        cont = c1.text_input("N° Contenedor")
        est = c2.selectbox("Estado", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
        fv = c2.date_input("Fecha de Vencimiento")
        cant = st.number_input("Cantidad Real Recibida", min_value=1)
        ref = st.text_input("N° Guía / Referencia")
        if st.form_submit_button("Registrar Ingreso"):
            actualizar_inventario(sku, cont, est, fv, cant)
            registrar_movimiento("INGRESO_PL", sku, cont, est, fv, cant, ref)
            st.success("✅ Stock ingresado correctamente.")

# --- RECLASIFICACIÓN ---
elif menu == "🔄 Reclasificación":
    st.header("Cambio de Estado e Inventario")
    with st.form("form_recla"):
        sku = st.text_input("SKU")
        cont = st.text_input("N° Contenedor")
        fv = st.date_input("Fecha Vencimiento")
        c1, c2 = st.columns(2)
        est_orig = c1.selectbox("De Estado:", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
        est_dest = c2.selectbox("A Estado:", ["Merma", "Bandejas", "Disponible", "Distribuidores"])
        cant = st.number_input("Cantidad a mover", min_value=1)
        if st.form_submit_button("Confirmar Reclasificación"):
            actualizar_inventario(sku, cont, est_orig, fv, -cant)
            actualizar_inventario(sku, cont, est_dest, fv, cant)
            registrar_movimiento("RECLASIFICACION", sku, cont, est_dest, fv, cant, f"De {est_orig}")
            st.success("🔄 Cambio de estado realizado.")

# --- DESPACHOS ---
elif menu == "📤 Despachos":
    st.header("Salida / Despacho de Mercadería")
    with st.form("form_despacho"):
        c1, c2 = st.columns(2)
        sku = c1.text_input("SKU")
        cont = c1.text_input("N° Contenedor")
        est = c2.selectbox("Estado de Origen", ["Disponible", "Distribuidores"])
        fv = c2.date_input("Fecha Vencimiento")
        cant = st.number_input("Cantidad a Despachar", min_value=1)
        cliente = st.text_input("Cliente")
        guia = st.text_input("N° Guía de Salida")
        if st.form_submit_button("Ejecutar Despacho"):
            actualizar_inventario(sku, cont, est, fv, -cant)
            registrar_movimiento("SALIDA_DESPACHO", sku, cont, est, fv, cant, guia, cliente)
            st.success(f"📦 Salida enviada a {cliente}")

# --- REPORTES ---
elif menu == "📊 Reportes":
    st.header("Reportes y Trazabilidad")
    
    # Cargar Data
    df_mov = pd.DataFrame(ws_mov.get_all_records())
    df_inv = pd.DataFrame(ws_inv.get_all_records())
    df_pl = pd.DataFrame(ws_pl.get_all_records())

    if df_mov.empty:
        st.warning("No hay movimientos registrados aún.")
    else:
        # Filtros
        st.subheader("🔍 Filtros Dinámicos")
        c1, c2, c3 = st.columns(3)
        f_cont = c1.selectbox("Filtrar Contenedor", ["Todos"] + list(df_mov['contenedor'].unique()))
        f_est = c2.selectbox("Filtrar Estado", ["Todos"] + list(df_mov['estado'].unique()))
        f_sku = c3.selectbox("Filtrar SKU", ["Todos"] + list(df_mov['sku'].unique()))

        # Aplicar Filtros al historial
        df_f = df_mov.copy()
        if f_cont != "Todos": df_f = df_f[df_f['contenedor'] == str(f_cont)]
        if f_est != "Todos": df_f = df_f[df_f['estado'] == f_est]
        if f_sku != "Todos": df_f = df_f[df_f['sku'] == f_sku]

        st.write("### 📜 Historial de Movimientos (Trazabilidad)")
        st.dataframe(df_f.sort_values(by="fecha_hora", ascending=False), use_container_width=True)

        # Reporte de Diferencias Packing List vs Real
        st.write("### ⚖️ Comparativa: Packing List vs Ingreso Real")
        # Solo sumamos ingresos iniciales para comparar con el PL
        ingresos_reales = df_mov[df_mov['tipo_mov'].isin(['INGRESO_PL', 'AUTO_INGRESO'])]
        reales_agrupado = ingresos_reales.groupby(['sku', 'contenedor'])['cantidad'].sum().reset_index()
        
        # Merge con PL incluyendo contenedor
        comparativo = pd.merge(df_pl, reales_agrupado, on=['sku', 'contenedor'], how='left').fillna(0)
        comparativo['Diferencia'] = comparativo['cantidad'] - comparativo['cantidad_pl']
        
        # Estética de tabla
        comparativo.columns = ['Contenedor', 'SKU', 'Descripción', 'Cantidad Esperada (PL)', 'Cantidad Recibida', 'Diferencia']
        st.table(comparativo)

        st.write("### 🏪 Stock Actual por Ubicación/Estado")
        st.dataframe(df_inv[df_inv['stock_actual'] != 0], use_container_width=True)
