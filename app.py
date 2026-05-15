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

# --- FUNCIONES DE SOPORTE ---
def formatear_fecha_lectura(df, columna, solo_fecha=False):
    if df.empty or columna not in df.columns: return df
    df[columna] = pd.to_datetime(df[columna], errors='coerce', dayfirst=True)
    fmt = '%d/%m/%Y' if solo_fecha else '%d/%m/%Y %H:%M:%S'
    df[f'{columna}_fmt'] = df[columna].dt.strftime(fmt).fillna("Formato Inválido")
    return df

def registrar_movimiento(tipo, sku, cont, est, fv, cant, ref, cliente="N/A"):
    fecha_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    ws_mov.append_row([fecha_str, tipo, str(sku).strip(), str(cont).strip(), est, cant, ref, cliente, str(fv)])

def actualizar_inventario(sku, cont, est, fv, cant):
    data = ws_inv.get_all_records()
    df_inv = pd.DataFrame(data)
    if not df_inv.empty: df_inv.columns = df_inv.columns.str.strip().str.lower()
    sku_s, cont_s, fv_s = str(sku).strip(), str(cont).strip(), str(fv)
    match = df_inv[(df_inv['sku'].astype(str)==sku_s) & (df_inv['contenedor'].astype(str)==cont_s) & (df_inv['estado']==est) & (df_inv['fecha_vencimiento'].astype(str)==fv_s)] if not df_inv.empty else pd.DataFrame()
    if match.empty:
        if cant > 0: ws_inv.append_row([sku_s, cont_s, est, fv_s, cant])
    else:
        idx = match.index[0] + 2
        val_actual = pd.to_numeric(match.iloc[0]['stock_actual'], errors='coerce') or 0
        ws_inv.update_cell(idx, 5, int(val_actual + cant))

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("MENÚ", ["🚀 Operaciones de Bodega", "📦 Reporte de Stock", "📊 Historial Movimientos", "📋 Estado Packing List", "💡 Insights"])

# --- 1. OPERACIONES (MANTENIDAS IGUAL) ---
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
            with st.form("f_ingreso"):
                c1, c2 = st.columns(2)
                est = c1.selectbox("Estado", ["Disponible", "Distribuidores", "Merma", "Bandejas"])
                fv = c1.date_input("Fecha Vencimiento")
                cant = c2.number_input("Cantidad Recibida:", min_value=0, step=1)
                ref = c2.text_input("Referencia / Guía")
                if st.form_submit_button("Guardar Ingreso"):
                    fv_str = fv.strftime('%d/%m/%Y')
                    actualizar_inventario(sku_sel, cont_sel, est, fv_str, cant)
                    registrar_movimiento("INGRESO_PL", sku_sel, cont_sel, est, fv_str, cant, ref)
                    st.success(f"✅ Ingreso Registrado: {fv_str}")

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
                    sel = st.selectbox("Lote (Origen):", [f"{r['contenedor']} | {r['estado']} | {r['fecha_vencimiento']}" for _, r in opciones.iterrows()])
                    cant_s = st.number_input("Cantidad:", min_value=1, step=1)
                    if st.form_submit_button("Confirmar Movimiento"):
                        idx = [f"{r['contenedor']} | {r['estado']} | {r['fecha_vencimiento']}" for _, r in opciones.iterrows()].index(sel)
                        fila = opciones.iloc[idx]
                        if tipo == "PICKING":
                            ws_pick.append_row([str(datetime.now().timestamp()), sku_p, str(fila['contenedor']), fila['estado'], str(fila['fecha_vencimiento']), cant_s, cliente, datetime.now().strftime('%d/%m/%Y')])
                        actualizar_inventario(sku_p, fila['contenedor'], fila['estado'], fila['fecha_vencimiento'], -cant_s)
                        registrar_movimiento(f"SALIDA_{tipo}", sku_p, fila['contenedor'], fila['estado'], fila['fecha_vencimiento'], cant_s, guia, cliente)
                        st.success("✅ Operación Exitosa"); st.rerun()

# --- 2. REPORTE DE STOCK ---
elif menu == "📦 Reporte de Stock":
    st.header("Inventario Real")
    df_i = pd.DataFrame(ws_inv.get_all_records())
    if not df_i.empty:
        df_i.columns = df_i.columns.str.strip().str.lower()
        df_i = formatear_fecha_lectura(df_i, 'fecha_vencimiento', solo_fecha=True)
        with st.container(border=True):
            c1, c2 = st.columns(2)
            f_cont = c1.multiselect("Contenedor:", sorted(df_i['contenedor'].unique().astype(str)))
            f_sku = c2.text_input("SKU:")
            if st.button("🔍 Buscar en Stock"):
                res = df_i[pd.to_numeric(df_i['stock_actual'], errors='coerce') > 0].copy()
                if f_cont: res = res[res['contenedor'].astype(str).isin(f_cont)]
                if f_sku: res = res[res['sku'].astype(str).str.contains(f_sku, case=False)]
                st.dataframe(res[['sku', 'contenedor', 'estado', 'fecha_vencimiento_fmt', 'stock_actual']].rename(columns={'fecha_vencimiento_fmt': 'vencimiento'}), use_container_width=True)

# --- 3. HISTORIAL ---
elif menu == "📊 Historial Movimientos":
    st.header("Trazabilidad")
    df_m = pd.DataFrame(ws_mov.get_all_records())
    if not df_m.empty:
        df_m.columns = df_m.columns.str.strip().str.lower()
        df_m = formatear_fecha_lectura(df_m, 'fecha_hora')
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            f_ini, f_fin = c1.date_input("Desde:", datetime.now() - timedelta(days=30)), c2.date_input("Hasta:", datetime.now())
            f_c = c3.multiselect("Contenedor:", sorted(df_m['contenedor'].unique().astype(str)))
            f_s = st.text_input("SKU:")
            if st.button("🔍 Filtrar Historial"):
                df_m['dt'] = pd.to_datetime(df_m['fecha_hora'], errors='coerce', dayfirst=True)
                mask = (df_m['dt'].dt.date >= f_ini) & (df_m['dt'].dt.date <= f_fin)
                res = df_m[mask | df_m['dt'].isna()].copy()
                if f_c: res = res[res['contenedor'].astype(str).isin(f_c)]
                if f_s: res = res[res['sku'].astype(str).str.contains(f_s, case=False)]
                st.dataframe(res[['fecha_hora_fmt', 'tipo_mov', 'sku', 'contenedor', 'cantidad', 'referencia']].rename(columns={'fecha_hora_fmt': 'fecha'}), use_container_width=True)

# --- 4. ESTADO PACKING LIST (CORREGIDO KEYERROR) ---
elif menu == "📋 Estado Packing List":
    st.header("Cruce Packing vs Real")
    df_pl = pd.DataFrame(ws_pl.get_all_records())
    df_mov = pd.DataFrame(ws_mov.get_all_records())
    if not df_pl.empty:
        df_pl.columns = df_pl.columns.str.strip().str.lower()
        df_mov.columns = df_mov.columns.str.strip().str.lower()
        with st.container(border=True):
            cont_f = st.selectbox("Contenedor:", ["Todos"] + sorted(df_pl['contenedor'].unique().astype(str)))
            if st.button("🔍 Generar Reporte"):
                # 1. Obtener cantidad real del historial
                real = df_mov[df_mov['tipo_mov']=="INGRESO_PL"].copy()
                real['cantidad'] = pd.to_numeric(real['cantidad'], errors='coerce').fillna(0)
                sum_r = real.groupby(['sku', 'contenedor'])['cantidad'].sum().reset_index()
                sum_r.columns = ['sku', 'contenedor', 'cantidad_real']
                
                # 2. Unir con Packing List
                res = pd.merge(df_pl, sum_r, on=['sku', 'contenedor'], how='left').fillna(0)
                
                # 3. Identificar columna de cantidad en Packing List (por si cambió de nombre)
                col_pl = 'cantidad' if 'cantidad' in res.columns else 'cantidad_pl'
                
                # 4. Asegurar que ambas columnas sean numéricas para evitar errores
                res['cantidad_real'] = pd.to_numeric(res['cantidad_real'], errors='coerce').fillna(0)
                res[col_pl] = pd.to_numeric(res[col_pl], errors='coerce').fillna(0)
                
                # 5. Calcular diferencia
                res['diferencia'] = res['cantidad_real'] - res[col_pl]
                
                if cont_f != "Todos": res = res[res['contenedor'].astype(str) == cont_f]
                st.dataframe(res, use_container_width=True)

# --- 5. INSIGHTS ---
elif menu == "💡 Insights":
    st.header("Análisis de Stock Inteligente")
    df_i = pd.DataFrame(ws_inv.get_all_records())
    df_m = pd.DataFrame(ws_mov.get_all_records())
    if not df_i.empty:
        df_i.columns = df_i.columns.str.strip().str.lower()
        df_i = formatear_fecha_lectura(df_i, 'fecha_vencimiento', solo_fecha=True)
        df_i['dt'] = pd.to_datetime(df_i['fecha_vencimiento'], errors='coerce', dayfirst=True)
        df_i['stock_actual'] = pd.to_numeric(df_i['stock_actual'], errors='coerce').fillna(0)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🚨 Vencimientos Próximos")
            prox = df_i[(df_i['dt'] <= (datetime.now() + timedelta(days=60))) & (df_i['stock_actual'] > 0)].copy()
            if not prox.empty:
                prox = prox.sort_values('dt')
                st.dataframe(prox[['sku', 'contenedor', 'fecha_vencimiento_fmt', 'stock_actual']].rename(columns={'fecha_vencimiento_fmt': 'vencimiento'}), use_container_width=True)
        with c2:
            st.subheader("🐢 Antigüedad de Stock (FIFO)")
            if not df_m.empty:
                df_m.columns = df_m.columns.str.strip().str.lower()
                df_m['dt_mov'] = pd.to_datetime(df_m['fecha_hora'], errors='coerce', dayfirst=True)
                fifo = df_m[df_m['tipo_mov']=="INGRESO_PL"].groupby(['sku', 'contenedor'])['dt_mov'].min().reset_index()
                fifo.columns = ['sku', 'contenedor', 'fecha_entrada_dt']
                res_fifo = pd.merge(df_i[df_i['stock_actual'] > 0], fifo, on=['sku', 'contenedor'], how='left')
                res_fifo = res_fifo.sort_values('fecha_entrada_dt')
                res_fifo['entrada_fmt'] = res_fifo['fecha_entrada_dt'].dt.strftime('%d/%m/%Y').fillna("S/D")
                st.dataframe(res_fifo[['sku', 'contenedor', 'entrada_fmt', 'stock_actual']], use_container_width=True)
