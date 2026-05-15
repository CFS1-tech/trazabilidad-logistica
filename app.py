import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="WMS Trazabilidad Pro", layout="wide")

@st.cache_resource
def conectar_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    except:
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return gspread.authorize(creds).open("LOGISTICA_TRAZABILIDAD")

gc = conectar_gsheet()
ws_inv, ws_mov, ws_pl = gc.worksheet("inventario"), gc.worksheet("movimientos"), gc.worksheet("packing_list")

# --- FUNCIÓN DE LIMPIEZA DE DATOS (ELIMINA EL ERROR DE REGISTROS OCULTOS) ---
def cargar_datos_seguros(worksheet):
    df = pd.DataFrame(worksheet.get_all_records())
    if not df.empty:
        df.columns = df.columns.str.strip().str.lower()
        # Convertimos todo a string para evitar errores de comparación iniciales
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    return df

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("MENÚ", ["📦 Reporte de Stock", "📊 Historial Movimientos", "📋 Estado Packing List"])

# --- 1. REPORTE DE STOCK CON BOTÓN ---
if menu == "📦 Reporte de Stock":
    st.header("Inventario en Bodega")
    df_inv = cargar_datos_seguros(ws_inv)
    
    if not df_inv.empty:
        with st.container(border=True):
            c1, c2 = st.columns(2)
            f_cont = c1.multiselect("Contenedor:", sorted(df_inv['contenedor'].unique()))
            f_sku = c2.text_input("SKU:")
            btn_stock = st.button("🔍 Buscar en Inventario")
        
        if btn_stock or (not f_cont and not f_sku):
            df_res = df_inv.copy()
            if f_cont: df_res = df_res[df_res['contenedor'].isin(f_cont)]
            if f_sku: df_res = df_res[df_res['sku'].str.contains(f_sku, case=False)]
            st.dataframe(df_res, use_container_width=True)

# --- 2. HISTORIAL CON BOTÓN Y CORRECCIÓN DE REGISTROS INVISIBLES ---
elif menu == "📊 Historial Movimientos":
    st.header("Trazabilidad Total")
    df_mov = cargar_datos_seguros(ws_mov)
    
    if not df_mov.empty:
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            f_ini = c1.date_input("Desde:", datetime.now() - timedelta(days=90))
            f_fin = c2.date_input("Hasta:", datetime.now())
            f_cont_h = c3.multiselect("Contenedor:", sorted(df_mov['contenedor'].unique()))
            f_sku_h = st.text_input("SKU:")
            btn_hist = st.button("🔍 Filtrar Historial")

        # Intentamos convertir fechas para el filtro, pero sin borrar datos si falla
        df_mov['fecha_dt'] = pd.to_datetime(df_mov['fecha_hora'], errors='coerce', dayfirst=True)
        
        if btn_hist:
            df_f = df_mov.copy()
            # Filtrar por fecha solo si la conversión fue exitosa
            mask_fecha = (df_f['fecha_dt'].dt.date >= f_ini) & (df_f['fecha_dt'].dt.date <= f_fin)
            # Mantenemos también las filas donde la fecha falló para que NO DESAPAREZCAN
            df_f = df_f[mask_fecha | df_f['fecha_dt'].isna()]
            
            if f_cont_h: df_f = df_f[df_f['contenedor'].isin(f_cont_h)]
            if f_sku_h: df_f = df_f[df_f['sku'].str.contains(f_sku_h, case=False)]
            
            st.write(f"Mostrando {len(df_f)} registros (incluyendo fechas con formato irregular)")
            st.dataframe(df_f.drop(columns=['fecha_dt']), use_container_width=True)
        else:
            # Por defecto mostrar todo lo reciente
            st.dataframe(df_mov.head(100), use_container_width=True)

# --- 3. PACKING LIST CON BOTÓN ---
elif menu == "📋 Estado Packing List":
    st.header("Estado de Recepción")
    df_pl = cargar_datos_seguros(ws_pl)
    df_mov = cargar_datos_seguros(ws_mov)
    
    with st.container(border=True):
        cont_f = st.selectbox("Seleccionar Contenedor:", ["Ver Todos"] + sorted(list(df_pl['contenedor'].unique())))
        btn_pl = st.button("🔍 Verificar Estado")

    if btn_pl:
        # Lógica de cruce
        df_real = df_mov[df_mov['tipo_mov'] == "INGRESO_PL"]
        df_real['cantidad'] = pd.to_numeric(df_real['cantidad'], errors='coerce').fillna(0)
        df_sum = df_real.groupby(['sku', 'contenedor'])['cantidad'].sum().reset_index()
        
        res = pd.merge(df_pl, df_sum, on=['sku', 'contenedor'], how='left').fillna(0)
        if cont_f != "Ver Todos":
            res = res[res['contenedor'] == cont_f]
        
        st.dataframe(res, use_container_width=True)
