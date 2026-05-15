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
    """Actualiza el stock sumando/restando. Si el SKU+Cont+Est+FV no existe, lo crea."""
    data = ws_inv.get_all_records()
    df_inv = pd.DataFrame(data)
    if not df_inv.empty:
        df_inv.columns = df_inv.columns.str.strip().str.lower()
    
    sku_s = str(sku).strip()
    cont_s = str(cont).strip()
    fv_s = str(fv)

    # Buscar coincidencia exacta
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
        # Si no existe y la cantidad es positiva, lo creamos
        if cant > 0:
            ws_inv.append_row([sku_s, cont_s, est, fv_s, cant])
    else:
        # Si existe, actualizamos la celda (Fila = index + 2 por encabezado)
        row_idx = match.index[0] + 2
        stock_actual = int(match.iloc[0]['stock_actual'])
        ws_inv.update_cell(row_idx, 5, stock_actual + cant)

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("MENÚ PRINCIPAL", [
    "🚀 Operaciones de Bodega", 
    "📦 Reporte de Stock", 
    "📋 Estado Packing List", 
    "📊 Historial Movimientos"
])

# --- MÓDULO: OPERACIONES ---
if menu == "🚀 Operaciones de Bodega":
    operacion = st.selectbox("Seleccione Operación:", 
                            ["Ingreso Físico", "Picking (Preparación)", "Despacho Directo", "Reclasificación"])
    st.divider()

    # 1. INGRESO
    if operacion == "Ingreso Físico":
        st.subheader("📥 Registro de Ingreso")
        df_pl = pd.DataFrame(ws_pl.get_all_records())
        if not df_pl.empty:
            df_pl.columns = df_pl.columns.str.strip().str.lower()
            cont_sel = st.selectbox("Contenedor:", sorted(df_pl['contenedor'].unique()))
            sku_sel = st.selectbox("SKU:", sorted(df_pl[df_pl['contenedor']==cont_sel]['sku'].unique()))
            with st.form("f_ing"):
                c1, c2 = st.columns(2)
                est = c1.selectbox("Estado", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
                fv = c1.date_input("Vencimiento")
                cant = c2.number_input("Cantidad Recibida:", min_value=0, step=1)
                ref = c2.text_input("Ref / Guía")
                if st.form_submit_button("Guardar"):
                    actualizar_inventario(sku_sel, cont_sel, est, fv, cant)
                    registrar_movimiento("INGRESO_PL", sku_sel, cont_sel, est, fv, cant, ref)
                    st.success("Guardado")

    # 2. PICKING / 3. DESPACHO
    elif operacion in ["Picking (Preparación)", "Despacho Directo"]:
        tipo = "PICKING" if operacion == "Picking (Preparación)" else "DESPACHO"
        st.subheader(f"📤 Registro de {tipo}")
        
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Cliente:")
        guia = c2.text_input("Nro Guía (Solo para Despacho Directo):")
        
        df_inv = pd.DataFrame(ws_inv.get_all_records())
        if not df_inv.empty:
            df_inv.columns = df_inv.columns.str.strip().str.lower()
            df_inv = df_inv[df_inv['stock_actual'] > 0]
            sku_p = st.selectbox("SKU:", ["Seleccione..."] + list(df_inv['sku'].unique()))
            
            if sku_p != "Seleccione...":
                opciones = df_inv[df_inv['sku']==sku_p]
                st.dataframe(opciones)
                with st.form("f_salida"):
                    sel = st.selectbox("Origen:", [f"{r['contenedor']} | {r['estado']} | {r['fecha_vencimiento']}" for _, r in opciones.iterrows()])
                    cant_s = st.number_input("Cantidad:", min_value=1, step=1)
                    if st.form_submit_button("Confirmar"):
                        idx = [f"{r['contenedor']} | {r['estado']} | {r['fecha_vencimiento']}" for _, r in opciones.iterrows()].index(sel)
                        fila = opciones.iloc[idx]
                        if tipo == "PICKING":
                            ws_pick.append_row([str(datetime.now().timestamp()), sku_p, fila['contenedor'], fila['estado'], fila['fecha_vencimiento'], cant_s, cliente, str(datetime.now().date())])
                            actualizar_inventario(sku_p, fila['contenedor'], fila['estado'], fila['fecha_vencimiento'], -cant_s)
                            registrar_movimiento("PICKING_REGISTRO", sku_p, fila['contenedor'], fila['estado'], fila['fecha_vencimiento'], cant_s, "RESERVA", cliente)
                        else:
                            actualizar_inventario(sku_p, fila['contenedor'], fila['estado'], fila['fecha_vencimiento'], -cant_s)
                            registrar_movimiento("SALIDA_DESPACHO", sku_p, fila['contenedor'], fila['estado'], fila['fecha_vencimiento'], cant_s, guia, cliente)
                        st.success("Operación Exitosa")

# --- MÓDULO: REPORTE ---
elif menu == "📦 Reporte de Stock":
    st.header("Stock Real en Bodega")
    df_inv = pd.DataFrame(ws_inv.get_all_records())
    if not df_inv.empty:
        df_inv.columns = df_inv.columns.str.strip().str.lower()
        st.dataframe(df_inv[df_inv['stock_actual'] > 0], use_container_width=True)
    
    st.divider()
    st.subheader("⛏️ Pickings Pendientes")
    df_p = pd.DataFrame(ws_pick.get_all_records())
    if not df_p.empty:
        df_p.columns = df_p.columns.str.strip().str.lower()
        for i, r in df_p.iterrows():
            with st.expander(f"{r['sku']} - {r['cliente']} ({r['cantidad']} und)"):
                g_p = st.text_input("Guía para Despachar:", key=f"g{i}")
                if st.button("Confirmar Salida Final", key=f"b{i}"):
                    registrar_movimiento("SALIDA_DESPACHO", r['sku'], r['contenedor'], r['estado'], r['fecha_vencimiento'], r['cantidad'], g_p, r['cliente'])
                    ws_pick.delete_rows(i + 2)
                    st.rerun()

# --- HISTORIAL ---
elif menu == "📊 Historial Movimientos":
    st.header("Historial")
    df_mov = pd.DataFrame(ws_mov.get_all_records())
    if not df_mov.empty:
        df_mov.columns = df_mov.columns.str.strip().str.lower()
        st.dataframe(df_mov.sort_values(by=df_mov.columns[0], ascending=False))
