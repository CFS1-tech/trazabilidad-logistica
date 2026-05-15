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
ws_pl, ws_inv, ws_mov, ws_pick = gc.worksheet("packing_list"), gc.worksheet("inventario"), gc.worksheet("movimientos"), gc.worksheet("picking")

# --- FUNCIÓN DE ESTANDARIZACIÓN DE FECHAS (EL CORAZÓN DEL SCRIPT) ---
def estandarizar_fechas(df, columna):
    if df.empty or columna not in df.columns:
        return df
    
    # Convertir a datetime de forma flexible (maneja formatos mixtos y errores)
    df[columna] = pd.to_datetime(df[columna], errors='coerce', dayfirst=True)
    
    # Ordenar por fecha (opcional, pero recomendado para trazabilidad)
    df = df.sort_values(by=columna, ascending=False)
    
    # Crear una columna de visualización bonita (String) para los reportes
    # Esto "chanca" el desorden visual y deja todo igual: DD/MM/YYYY HH:MM:SS
    df[f'{columna}_display'] = df[columna].dt.strftime('%d/%m/%Y %H:%M:%S').fillna("Fecha Inválida")
    return df

def cargar_datos_base(ws):
    df = pd.DataFrame(ws.get_all_records())
    if not df.empty:
        df.columns = df.columns.str.strip().str.lower()
    return df

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("MENÚ PRINCIPAL", ["🚀 Operaciones", "📦 Reporte de Stock", "📊 Historial", "📋 Packing List", "💡 Insights"])

# --- 1. OPERACIONES ---
if menu == "🚀 Operaciones":
    op = st.selectbox("Operación:", ["Ingreso Físico", "Picking", "Despacho Directo"])
    
    if op == "Ingreso Físico":
        st.subheader("📥 Ingreso")
        df_p = cargar_datos_base(ws_pl)
        if not df_p.empty:
            c_sel = st.selectbox("Contenedor:", sorted(df_p['contenedor'].astype(str).unique()))
            s_sel = st.selectbox("SKU:", sorted(df_p[df_p['contenedor'].astype(str)==c_sel]['sku'].astype(str).unique()))
            with st.form("f_ing"):
                c1, c2 = st.columns(2)
                est = c1.selectbox("Estado", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
                fv = c1.date_input("Vencimiento")
                cant = c2.number_input("Cantidad:", min_value=0)
                ref = c2.text_input("Guía/Ref")
                if st.form_submit_button("Confirmar"):
                    # Registro con timestamp limpio
                    fecha_ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ws_mov.append_row([fecha_ahora, "INGRESO_PL", str(s_sel), str(c_sel), est, cant, ref, "N/A", str(fv)])
                    st.success("✅ Registrado")

# --- 2. REPORTE DE STOCK ---
elif menu == "📦 Reporte de Stock":
    st.header("Inventario Real")
    df_i = cargar_datos_base(ws_inv)
    if not df_i.empty:
        # Estandarizar fecha de vencimiento
        df_i = estandarizar_fechas(df_i, 'fecha_vencimiento')
        
        with st.container(border=True):
            c1, c2 = st.columns(2)
            f_cont = c1.multiselect("Contenedor:", sorted(df_i['contenedor'].unique().astype(str)))
            f_sku = c2.text_input("SKU:")
            btn = st.button("🔍 Buscar en Stock")
        
        if btn or (not f_cont and not f_sku):
            res = df_i[pd.to_numeric(df_i['stock_actual'], errors='coerce') > 0].copy()
            if f_cont: res = res[res['contenedor'].astype(str).isin(f_cont)]
            if f_sku: res = res[res['sku'].astype(str).str.contains(f_sku, case=False)]
            
            # Mostramos la columna display y ocultamos la original de proceso
            cols_mostrar = ['sku', 'contenedor', 'estado', 'fecha_vencimiento_display', 'stock_actual']
            st.dataframe(res[cols_mostrar].rename(columns={'fecha_vencimiento_display': 'vencimiento'}), use_container_width=True)

# --- 3. HISTORIAL (EL MÁS AFECTADO POR FECHAS MIXTAS) ---
elif menu == "📊 Historial":
    st.header("Trazabilidad Homogénea")
    df_m = cargar_datos_base(ws_mov)
    if not df_m.empty:
        # Aquí "chancamos" todos los formatos a uno solo
        df_m = estandarizar_fechas(df_m, 'fecha_hora')
        
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            f_ini = c1.date_input("Desde:", datetime.now() - timedelta(days=90))
            f_fin = c2.date_input("Hasta:", datetime.now())
            f_c = c3.multiselect("Contenedor:", sorted(df_m['contenedor'].unique().astype(str)))
            f_s = st.text_input("SKU:")
            btn_h = st.button("🔍 Filtrar Historial")

        if btn_h:
            mask = (df_m['fecha_hora'].dt.date >= f_ini) & (df_m['fecha_hora'].dt.date <= f_fin)
            # Incluimos los NaT (fechas rotas) para que no desaparezcan registros
            res = df_m[mask | df_m['fecha_hora'].isna()].copy()
            
            if f_c: res = res[res['contenedor'].astype(str).isin(f_c)]
            if f_s: res = res[res['sku'].astype(str).str.contains(f_s, case=False)]
            
            # Limpiamos las columnas para mostrar solo lo importante con formato unificado
            display_cols = ['fecha_hora_display', 'tipo_mov', 'sku', 'contenedor', 'cantidad', 'referencia']
            st.dataframe(res[display_cols].rename(columns={'fecha_hora_display': 'fecha_hora'}), use_container_width=True)
        else:
            st.info("Use los filtros y presione Buscar para ver los movimientos.")

# --- 4. INSIGHTS (CORREGIDO KEYERROR) ---
elif menu == "💡 Insights":
    st.header("Análisis de Vencimientos y FIFO")
    df_i = cargar_datos_base(ws_inv)
    df_m = cargar_datos_base(ws_mov)
    
    if not df_i.empty:
        df_i = estandarizar_fechas(df_i, 'fecha_vencimiento')
        df_i['stock_actual'] = pd.to_numeric(df_i['stock_actual'], errors='coerce').fillna(0)
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🚨 Próximos Vencimientos")
            limite = datetime.now() + timedelta(days=60)
            prox = df_i[(df_i['fecha_vencimiento'] <= limite) & (df_i['stock_actual'] > 0)].copy()
            if not prox.empty:
                st.dataframe(prox[['sku', 'contenedor', 'fecha_vencimiento_display', 'stock_actual']], use_container_width=True)
        
        with c2:
            st.subheader("🐢 Antigüedad de Stock (FIFO)")
            if not df_m.empty:
                df_m = estandarizar_fechas(df_m, 'fecha_hora')
                ent = df_m[df_m['tipo_mov']=="INGRESO_PL"].groupby(['sku', 'contenedor'])['fecha_hora'].min().reset_index()
                ent.columns = ['sku', 'contenedor', 'fecha_entrada']
                
                res_fifo = pd.merge(df_i[df_i['stock_actual']>0], ent, on=['sku', 'contenedor'], how='left')
                res_fifo = res_fifo.sort_values('fecha_entrada')
                res_fifo['entrada_display'] = res_fifo['fecha_entrada'].dt.strftime('%d/%m/%Y')
                
                st.dataframe(res_fifo[['sku', 'contenedor', 'entrada_display', 'stock_actual']], use_container_width=True)
