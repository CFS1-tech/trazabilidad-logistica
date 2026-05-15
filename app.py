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

# --- FUNCIONES CORE ---
def registrar_movimiento(tipo, sku, cont, est, fv, cant, ref, cliente="N/A"):
    ws_mov.append_row([str(datetime.now()), tipo, str(sku).strip(), str(cont).strip(), est, cant, ref, cliente, str(fv)])

def actualizar_inventario(sku, cont, est, fv, cant):
    data = ws_inv.get_all_records()
    df_inv = pd.DataFrame(data)
    if not df_inv.empty:
        df_inv.columns = df_inv.columns.str.strip().str.lower()
    
    fv_str = str(fv)
    sku_str = str(sku).strip()
    cont_str = str(cont).strip()

    if not df_inv.empty:
        match = df_inv[
            (df_inv['sku'].astype(str) == sku_str) & 
            (df_inv['contenedor'].astype(str) == cont_str) & 
            (df_inv['estado'] == est) & 
            (df_inv['fecha_vencimiento'].astype(str) == fv_str)
        ]
    else:
        match = pd.DataFrame()

    if match.empty:
        ws_inv.append_row([sku_str, cont_str, est, fv_str, cant])
    else:
        row_idx = match.index[0] + 2
        new_val = int(match.iloc[0]['stock_actual']) + cant
        ws_inv.update_cell(row_idx, 5, new_val)

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("MENÚ PRINCIPAL", [
    "📥 Ingreso Físico", 
    "🔄 Reclasificación", 
    "📤 Despacho Multilínea", 
    "📋 Estado Packing List", 
    "📊 Reportes"
])

# --- MÓDULO 1: INGRESO FÍSICO (IGUAL AL ANTERIOR) ---
if menu == "📥 Ingreso Físico":
    st.header("Registro de Ingreso Real")
    df_pl_datos = pd.DataFrame(ws_pl.get_all_records())
    if not df_pl_datos.empty:
        df_pl_datos.columns = df_pl_datos.columns.str.strip().str.lower()
        lista_cont_ingreso = sorted(list(df_pl_datos['contenedor'].astype(str).unique()))
        cont_seleccionado = st.selectbox("1. Seleccione el Contenedor:", lista_cont_ingreso)
        skus_filtrados = df_pl_datos[df_pl_datos['contenedor'].astype(str) == cont_seleccionado]
        lista_skus_ingreso = sorted(list(skus_filtrados['sku'].astype(str).unique()))
        
        with st.form("form_ingreso_dinamico"):
            c1, c2 = st.columns(2)
            sku_final = c1.selectbox("2. Seleccione SKU (COD II):", lista_skus_ingreso)
            desc_aux = skus_filtrados[skus_filtrados['sku'].astype(str) == sku_final]['descripcion'].values[0]
            c1.info(f"Producto: {desc_aux}")
            est = c2.selectbox("Estado", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
            fv = c2.date_input("Fecha Vencimiento")
            cant = st.number_input("Cantidad Recibida", min_value=1)
            ref = st.text_input("Referencia / Guía")
            if st.form_submit_button("Confirmar Ingreso"):
                actualizar_inventario(sku_final, cont_seleccionado, est, fv, cant)
                registrar_movimiento("INGRESO_PL", sku_final, cont_seleccionado, est, fv, cant, ref)
                st.success("✅ Ingreso registrado.")

# --- MÓDULO 3: DESPACHO MULTILÍNEA (NUEVO) ---
elif menu == "📤 Despacho Multilínea":
    st.header("Gestión de Despacho por Cliente")
    
    # Inicializar sesión de despacho
    if 'despacho_cliente' not in st.session_state:
        st.session_state.despacho_cliente = ""
    if 'despacho_guia' not in st.session_state:
        st.session_state.despacho_guia = ""

    # Paso 1: Datos de Cabecera
    with st.expander("1. Datos de la Guía / Cliente", expanded=(not st.session_state.despacho_cliente)):
        c1, c2 = st.columns(2)
        cliente_input = c1.text_input("Cliente:", value=st.session_state.despacho_cliente)
        guia_input = c2.text_input("N° Guía de Salida:", value=st.session_state.despacho_guia)
        if st.button("Fijar Datos de Despacho"):
            st.session_state.despacho_cliente = cliente_input
            st.session_state.despacho_guia = guia_input
            st.rerun()

    if st.session_state.despacho_cliente and st.session_state.despacho_guia:
        st.success(f"📍 Despachando a: **{st.session_state.despacho_cliente}** | Guía: **{st.session_state.despacho_guia}**")
        if st.button("Finalizar / Cambiar Cliente"):
            st.session_state.despacho_cliente = ""
            st.session_state.despacho_guia = ""
            st.rerun()

        st.divider()

        # Paso 2: Selección de Producto e Inventario
        df_inv_actual = pd.DataFrame(ws_inv.get_all_records())
        if not df_inv_actual.empty:
            df_inv_actual.columns = df_inv_actual.columns.str.strip().str.lower()
            # Solo mostrar stock mayor a 0
            df_inv_actual = df_inv_actual[df_inv_actual['stock_actual'] > 0]
            
            sku_lista = sorted(list(df_inv_actual['sku'].astype(str).unique()))
            sku_para_despacho = st.selectbox("2. Seleccione SKU a despachar:", ["Seleccione..."] + sku_lista)

            if sku_para_despacho != "Seleccione...":
                # Filtrar inventario disponible para ese SKU
                stock_opciones = df_inv_actual[df_inv_actual['sku'].astype(str) == sku_para_despacho]
                st.write("Saldos Disponibles por Contenedor/Estado:")
                st.dataframe(stock_opciones[['contenedor', 'estado', 'fecha_vencimiento', 'stock_actual']], use_container_width=True)

                with st.form("form_linea_despacho", clear_on_submit=True):
                    st.write("Detalle de Salida:")
                    # Crear una etiqueta clara para el selector de origen
                    opciones_origen = [
                        f"CONT: {r['contenedor']} | EST: {r['estado']} | FV: {r['fecha_vencimiento']} (Stock: {r['stock_actual']})"
                        for _, r in stock_opciones.iterrows()
                    ]
                    origen_sel = st.selectbox("Seleccione el origen específico:", opciones_origen)
                    
                    # Extraer datos de la opción seleccionada
                    idx_sel = opciones_origen.index(origen_sel)
                    fila_sel = stock_opciones.iloc[idx_sel]
                    
                    cant_salida = st.number_input("Cantidad a despachar:", min_value=1, max_value=int(fila_sel['stock_actual']))
                    
                    if st.form_submit_button("Confirmar salida de este SKU"):
                        # Ejecutar actualización
                        actualizar_inventario(sku_para_despacho, fila_sel['contenedor'], fila_sel['estado'], fila_sel['fecha_vencimiento'], -cant_salida)
                        registrar_movimiento("SALIDA_DESPACHO", sku_para_despacho, fila_sel['contenedor'], fila_sel['estado'], fila_sel['fecha_vencimiento'], cant_salida, st.session_state.despacho_guia, st.session_state.despacho_cliente)
                        st.success(f"✅ Salida registrada: {cant_salida} und de {sku_para_despacho}")
                        st.info("Puede seleccionar otro SKU arriba para continuar con la misma guía.")
        else:
            st.warning("No hay stock disponible en inventario.")

# --- MÓDULOS RESTANTES (RECLASIFICACIÓN, REPORTES, ETC.) SE MANTIENEN IGUAL ---
elif menu == "🔄 Reclasificación":
    st.header("Cambio de Estado Interno")
    with st.form("recla"):
        sku = st.text_input("SKU")
        cont = st.text_input("Contenedor")
        fv = st.date_input("Fecha Vencimiento Original")
        c1, c2 = st.columns(2)
        est_orig = c1.selectbox("De:", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
        est_dest = c2.selectbox("A:", ["Merma", "Bandejas", "Disponible", "Distribuidores"])
        cant = st.number_input("Cantidad", min_value=1)
        if st.form_submit_button("Mover Stock"):
            actualizar_inventario(sku, cont, est_orig, fv, -cant)
            actualizar_inventario(sku, cont, est_dest, fv, cant)
            registrar_movimiento("RECLASIFICACION", sku, cont, est_dest, fv, cant, f"Desde {est_orig}")
            st.success("🔄 Stock actualizado.")

elif menu == "📋 Estado Packing List":
    st.header("Estado de Recepción por Contenedor")
    df_pl = pd.DataFrame(ws_pl.get_all_records())
    if not df_pl.empty: df_pl.columns = df_pl.columns.str.strip().str.lower()
    df_mov = pd.DataFrame(ws_mov.get_all_records())
    if not df_mov.empty: df_mov.columns = df_mov.columns.str.strip().str.lower()
    else: df_mov = pd.DataFrame(columns=['fecha_hora', 'tipo_mov', 'sku', 'contenedor', 'estado', 'cantidad', 'referencia', 'cliente', 'fecha_vencimiento'])
    
    if df_pl.empty: st.warning("Packing List vacío.")
    else:
        f_cont = st.selectbox("Seleccionar Contenedor:", ["Todos"] + sorted(list(df_pl['contenedor'].astype(str).unique())))
        df_real = df_mov[df_mov['tipo_mov'].isin(['INGRESO_PL', 'AUTO_INGRESO'])]
        df_real_sum = df_real.groupby(['sku', 'contenedor'])['cantidad'].sum().reset_index() if not df_real.empty else pd.DataFrame(columns=['sku', 'contenedor', 'qty_in'])
        df_real_sum.columns = ['sku', 'contenedor', 'qty_in']
        
        df_pl['sku'], df_pl['contenedor'] = df_pl['sku'].astype(str), df_pl['contenedor'].astype(str)
        df_real_sum['sku'], df_real_sum['contenedor'] = df_real_sum['sku'].astype(str), df_real_sum['contenedor'].astype(str)
        
        res = pd.merge(df_pl, df_real_sum, on=['sku', 'contenedor'], how='left').fillna(0)
        res['dif'] = res['qty_in'] - res['cantidad_pl']
        view = res[['sku', 'descripcion', 'contenedor', 'cantidad_pl', 'qty_in', 'dif', 'fecha_ingreso', 'estado']]
        view.columns = ['COD II', 'DESCRIPCIÓN', 'NRO CONT', 'QTY PL', 'QTY IN', 'DIF', 'FECH INC', 'ESTADO']
        if f_cont != "Todos": view = view[view['NRO CONT'] == f_cont]
        st.dataframe(view.style.map(lambda x: 'color: red' if isinstance(x, (int, float)) and x < 0 else None, subset=['DIF']), use_container_width=True)

elif menu == "📊 Reportes":
    st.header("Reporte de Movimientos")
    df_mov = pd.DataFrame(ws_mov.get_all_records())
    if not df_mov.empty:
        df_mov.columns = df_mov.columns.str.strip().str.lower()
        st.dataframe(df_mov.sort_values(by="fecha_hora", ascending=False), use_container_width=True)
