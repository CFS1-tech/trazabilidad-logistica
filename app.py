import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="WMS Trazabilidad Pro", layout="wide")

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

# Inicialización segura de hojas
gc = conectar_gsheet()
ws_pl = gc.worksheet("packing_list")
ws_inv = gc.worksheet("inventario")
ws_mov = gc.worksheet("movimientos")
ws_pick = gc.worksheet("picking")

# --- FUNCIONES CORE ---
def registrar_movimiento(tipo, sku, cont, est, fv, cant, ref, cliente="N/A", fecha_manual=None):
    fecha = str(fecha_manual) if fecha_manual else str(datetime.now())
    ws_mov.append_row([fecha, tipo, str(sku).strip(), str(cont).strip(), est, cant, ref, cliente, str(fv)])

def actualizar_inventario(sku, cont, est, fv, cant):
    data = ws_inv.get_all_records()
    df_inv = pd.DataFrame(data)
    if not df_inv.empty: df_inv.columns = df_inv.columns.str.strip().str.lower()
    
    sku_s, cont_s, fv_s = str(sku).strip(), str(cont).strip(), str(fv)
    
    if not df_inv.empty:
        match = df_inv[(df_inv['sku'].astype(str) == sku_s) & (df_inv['contenedor'].astype(str) == cont_s) & 
                       (df_inv['estado'] == est) & (df_inv['fecha_vencimiento'].astype(str) == fv_s)]
    else:
        match = pd.DataFrame()

    if match.empty:
        ws_inv.append_row([sku_s, cont_s, est, fv_s, cant])
    else:
        row_idx = match.index[0] + 2
        new_val = int(match.iloc[0]['stock_actual']) + cant
        ws_inv.update_cell(row_idx, 5, new_val)

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("MENÚ PRINCIPAL", [
    "📥 Ingreso Físico", 
    "🔄 Reclasificación", 
    "⛏️ Picking (Preparación)",
    "📦 Reporte de Stock",
    "📋 Estado Packing List",
    "📊 Historial Movimientos"
])

# --- MÓDULO 1: INGRESO FÍSICO ---
if menu == "📥 Ingreso Físico":
    st.header("Registro de Ingreso Real")
    df_pl_datos = pd.DataFrame(ws_pl.get_all_records())
    if not df_pl_datos.empty:
        df_pl_datos.columns = df_pl_datos.columns.str.strip().str.lower()
        lista_cont = sorted(list(df_pl_datos['contenedor'].astype(str).unique()))
        cont_sel = st.selectbox("1. Seleccione Contenedor:", lista_cont)
        
        skus_f = df_pl_datos[df_pl_datos['contenedor'].astype(str) == cont_sel]
        sku_sel = st.selectbox("2. Seleccione SKU:", sorted(list(skus_f['sku'].astype(str).unique())))
        
        with st.form("form_ingreso"):
            c1, c2 = st.columns(2)
            est = c1.selectbox("Estado", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
            fv = c1.date_input("Fecha Vencimiento")
            cant = c2.number_input("Cantidad Recibida:", min_value=0, step=1)
            ref = c2.text_input("Referencia / Guía")
            if st.form_submit_button("Confirmar Ingreso"):
                if cant > 0:
                    actualizar_inventario(sku_sel, cont_sel, est, fv, cant)
                    registrar_movimiento("INGRESO_PL", sku_sel, cont_sel, est, fv, cant, ref)
                    st.success("✅ Ingreso registrado con éxito.")
                else: st.error("La cantidad debe ser mayor a 0.")

# --- MÓDULO 2: PICKING ---
elif menu == "⛏️ Picking (Preparación)":
    st.header("Gestión de Picking y Despacho")
    t1, t2 = st.tabs(["Nueva Reserva (Picking)", "Control de Pendientes"])
    
    with t1:
        df_inv = pd.DataFrame(ws_inv.get_all_records())
        if not df_inv.empty:
            df_inv.columns = df_inv.columns.str.strip().str.lower()
            df_inv = df_inv[df_inv['stock_actual'] > 0]
            sku_p = st.selectbox("Producto a Picar:", ["Seleccione..."] + sorted(list(df_inv['sku'].astype(str).unique())))
            
            if sku_p != "Seleccione...":
                stock_op = df_inv[df_inv['sku'].astype(str) == sku_p]
                st.write("Saldos Disponibles:")
                st.dataframe(stock_op, use_container_width=True)
                
                with st.form("f_pick"):
                    op = [f"CONT: {r['contenedor']} | EST: {r['estado']} | FV: {r['fecha_vencimiento']}" for _, r in stock_op.iterrows()]
                    sel_o = st.selectbox("Origen de Stock:", op)
                    f_s = stock_op.iloc[op.index(sel_o)]
                    cant_p = st.number_input("Cantidad:", min_value=1, max_value=int(f_s['stock_actual']), step=1)
                    cli_p = st.text_input("Cliente:")
                    if st.form_submit_button("Separar Mercadería"):
                        ws_pick.append_row([str(datetime.now().timestamp()), sku_p, str(f_s['contenedor']), f_s['estado'], str(f_s['fecha_vencimiento']), cant_p, cli_p, str(datetime.now().date())])
                        actualizar_inventario(sku_p, f_s['contenedor'], f_s['estado'], f_s['fecha_vencimiento'], -cant_p)
                        registrar_movimiento("PICKING_REGISTRO", sku_p, f_s['contenedor'], f_s['estado'], f_s['fecha_vencimiento'], cant_p, "RESERVA", cli_p)
                        st.success("✅ Stock reservado.")
                        st.rerun()

    with t2:
        df_p = pd.DataFrame(ws_pick.get_all_records())
        if not df_p.empty:
            df_p.columns = df_p.columns.str.strip().str.lower()
            for i, r in df_p.iterrows():
                with st.expander(f"📦 {r['sku']} | {r['cliente']} | {r['cantidad']} und"):
                    c1, c2 = st.columns(2)
                    n_cant = c1.number_input("Editar Cantidad:", value=int(r['cantidad']), key=f"ec_{i}")
                    guia_d = c2.text_input("N° Guía para Despachar:", key=f"gd_{i}")
                    
                    b1, b2, b3 = st.columns(3)
                    if b1.button("🗑️ Devolver a Stock", key=f"dev_{i}"):
                        actualizar_inventario(r['sku'], r['contenedor'], r['estado'], r['fecha_vencimiento'], r['cantidad'])
                        registrar_movimiento("DEVOLUCION_PICKING", r['sku'], r['contenedor'], r['estado'], r['fecha_vencimiento'], r['cantidad'], "ELIMINADO", r['cliente'])
                        ws_pick.delete_rows(i + 2)
                        st.rerun()
                    if b2.button("💾 Guardar Cambios", key=f"up_{i}"):
                        diff = r['cantidad'] - n_cant
                        actualizar_inventario(r['sku'], r['contenedor'], r['estado'], r['fecha_vencimiento'], diff)
                        ws_pick.update_cell(i + 2, 6, n_cant)
                        st.rerun()
                    if b3.button("🚀 Confirmar Salida", key=f"ok_{i}"):
                        if guia_d:
                            registrar_movimiento("SALIDA_DESPACHO", r['sku'], r['contenedor'], r['estado'], r['fecha_vencimiento'], r['cantidad'], guia_d, r['cliente'])
                            ws_pick.delete_rows(i + 2)
                            st.rerun()
                        else: st.error("Ingrese Guía.")

# --- MÓDULO 3: REPORTE DE STOCK ---
elif menu == "📦 Reporte de Stock":
    st.header("Balance de Inventarios")
    df_inv = pd.DataFrame(ws_inv.get_all_records())
    if not df_inv.empty:
        df_inv.columns = df_inv.columns.str.strip().str.lower()
        st.subheader("Stock Físico (En Estantería)")
        st.dataframe(df_inv[df_inv['stock_actual'] > 0], use_container_width=True)
        
        df_p = pd.DataFrame(ws_pick.get_all_records())
        if not df_p.empty:
            st.subheader("⚠️ Stock en Picking (Comprometido)")
            st.dataframe(df_p, use_container_width=True)

# --- MÓDULO 4: ESTADO PACKING LIST ---
elif menu == "📋 Estado Packing List":
    st.header("Control Packing List vs Ingresos")
    df_pl = pd.DataFrame(ws_pl.get_all_records())
    df_mov = pd.DataFrame(ws_mov.get_all_records())
    if not df_pl.empty:
        df_pl.columns = df_pl.columns.str.strip().str.lower()
        df_mov.columns = df_mov.columns.str.strip().str.lower()
        
        f_c = st.selectbox("Filtrar Contenedor:", ["Todos"] + sorted(list(df_pl['contenedor'].astype(str).unique())))
        
        df_real = df_mov[df_mov['tipo_mov'] == "INGRESO_PL"].groupby(['sku', 'contenedor'])['cantidad'].sum().reset_index()
        df_real.columns = ['sku', 'contenedor', 'qty_in']
        
        df_pl['sku'], df_pl['contenedor'] = df_pl['sku'].astype(str), df_pl['contenedor'].astype(str)
        df_real['sku'], df_real['contenedor'] = df_real['sku'].astype(str), df_real['contenedor'].astype(str)
        
        res = pd.merge(df_pl, df_real, on=['sku', 'contenedor'], how='left').fillna(0)
        res['dif'] = res['qty_in'] - res['cantidad_pl']
        
        view = res[['sku', 'descripcion', 'contenedor', 'cantidad_pl', 'qty_in', 'dif', 'fecha_ingreso', 'estado']]
        view.columns = ['COD II', 'DESCRIPCIÓN', 'NRO CONT', 'QTY PL', 'QTY IN', 'DIF', 'FECH INC', 'ESTADO']
        if f_c != "Todos": view = view[view['NRO CONT'] == f_c]
        st.dataframe(view.style.map(lambda x: 'color: red' if isinstance(x, (int, float)) and x < 0 else None, subset=['DIF']), use_container_width=True)

# --- MÓDULO 5: HISTORIAL ---
elif menu == "📊 Historial Movimientos":
    st.header("Trazabilidad de Movimientos")
    df_mov = pd.DataFrame(ws_mov.get_all_records())
    if not df_mov.empty:
        df_mov.columns = df_mov.columns.str.strip().str.lower()
        c1, c2, c3 = st.columns(3)
        t_sel = c1.multiselect("Operación:", df_mov['tipo_mov'].unique(), default=list(df_mov['tipo_mov'].unique()))
        c_sel = c2.text_input("Contenedor:")
        s_sel = c3.text_input("SKU:")
        
        df_f = df_mov[df_mov['tipo_mov'].isin(t_sel)]
        if c_sel: df_f = df_f[df_f['contenedor'].astype(str).str.contains(c_sel)]
        if s_sel: df_f = df_f[df_f['sku'].astype(str).str.contains(s_sel)]
        
        st.dataframe(df_f.sort_values(by=df_f.columns[0], ascending=False), use_container_width=True)

# Módulo Reclasificación (Mantenido igual)
elif menu == "🔄 Reclasificación":
    st.header("Cambio de Estado")
    with st.form("f_recla"):
        sku = st.text_input("SKU")
        cont = st.text_input("Contenedor")
        fv = st.date_input("Vencimiento")
        e_o = st.selectbox("De:", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
        e_d = st.selectbox("A:", ["Merma", "Bandejas", "Disponible", "Distribuidores"])
        cant = st.number_input("Cantidad", min_value=1)
        if st.form_submit_button("Ejecutar"):
            actualizar_inventario(sku, cont, e_o, fv, -cant)
            actualizar_inventario(sku, cont, e_d, fv, cant)
            registrar_movimiento("RECLASIFICACION", sku, cont, e_d, fv, cant, f"De {e_o}")
            st.success("Actualizado.")
