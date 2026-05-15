import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Trazabilidad Logística", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS ---
def conectar_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # En Streamlit Cloud, usaremos st.secrets para mayor seguridad
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    except:
        # Para uso local con archivo JSON
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    
    client = gspread.authorize(creds)
    return client.open("LOGISTICA_TRAZABILIDAD")

sheet = conectar_gsheet()
ws_pl = sheet.worksheet("packing_list")
ws_inv = sheet.worksheet("inventario")
ws_mov = sheet.worksheet("movimientos")

# --- FUNCIONES DE AYUDA ---
def registrar_movimiento(tipo, sku, cont, est, fv, cant, ref, cliente="N/A"):
    ws_mov.append_row([str(datetime.now()), tipo, sku, str(cont), est, cant, ref, cliente, str(fv)])

def actualizar_inventario(sku, cont, est, fv, cant):
    df_inv = pd.DataFrame(ws_inv.get_all_records())
    fv_str = str(fv)
    
    match = df_inv[
        (df_inv['sku'] == sku) & 
        (df_inv['contenedor'] == str(cont)) & 
        (df_inv['estado'] == est) & 
        (df_inv['fecha_vencimiento'] == fv_str)
    ]
    
    if match.empty:
        ws_inv.append_row([sku, str(cont), est, fv_str, cant])
    else:
        row_idx = match.index[0] + 2
        new_val = int(match.iloc[0]['stock_actual']) + cant
        ws_inv.update_cell(row_idx, 5, new_val)

# --- INTERFAZ ---
st.sidebar.title("Navegación")
menu = st.sidebar.radio("Seleccione una opción:", ["📥 Ingreso Físico", "🔄 Reclasificación", "📤 Despachos", "📊 Reportes"])

# --- MODULO 1: INGRESO ---
if menu == "📥 Ingreso Físico":
    st.header("Registro de Ingreso Real")
    with st.form("form_ingreso"):
        c1, c2 = st.columns(2)
        sku = c1.text_input("SKU")
        cont = c1.text_input("N° Contenedor (Obligatorio)")
        est = c2.selectbox("Estado", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
        fv = c2.date_input("Fecha de Vencimiento")
        cant = st.number_input("Cantidad Real", min_value=1)
        ref = st.text_input("N° Guía de Ingreso")
        if st.form_submit_button("Confirmar Ingreso"):
            actualizar_inventario(sku, cont, est, fv, cant)
            registrar_movimiento("INGRESO_PL", sku, cont, est, fv, cant, ref)
            st.success("✅ Ingreso registrado y stock actualizado.")

# --- MODULO 2: RECLASIFICACIÓN ---
elif menu == "🔄 Reclasificación":
    st.header("Cambio de Estado Interno")
    st.info("Mueve stock entre estados del mismo contenedor.")
    with st.form("form_recla"):
        sku = st.text_input("SKU")
        cont = st.text_input("N° Contenedor")
        fv = st.date_input("Fecha Vencimiento del lote")
        c1, c2 = st.columns(2)
        est_orig = c1.selectbox("De Estado:", ["Disponible", "Distribuidores", "Merma", "Bandejas"], key="e1")
        est_dest = c2.selectbox("A Estado:", ["Merma", "Bandejas", "Disponible", "Distribuidores"], key="e2")
        cant = st.number_input("Cantidad a Reclasificar", min_value=1)
        if st.form_submit_button("Ejecutar Cambio"):
            actualizar_inventario(sku, cont, est_orig, fv, -cant)
            actualizar_inventario(sku, cont, est_dest, fv, cant)
            registrar_movimiento("RECLASIFICACION", sku, cont, est_dest, fv, cant, f"Desde {est_orig}")
            st.success("🔄 Stock reclasificado con éxito.")

# --- MODULO 3: DESPACHOS ---
elif menu == "📤 Despachos":
    st.header("Salida de Productos (Despacho)")
    with st.form("form_despacho"):
        c1, c2 = st.columns(2)
        sku = c1.text_input("SKU")
        cont = c1.text_input("N° Contenedor")
        est = c2.selectbox("Extraer de Estado", ["Disponible", "Distribuidores"])
        fv = c2.date_input("Fecha Vencimiento")
        cant = st.number_input("Cantidad a Despachar", min_value=1)
        cliente = st.text_input("Nombre del Cliente")
        guia = st.text_input("N° Guía de Salida")
        if st.form_submit_button("Procesar Salida"):
            actualizar_inventario(sku, cont, est, fv, -cant)
            registrar_movimiento("SALIDA_DESPACHO", sku, cont, est, fv, cant, guia, cliente)
            st.success(f"📦 Salida registrada para {cliente}")

# --- MODULO 4: REPORTES ---
elif menu == "📊 Reportes":
    st.header("Panel de Control y Trazabilidad")
    df_mov = pd.DataFrame(ws_mov.get_all_records())
    df_inv = pd.DataFrame(ws_inv.get_all_records())
    df_pl = pd.DataFrame(ws_pl.get_all_records())

    st.subheader("🔍 Filtros de Trazabilidad")
    c1, c2, c3 = st.columns(3)
    f_cont = c1.selectbox("Contenedor", ["Todos"] + list(df_mov['contenedor'].unique()))
    f_est = c2.selectbox("Estado", ["Todos"] + list(df_mov['estado'].unique()))
    f_sku = c3.selectbox("SKU", ["Todos"] + list(df_mov['sku'].unique()))

    df_f = df_mov.copy()
    if f_cont != "Todos": df_f = df_f[df_f['contenedor'] == f_cont]
    if f_est != "Todos": df_f = df_f[df_f['estado'] == f_est]
    if f_sku != "Todos": df_f = df_f[df_f['sku'] == f_sku]

    st.write("### Historial Detallado (Kardex)")
    st.dataframe(df_f.sort_values(by="fecha_hora", ascending=False))

    st.write("### Comparativo Packing List vs Real")
    ingresos = df_mov[df_mov['tipo_mov'].isin(['INGRESO_PL', 'AUTO_INGRESO'])].groupby('sku')['cantidad'].sum().reset_index()
    reporte_dif = pd.merge(df_pl, ingresos, on='sku', how='left').fillna(0)
    reporte_dif.columns = ['SKU', 'Descripción', 'Cant. Packing List', 'Cant. Ingreso Real']
    reporte_dif['Diferencia'] = reporte_dif['Cant. Ingreso Real'] - reporte_dif['Cant. Packing List']
    st.table(reporte_dif)