import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

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
    else: ws_inv.update_cell(match.index[0]+2, 5, int(match.iloc[0]['stock_actual']) + cant)

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("MENÚ PRINCIPAL", ["🚀 Operaciones de Bodega", "📦 Reporte de Stock", "📋 Estado Packing List", "📊 Historial Movimientos"])

# --- SECCIÓN ÚNICA DE REGISTROS ---
if menu == "🚀 Operaciones de Bodega":
    operacion = st.selectbox("Seleccione la operación a realizar:", 
                            ["Ingreso Físico", "Picking (Preparación)", "Despacho Directo (Salida)", "Reclasificación (Cambio Estado)"])
    st.divider()

    # --- 1. INGRESO FÍSICO ---
    if operacion == "Ingreso Físico":
        st.subheader("📥 Registro de Ingreso")
        df_pl_datos = pd.DataFrame(ws_pl.get_all_records())
        if not df_pl_datos.empty:
            df_pl_datos.columns = df_pl_datos.columns.str.strip().str.lower()
            cont_sel = st.selectbox("Contenedor:", sorted(list(df_pl_datos['contenedor'].astype(str).unique())))
            skus_f = df_pl_datos[df_pl_datos['contenedor'].astype(str) == cont_sel]
            sku_sel = st.selectbox("SKU:", sorted(list(skus_f['sku'].astype(str).unique())))
            with st.form("f_ingreso"):
                c1, c2 = st.columns(2)
                est = c1.selectbox("Estado", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
                fv = c1.date_input("Vencimiento")
                cant = c2.number_input("Cantidad:", min_value=0, step=1)
                ref = c2.text_input("Referencia/Guía")
                if st.form_submit_button("Confirmar Ingreso"):
                    if cant > 0:
                        actualizar_inventario(sku_sel, cont_sel, est, fv, cant)
                        registrar_movimiento("INGRESO_PL", sku_sel, cont_sel, est, fv, cant, ref)
                        st.success("✅ Ingreso exitoso")
                    else: st.error("Cantidad debe ser > 0")

    # --- 2. PICKING / 3. DESPACHO ---
    elif operacion in ["Picking (Preparación)", "Despacho Directo (Salida)"]:
        is_picking = operacion == "Picking (Preparación)"
        st.subheader(f"{'⛏️' if is_picking else '📤'} {operacion}")
        
        # Cabecera persistente
        if 'cli_tmp' not in st.session_state: st.session_state.cli_tmp = ""
        if 'guia_tmp' not in st.session_state: st.session_state.guia_tmp = ""
        
        col_c1, col_c2 = st.columns(2)
        st.session_state.cli_tmp = col_c1.text_input("Cliente:", value=st.session_state.cli_tmp)
        if not is_picking:
            st.session_state.guia_tmp = col_c2.text_input("Guía de Salida:", value=st.session_state.guia_tmp)
        
        df_inv = pd.DataFrame(ws_inv.get_all_records())
        if not df_inv.empty:
            df_inv.columns = df_inv.columns.str.strip().str.lower()
            df_inv = df_inv[df_inv['stock_actual'] > 0]
            sku_p = st.selectbox("Seleccione Producto:", ["Seleccione..."] + sorted(list(df_inv['sku'].astype(str).unique())))
            
            if sku_p != "Seleccione...":
                stock_op = df_inv[df_inv['sku'].astype(str) == sku_p]
                st.write("Saldos Disponibles:")
                st.dataframe(stock_op, use_container_width=True)
                
                with st.form("f_salida"):
                    op_txt = [f"CONT: {r['contenedor']} | EST: {r['estado']} | FV: {r['fecha_vencimiento']}" for _, r in stock_op.iterrows()]
                    sel_o = st.selectbox("Origen de Stock:", op_txt)
                    f_s = stock_op.iloc[op_txt.index(sel_o)]
                    cant_s = st.number_input("Cantidad:", min_value=1, max_value=int(f_s['stock_actual']), step=1)
                    
                    if st.form_submit_button("Confirmar Operación"):
                        if st.session_state.cli_tmp:
                            if is_picking:
                                ws_pick.append_row([str(datetime.now().timestamp()), sku_p, str(f_s['contenedor']), f_s['estado'], str(f_s['fecha_vencimiento']), cant_s, st.session_state.cli_tmp, str(datetime.now().date())])
                                actualizar_inventario(sku_p, f_s['contenedor'], f_s['estado'], f_s['fecha_vencimiento'], -cant_s)
                                registrar_movimiento("PICKING_REGISTRO", sku_p, f_s['contenedor'], f_s['estado'], f_s['fecha_vencimiento'], cant_s, "RESERVA", st.session_state.cli_tmp)
                                st.success("✅ Reservado en Picking")
                            else:
                                if st.session_state.guia_tmp:
                                    actualizar_inventario(sku_p, f_s['contenedor'], f_s['estado'], f_s['fecha_vencimiento'], -cant_s)
                                    registrar_movimiento("SALIDA_DESPACHO", sku_p, f_s['contenedor'], f_s['estado'], f_s['fecha_vencimiento'], cant_s, st.session_state.guia_tmp, st.session_state.cli_tmp)
                                    st.success("✅ Despacho Directo Exitoso")
                                else: st.error("Falta Guía")
                        else: st.error("Falta Cliente")

    # --- 4. RECLASIFICACIÓN ---
    elif operacion == "Reclasificación (Cambio Estado)":
        st.subheader("🔄 Reclasificación de Stock")
        with st.form("f_recla"):
            c1, c2 = st.columns(2)
            sku = c1.text_input("SKU")
            cont = c1.text_input("Contenedor")
            fv = c2.date_input("Fecha Vencimiento")
            cant = c2.number_input("Cantidad", min_value=1)
            e_o = st.selectbox("Desde Estado:", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
            e_d = st.selectbox("Hacia Estado:", ["Merma", "Bandejas", "Disponible", "Distribuidores"])
            if st.form_submit_button("Ejecutar Cambio"):
                actualizar_inventario(sku, cont, e_o, fv, -cant)
                actualizar_inventario(sku, cont, e_d, fv, cant)
                registrar_movimiento("RECLASIFICACION", sku, cont, e_d, fv, cant, f"De {e_o}")
                st.success("🔄 Estado actualizado")

# --- CONTROL DE PICKING (DENTRO DE REPORTE O INDEPENDIENTE) ---
if menu == "📦 Reporte de Stock":
    st.header("Inventario y Control de Picking")
    t_inv, t_pick = st.tabs(["📊 Stock en Bodega", "⛏️ Gestión de Picking Pendiente"])
    
    with t_inv:
        df_inv = pd.DataFrame(ws_inv.get_all_records())
        if not df_inv.empty:
            df_inv.columns = df_inv.columns.str.strip().str.lower()
            st.dataframe(df_inv[df_inv['stock_actual'] > 0], use_container_width=True)
    
    with t_pick:
        df_p = pd.DataFrame(ws_pick.get_all_records())
        if not df_p.empty:
            df_p.columns = df_p.columns.str.strip().str.lower()
            for i, r in df_p.iterrows():
                with st.expander(f"📦 {r['sku']} | {r['cliente']} | {r['cantidad']} und"):
                    c1, c2 = st.columns(2)
                    n_cant = c1.number_input("Modificar Cantidad:", value=int(r['cantidad']), key=f"p_q_{i}")
                    guia_p = c2.text_input("Guía para Despacho:", key=f"p_g_{i}")
                    b1, b2, b3 = st.columns(3)
                    if b1.button("🗑️ Devolver", key=f"p_del_{i}"):
                        actualizar_inventario(r['sku'], r['contenedor'], r['estado'], r['fecha_vencimiento'], r['cantidad'])
                        registrar_movimiento("DEVOLUCION_PICKING", r['sku'], r['contenedor'], r['estado'], r['fecha_vencimiento'], r['cantidad'], "RETORNO", r['cliente'])
                        ws_pick.delete_rows(i + 2); st.rerun()
                    if b2.button("💾 Actualizar", key=f"p_up_{i}"):
                        diff = r['cantidad'] - n_cant
                        actualizar_inventario(r['sku'], r['contenedor'], r['estado'], r['fecha_vencimiento'], diff)
                        ws_pick.update_cell(i + 2, 6, n_cant); st.rerun()
                    if b3.button("🚀 Despachar", key=f"p_ok_{i}"):
                        if guia_p:
                            registrar_movimiento("SALIDA_DESPACHO", r['sku'], r['contenedor'], r['estado'], r['fecha_vencimiento'], r['cantidad'], guia_p, r['cliente'])
                            ws_pick.delete_rows(i + 2); st.rerun()
                        else: st.error("Falta Guía")

# --- MÓDULOS DE REPORTE (MANTENIDOS) ---
elif menu == "📋 Estado Packing List":
    st.header("Control de Recepción")
    df_pl = pd.DataFrame(ws_pl.get_all_records()); df_mov = pd.DataFrame(ws_mov.get_all_records())
    if not df_pl.empty:
        df_pl.columns = df_pl.columns.str.strip().str.lower(); df_mov.columns = df_mov.columns.str.strip().str.lower()
        df_real = df_mov[df_mov['tipo_mov'] == "INGRESO_PL"].groupby(['sku', 'contenedor'])['cantidad'].sum().reset_index()
        df_real.columns = ['sku', 'contenedor', 'qty_in']
        res = pd.merge(df_pl, df_real, on=['sku', 'contenedor'], how='left').fillna(0)
        res['dif'] = res['qty_in'] - res['cantidad_pl']
        st.dataframe(res.style.map(lambda x: 'color: red' if isinstance(x, (int, float)) and x < 0 else None, subset=['dif']), use_container_width=True)

elif menu == "📊 Historial Movimientos":
    st.header("Trazabilidad Total")
    df_mov = pd.DataFrame(ws_mov.get_all_records())
    if not df_mov.empty:
        df_mov.columns = df_mov.columns.str.strip().str.lower()
        t_sel = st.multiselect("Tipo Movimiento:", df_mov['tipo_mov'].unique(), default=list(df_mov['tipo_mov'].unique()))
        df_f = df_mov[df_mov['tipo_mov'].isin(t_sel)]
        st.dataframe(df_f.sort_values(by=df_f.columns[0], ascending=False), use_container_width=True)
