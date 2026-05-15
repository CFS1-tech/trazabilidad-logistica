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

# --- FUNCIONES CORE ---
def registrar_movimiento(tipo, sku, cont, est, fv, cant, ref, cliente="N/A", fecha_manual=None):
    fecha = str(fecha_manual) if fecha_manual else str(datetime.now())
    ws_mov.append_row([fecha, tipo, str(sku).strip(), str(cont).strip(), est, cant, ref, cliente, str(fv)])

def actualizar_inventario(sku, cont, est, fv, cant):
    data = ws_inv.get_all_records()
    df_inv = pd.DataFrame(data)
    if not df_inv.empty: df_inv.columns = df_inv.columns.str.strip().str.lower()
    sku_s, cont_s, fv_s = str(sku).strip(), str(cont).strip(), str(fv)
    match = df_inv[(df_inv['sku'].astype(str)==sku_s) & (df_inv['contenedor'].astype(str)==cont_s) & (df_inv['estado']==est) & (df_inv['fecha_vencimiento'].astype(str)==fv_s)] if not df_inv.empty else pd.DataFrame()
    if match.empty: ws_inv.append_row([sku_s, cont_s, est, fv_s, cant])
    else: 
        val_actual = pd.to_numeric(match.iloc[0]['stock_actual'], errors='coerce') or 0
        ws_inv.update_cell(match.index[0]+2, 5, int(val_actual + cant))

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("MENÚ PRINCIPAL", [
    "🚀 Operaciones de Bodega", 
    "📦 Reporte de Stock", 
    "📋 Estado Packing List", 
    "📊 Historial Movimientos",
    "💡 Insights de Inventario"
])

# --- 1. OPERACIONES (Mantenido) ---
if menu == "🚀 Operaciones de Bodega":
    operacion = st.selectbox("Seleccione la operación:", ["Ingreso Físico", "Picking (Preparación)", "Despacho Directo (Salida)", "Reclasificación (Cambio Estado)"])
    st.divider()
    
    if operacion == "Ingreso Físico":
        df_pl_datos = pd.DataFrame(ws_pl.get_all_records())
        if not df_pl_datos.empty:
            df_pl_datos.columns = df_pl_datos.columns.str.strip().str.lower()
            cont_sel = st.selectbox("Contenedor:", sorted(list(df_pl_datos['contenedor'].astype(str).unique())))
            sku_sel = st.selectbox("SKU:", sorted(list(df_pl_datos[df_pl_datos['contenedor'].astype(str) == cont_sel]['sku'].astype(str).unique())))
            with st.form("f_ingreso"):
                c1, c2 = st.columns(2); est = c1.selectbox("Estado", ["Disponible", "Distribuidores", "Merma", "Bandejas"]); fv = c1.date_input("Vencimiento")
                cant = c2.number_input("Cantidad:", min_value=0, step=1); ref = c2.text_input("Referencia/Guía")
                if st.form_submit_button("Confirmar Ingreso"):
                    actualizar_inventario(sku_sel, cont_sel, est, fv, cant)
                    registrar_movimiento("INGRESO_PL", sku_sel, cont_sel, est, fv, cant, ref); st.success("✅ Ingreso exitoso")

    elif operacion in ["Picking (Preparación)", "Despacho Directo (Salida)"]:
        is_picking = operacion == "Picking (Preparación)"
        st.session_state.cli_tmp = st.text_input("Cliente:", value=st.session_state.get('cli_tmp', ""))
        if not is_picking: st.session_state.guia_tmp = st.text_input("Guía de Salida:", value=st.session_state.get('guia_tmp', ""))
        
        df_inv = pd.DataFrame(ws_inv.get_all_records())
        if not df_inv.empty:
            df_inv.columns = df_inv.columns.str.strip().str.lower()
            df_inv['stock_actual'] = pd.to_numeric(df_inv['stock_actual'], errors='coerce') or 0
            df_inv = df_inv[df_inv['stock_actual'] > 0]
            sku_p = st.selectbox("Seleccione Producto:", ["Seleccione..."] + sorted(list(df_inv['sku'].astype(str).unique())))
            if sku_p != "Seleccione...":
                stock_op = df_inv[df_inv['sku'].astype(str) == sku_p]
                with st.form("f_salida"):
                    op_txt = [f"CONT: {r['contenedor']} | EST: {r['estado']} | FV: {r['fecha_vencimiento']}" for _, r in stock_op.iterrows()]
                    sel_o = st.selectbox("Origen:", op_txt); f_s = stock_op.iloc[op_txt.index(sel_o)]
                    cant_s = st.number_input("Cantidad:", min_value=1, max_value=int(f_s['stock_actual']), step=1)
                    if st.form_submit_button("Confirmar Operación"):
                        if is_picking:
                            ws_pick.append_row([str(datetime.now().timestamp()), sku_p, str(f_s['contenedor']), f_s['estado'], str(f_s['fecha_vencimiento']), cant_s, st.session_state.cli_tmp, str(datetime.now().date())])
                            actualizar_inventario(sku_p, f_s['contenedor'], f_s['estado'], f_s['fecha_vencimiento'], -cant_s)
                            registrar_movimiento("PICKING_REGISTRO", sku_p, f_s['contenedor'], f_s['estado'], f_s['fecha_vencimiento'], cant_s, "RESERVA", st.session_state.cli_tmp)
                            st.success("✅ Reservado"); st.rerun()
                        elif st.session_state.guia_tmp:
                            actualizar_inventario(sku_p, f_s['contenedor'], f_s['estado'], f_s['fecha_vencimiento'], -cant_s)
                            registrar_movimiento("SALIDA_DESPACHO", sku_p, f_s['contenedor'], f_s['estado'], f_s['fecha_vencimiento'], cant_s, st.session_state.guia_tmp, st.session_state.cli_tmp)
                            st.success("✅ Despachado"); st.rerun()

# --- 2. REPORTE DE STOCK (CON FILTROS) ---
elif menu == "📦 Reporte de Stock":
    st.header("Inventario y Control de Picking")
    t_inv, t_pick = st.tabs(["📊 Stock en Bodega", "⛏️ Gestión de Picking Pendiente"])
    
    with t_inv:
        df_inv = pd.DataFrame(ws_inv.get_all_records())
        if not df_inv.empty:
            df_inv.columns = df_inv.columns.str.strip().str.lower()
            df_inv['stock_actual'] = pd.to_numeric(df_inv['stock_actual'], errors='coerce').fillna(0)
            
            c1, c2 = st.columns(2)
            f_cont = c1.multiselect("Filtrar Contenedor:", df_inv['contenedor'].unique())
            f_sku = c2.text_input("Buscar SKU:")
            
            df_res = df_inv[df_inv['stock_actual'] > 0]
            if f_cont: df_res = df_res[df_res['contenedor'].astype(str).isin(map(str, f_cont))]
            if f_sku: df_res = df_res[df_res['sku'].astype(str).str.contains(f_sku, case=False)]
            
            st.dataframe(df_res, use_container_width=True)

    with t_pick:
        df_p = pd.DataFrame(ws_pick.get_all_records())
        if not df_p.empty:
            df_p.columns = df_p.columns.str.strip().str.lower()
            for i, r in df_p.iterrows():
                with st.expander(f"📦 {r['sku']} | {r['cliente']} | {r['cantidad']} und"):
                    guia_p = st.text_input("Guía para Despacho:", key=f"pg_{i}")
                    if st.button("🚀 Confirmar Despacho", key=f"pok_{i}"):
                        if guia_p:
                            registrar_movimiento("SALIDA_DESPACHO", r['sku'], r['contenedor'], r['estado'], r['fecha_vencimiento'], r['cantidad'], guia_p, r['cliente'])
                            ws_pick.delete_rows(i + 2); st.rerun()

# --- 3. ESTADO PACKING LIST (CON FILTRO) ---
elif menu == "📋 Estado Packing List":
    st.header("Control de Recepción vs PL")
    df_pl = pd.DataFrame(ws_pl.get_all_records()); df_mov = pd.DataFrame(ws_mov.get_all_records())
    if not df_pl.empty:
        df_pl.columns = df_pl.columns.str.strip().str.lower(); df_mov.columns = df_mov.columns.str.strip().str.lower()
        
        f_cont_pl = st.selectbox("Filtrar por Contenedor:", ["Todos"] + list(df_pl['contenedor'].unique().astype(str)))
        
        df_real = df_mov[df_mov['tipo_mov'] == "INGRESO_PL"].groupby(['sku', 'contenedor'])['cantidad'].apply(lambda x: pd.to_numeric(x).sum()).reset_index()
        df_real.columns = ['sku', 'contenedor', 'qty_in']
        
        res = pd.merge(df_pl, df_real, on=['sku', 'contenedor'], how='left').fillna(0)
        res['dif'] = res['qty_in'] - pd.to_numeric(res['cantidad_pl'])
        
        if f_cont_pl != "Todos": res = res[res['contenedor'].astype(str) == f_cont_pl]
        st.dataframe(res.style.map(lambda x: 'color: red' if isinstance(x, (int, float)) and x < 0 else None, subset=['dif']), use_container_width=True)

# --- 4. HISTORIAL (CON FILTRO FECHA) ---
elif menu == "📊 Historial Movimientos":
    st.header("Trazabilidad Histórica")
    df_mov = pd.DataFrame(ws_mov.get_all_records())
    if not df_mov.empty:
        df_mov.columns = df_mov.columns.str.strip().str.lower()
        df_mov['fecha_hora'] = pd.to_datetime(df_mov['fecha_hora'], errors='coerce')
        
        c1, c2 = st.columns(2)
        f_inicio = c1.date_input("Desde:", datetime.now() - timedelta(days=30))
        f_fin = c2.date_input("Hasta:", datetime.now())
        
        df_f = df_mov[(df_mov['fecha_hora'].dt.date >= f_inicio) & (df_mov['fecha_hora'].dt.date <= f_fin)]
        st.dataframe(df_f.sort_values(by='fecha_hora', ascending=False), use_container_width=True)

# --- 5. INSIGHTS INTELIGENTES (NUEVO) ---
elif menu == "💡 Insights de Inventario":
    st.header("Análisis Inteligente de Stock")
    df_inv = pd.DataFrame(ws_inv.get_all_records())
    if not df_inv.empty:
        df_inv.columns = df_inv.columns.str.strip().str.lower()
        df_inv['fecha_vencimiento'] = pd.to_datetime(df_inv['fecha_vencimiento'], errors='coerce')
        df_inv['stock_actual'] = pd.to_numeric(df_inv['stock_actual'], errors='coerce').fillna(0)
        df_inv = df_inv[df_inv['stock_actual'] > 0]

        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🚨 Próximos a Vencer (30-60 días)")
            hoy = datetime.now()
            proximos = df_inv[df_inv['fecha_vencimiento'] <= (hoy + timedelta(days=60))].sort_values('fecha_vencimiento')
            st.dataframe(proximos[['sku', 'contenedor', 'fecha_vencimiento', 'stock_actual']], use_container_width=True)
            
        with col2:
            st.subheader("🐢 Productos con Mayor Antigüedad")
            # Obtenemos la primera fecha de ingreso desde el historial para cada SKU/Contenedor
            df_mov = pd.DataFrame(ws_mov.get_all_records())
            df_mov.columns = df_mov.columns.str.strip().str.lower()
            df_mov['fecha_hora'] = pd.to_datetime(df_mov['fecha_hora'], errors='coerce')
            ingresos = df_mov[df_mov['tipo_mov'] == "INGRESO_PL"].groupby(['sku', 'contenedor'])['fecha_hora'].min().reset_index()
            ingresos.columns = ['sku', 'contenedor', 'fecha_primer_ingreso']
            
            antiguedad = pd.merge(df_inv, ingresos, on=['sku', 'contenedor'], how='left')
            st.dataframe(antiguedad.sort_values('fecha_primer_ingreso')[['sku', 'contenedor', 'fecha_primer_ingreso', 'stock_actual']], use_container_width=True)
