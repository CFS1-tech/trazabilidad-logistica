import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="WMS Trazabilidad Pro", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def conectar_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # Intento con secretos de Streamlit Cloud
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    except:
        # Intento local con archivo json
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return gspread.authorize(creds).open("LOGISTICA_TRAZABILIDAD")

gc = conectar_gsheet()
ws_pl = gc.worksheet("packing_list")
ws_inv = gc.worksheet("inventario")
ws_mov = gc.worksheet("movimientos")
ws_pick = gc.worksheet("picking")

# --- FUNCIONES DE UTILIDAD (LIMPIEZA Y ROBUSTEZ) ---

def convertir_fecha_robusta(serie):
    """Convierte fechas ISO de Python y fechas manuales DD/MM/YYYY."""
    return pd.to_datetime(serie, errors='coerce', dayfirst=True)

def registrar_movimiento(tipo, sku, cont, est, fv, cant, ref, cliente="N/A", fecha_manual=None):
    fecha = str(fecha_manual) if fecha_manual else str(datetime.now())
    ws_mov.append_row([fecha, tipo, str(sku).strip(), str(cont).strip(), est, cant, ref, cliente, str(fv)])

def actualizar_inventario(sku, cont, est, fv, cant):
    data = ws_inv.get_all_records()
    df_inv = pd.DataFrame(data)
    if not df_inv.empty: 
        df_inv.columns = df_inv.columns.str.strip().str.lower()
    
    sku_s, cont_s, fv_s = str(sku).strip(), str(cont).strip(), str(fv)
    
    if not df_inv.empty:
        match = df_inv[
            (df_inv['sku'].astype(str) == sku_s) & 
            (df_inv['contenedor'].astype(str) == cont_s) & 
            (df_inv['estado'] == est) & 
            (df_inv['fecha_vencimiento'].astype(str) == fv_s)
        ]
    else:
        match = pd.DataFrame()

    if match.empty:
        if cant > 0: ws_inv.append_row([sku_s, cont_s, est, fv_s, cant])
    else:
        row_idx = match.index[0] + 2
        val_actual = pd.to_numeric(match.iloc[0]['stock_actual'], errors='coerce') or 0
        ws_inv.update_cell(row_idx, 5, int(val_actual + cant))

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("MENÚ PRINCIPAL", [
    "🚀 Operaciones de Bodega", 
    "📦 Reporte de Stock", 
    "📋 Estado Packing List", 
    "📊 Historial Movimientos",
    "💡 Insights de Inventario"
])

# --- 1. OPERACIONES DE BODEGA ---
if menu == "🚀 Operaciones de Bodega":
    operacion = st.selectbox("Operación:", ["Ingreso Físico", "Picking (Preparación)", "Despacho Directo", "Reclasificación"])
    st.divider()

    if operacion == "Ingreso Físico":
        st.subheader("📥 Registro de Ingreso")
        df_pl = pd.DataFrame(ws_pl.get_all_records())
        if not df_pl.empty:
            df_pl.columns = df_pl.columns.str.strip().str.lower()
            cont_sel = st.selectbox("Contenedor:", sorted(df_pl['contenedor'].unique().astype(str)))
            sku_sel = st.selectbox("SKU:", sorted(df_pl[df_pl['contenedor'].astype(str)==cont_sel]['sku'].unique().astype(str)))
            with st.form("f_ing"):
                c1, c2 = st.columns(2)
                est = c1.selectbox("Estado", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
                fv = c1.date_input("Vencimiento")
                cant = c2.number_input("Cantidad Recibida:", min_value=0, step=1)
                ref = c2.text_input("Ref / Guía")
                if st.form_submit_button("Guardar"):
                    actualizar_inventario(sku_sel, cont_sel, est, fv, cant)
                    registrar_movimiento("INGRESO_PL", sku_sel, cont_sel, est, fv, cant, ref)
                    st.success("✅ Guardado correctamente")

    elif operacion in ["Picking (Preparación)", "Despacho Directo"]:
        tipo = "PICKING" if operacion == "Picking (Preparación)" else "DESPACHO"
        st.subheader(f"📤 Registro de {tipo}")
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Cliente:")
        guia = c2.text_input("Guía de Salida:") if tipo == "DESPACHO" else "RESERVA"
        
        df_inv = pd.DataFrame(ws_inv.get_all_records())
        if not df_inv.empty:
            df_inv.columns = df_inv.columns.str.strip().str.lower()
            df_inv['stock_actual'] = pd.to_numeric(df_inv['stock_actual'], errors='coerce').fillna(0)
            df_inv = df_inv[df_inv['stock_actual'] > 0]
            
            sku_p = st.selectbox("SKU:", ["Seleccione..."] + sorted(df_inv['sku'].unique().astype(str)))
            if sku_p != "Seleccione...":
                opciones = df_inv[df_inv['sku'].astype(str)==sku_p]
                st.dataframe(opciones, use_container_width=True)
                with st.form("f_salida"):
                    sel = st.selectbox("Origen:", [f"{r['contenedor']} | {r['estado']} | {r['fecha_vencimiento']}" for _, r in opciones.iterrows()])
                    cant_s = st.number_input("Cantidad:", min_value=1, step=1)
                    if st.form_submit_button("Confirmar"):
                        idx = [f"{r['contenedor']} | {r['estado']} | {r['fecha_vencimiento']}" for _, r in opciones.iterrows()].index(sel)
                        fila = opciones.iloc[idx]
                        if tipo == "PICKING":
                            ws_pick.append_row([str(datetime.now().timestamp()), sku_p, str(fila['contenedor']), fila['estado'], str(fila['fecha_vencimiento']), cant_s, cliente, str(datetime.now().date())])
                            actualizar_inventario(sku_p, fila['contenedor'], fila['estado'], fila['fecha_vencimiento'], -cant_s)
                            registrar_movimiento("PICKING_REGISTRO", sku_p, fila['contenedor'], fila['estado'], fila['fecha_vencimiento'], cant_s, "RESERVA", cliente)
                        else:
                            actualizar_inventario(sku_p, fila['contenedor'], fila['estado'], fila['fecha_vencimiento'], -cant_s)
                            registrar_movimiento("SALIDA_DESPACHO", sku_p, fila['contenedor'], fila['estado'], fila['fecha_vencimiento'], cant_s, guia, cliente)
                        st.success("✅ Operación Exitosa"); st.rerun()

# --- 2. REPORTE DE STOCK (CON FILTROS SKU Y CONTENEDOR) ---
elif menu == "📦 Reporte de Stock":
    st.header("Inventario en Bodega")
    df_inv = pd.DataFrame(ws_inv.get_all_records())
    if not df_inv.empty:
        df_inv.columns = df_inv.columns.str.strip().str.lower()
        df_inv['stock_actual'] = pd.to_numeric(df_inv['stock_actual'], errors='coerce').fillna(0)
        
        c1, c2 = st.columns(2)
        f_cont = c1.multiselect("Filtrar Contenedor:", sorted(df_inv['contenedor'].unique().astype(str)))
        f_sku = c2.text_input("Filtrar SKU (parcial o completo):")
        
        df_res = df_inv[df_inv['stock_actual'] > 0]
        if f_cont: df_res = df_res[df_res['contenedor'].astype(str).isin(f_cont)]
        if f_sku: df_res = df_res[df_res['sku'].astype(str).str.contains(f_sku, case=False)]
        
        st.dataframe(df_res, use_container_width=True)

# --- 3. ESTADO PACKING LIST (FILTRO CONTENEDOR) ---
elif menu == "📋 Estado Packing List":
    st.header("Cruce Packing List vs Real")
    df_pl = pd.DataFrame(ws_pl.get_all_records())
    df_mov = pd.DataFrame(ws_mov.get_all_records())
    if not df_pl.empty:
        df_pl.columns = df_pl.columns.str.strip().str.lower()
        df_mov.columns = df_mov.columns.str.strip().str.lower()
        
        f_cont_pl = st.selectbox("Filtrar por Contenedor:", ["Todos"] + sorted(list(df_pl['contenedor'].unique().astype(str))))
        
        df_real = df_mov[df_mov['tipo_mov'] == "INGRESO_PL"].groupby(['sku', 'contenedor'])['cantidad'].sum().reset_index()
        res = pd.merge(df_pl, df_real, on=['sku', 'contenedor'], how='left').fillna(0)
        res['dif'] = res['cantidad'] - res['cantidad_pl'] # Ajustado segun tus columnas
        
        if f_cont_pl != "Todos": res = res[res['contenedor'].astype(str) == f_cont_pl]
        st.dataframe(res, use_container_width=True)

# --- 4. HISTORIAL (FILTROS FECHA, CONTENEDOR Y SKU) ---
elif menu == "📊 Historial Movimientos":
    st.header("Trazabilidad Histórica")
    df_mov = pd.DataFrame(ws_mov.get_all_records())
    if not df_mov.empty:
        df_mov.columns = df_mov.columns.str.strip().str.lower()
        df_mov['fecha_hora'] = convertir_fecha_robusta(df_mov['fecha_hora'])
        
        c1, c2, c3 = st.columns(3)
        f_ini = c1.date_input("Desde:", datetime.now() - timedelta(days=60))
        f_fin = c2.date_input("Hasta:", datetime.now())
        f_cont_h = c3.multiselect("Contenedor:", sorted(df_mov['contenedor'].unique().astype(str)))
        f_sku_h = st.text_input("SKU en Historial:")
        
        df_f = df_mov.dropna(subset=['fecha_hora'])
        df_f = df_f[(df_f['fecha_hora'].dt.date >= f_ini) & (df_f['fecha_hora'].dt.date <= f_fin)]
        if f_cont_h: df_f = df_f[df_f['contenedor'].astype(str).isin(f_cont_h)]
        if f_sku_h: df_f = df_f[df_f['sku'].astype(str).str.contains(f_sku_h, case=False)]
        
        st.dataframe(df_f.sort_values(by='fecha_hora', ascending=False), use_container_width=True)

# --- 5. INSIGHTS INTELIGENTES ---
elif menu == "💡 Insights de Inventario":
    st.header("Análisis de Inventario Crítico")
    df_inv = pd.DataFrame(ws_inv.get_all_records())
    df_mov = pd.DataFrame(ws_mov.get_all_records())
    
    if not df_inv.empty:
        df_inv.columns = df_inv.columns.str.strip().str.lower()
        df_inv['fecha_vencimiento'] = convertir_fecha_robusta(df_inv['fecha_vencimiento'])
        df_inv['stock_actual'] = pd.to_numeric(df_inv['stock_actual'], errors='coerce').fillna(0)
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🚨 Próximos Vencimientos (60 días)")
            prox = df_inv[df_inv['fecha_vencimiento'] <= (datetime.now() + timedelta(days=60))]
            st.dataframe(prox[['sku', 'contenedor', 'fecha_vencimiento', 'stock_actual']].sort_values('fecha_vencimiento'), use_container_width=True)
        
        with c2:
            st.subheader("🐢 Antigüedad (FIFO)")
            if not df_mov.empty:
                df_mov.columns = df_mov.columns.str.strip().str.lower()
                df_mov['fecha_hora'] = convertir_fecha_robusta(df_mov['fecha_hora'])
                entradas = df_mov[df_mov['tipo_mov'] == "INGRESO_PL"].groupby(['sku', 'contenedor'])['fecha_hora'].min().reset_index()
                entradas.columns = ['sku', 'contenedor', 'fecha_entrada']
                df_fifo = pd.merge(df_inv[df_inv['stock_actual']>0], entradas, on=['sku', 'contenedor'], how='left')
                st.dataframe(df_fifo[['sku', 'contenedor', 'fecha_entrada', 'stock_actual']].sort_values('fecha_entrada'), use_container_width=True)
