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
    
    if match.empty: 
        if cant > 0: ws_inv.append_row([sku_s, cont_s, est, fv_s, cant])
    else: 
        idx = match.index[0] + 2
        val_actual = pd.to_numeric(match.iloc[0]['stock_actual'], errors='coerce') or 0
        ws_inv.update_cell(idx, 5, int(val_actual + cant))

def cargar_datos_limpios(ws):
    df = pd.DataFrame(ws.get_all_records())
    if not df.empty:
        df.columns = df.columns.str.strip().str.lower()
    return df

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("MENÚ PRINCIPAL", ["🚀 Operaciones", "📦 Reporte de Stock", "📊 Historial", "📋 Packing List", "💡 Insights"])

# --- 1. OPERACIONES (INGRESO, PICKING, DESPACHO) ---
if menu == "🚀 Operaciones":
    op = st.selectbox("Operación:", ["Ingreso Físico", "Picking", "Despacho Directo", "Reclasificación"])
    
    if op == "Ingreso Físico":
        st.subheader("📥 Ingreso")
        df_p = cargar_datos_limpios(ws_pl)
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
                    actualizar_inventario(s_sel, c_sel, est, fv, cant)
                    registrar_movimiento("INGRESO_PL", s_sel, c_sel, est, fv, cant, ref)
                    st.success("✅ Registrado")

    elif op in ["Picking", "Despacho Directo"]:
        st.subheader(f"📤 {op}")
        df_i = cargar_datos_limpios(ws_inv)
        df_i['stock_actual'] = pd.to_numeric(df_i['stock_actual'], errors='coerce').fillna(0)
        df_i = df_i[df_i['stock_actual'] > 0]
        
        cliente = st.text_input("Cliente:")
        guia = st.text_input("Guía:") if op == "Despacho Directo" else "RESERVA"
        
        sku_sel = st.selectbox("Producto:", ["Seleccione..."] + sorted(df_i['sku'].unique().astype(str)))
        if sku_sel != "Seleccione...":
            lotes = df_i[df_i['sku'].astype(str) == sku_sel]
            st.dataframe(lotes)
            with st.form("f_sal"):
                sel = st.selectbox("Lote:", [f"CONT: {r['contenedor']} | FV: {r['fecha_vencimiento']}" for _, r in lotes.iterrows()])
                cant_s = st.number_input("Cantidad:", min_value=1)
                if st.form_submit_button("Confirmar Salida"):
                    idx = [f"CONT: {r['contenedor']} | FV: {r['fecha_vencimiento']}" for _, r in lotes.iterrows()].index(sel)
                    l = lotes.iloc[idx]
                    if op == "Picking":
                        ws_pick.append_row([str(datetime.now().timestamp()), sku_sel, str(l['contenedor']), l['estado'], str(l['fecha_vencimiento']), cant_s, cliente, str(datetime.now().date())])
                    actualizar_inventario(sku_sel, l['contenedor'], l['estado'], l['fecha_vencimiento'], -cant_s)
                    registrar_movimiento(f"SALIDA_{op.upper()}", sku_sel, l['contenedor'], l['estado'], l['fecha_vencimiento'], cant_s, guia, cliente)
                    st.success("✅ Operación completada")

# --- 2. REPORTE DE STOCK (FILTROS + BUSCAR) ---
elif menu == "📦 Reporte de Stock":
    st.header("Inventario Real")
    df_i = cargar_datos_limpios(ws_inv)
    if not df_i.empty:
        with st.container(border=True):
            c1, c2 = st.columns(2)
            f_cont = c1.multiselect("Contenedor:", sorted(df_i['contenedor'].unique().astype(str)))
            f_sku = c2.text_input("SKU:")
            btn = st.button("🔍 Buscar en Stock")
        
        if btn or (not f_cont and not f_sku):
            res = df_i[pd.to_numeric(df_i['stock_actual'], errors='coerce') > 0]
            if f_cont: res = res[res['contenedor'].astype(str).isin(f_cont)]
            if f_sku: res = res[res['sku'].astype(str).str.contains(f_sku, case=False)]
            st.dataframe(res, use_container_width=True)

# --- 3. HISTORIAL (FILTROS FECHA/CONT/SKU + BUSCAR) ---
elif menu == "📊 Historial":
    st.header("Trazabilidad de Movimientos")
    df_m = cargar_datos_limpios(ws_mov)
    if not df_m.empty:
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            f_ini = c1.date_input("Desde:", datetime.now() - timedelta(days=60))
            f_fin = c2.date_input("Hasta:", datetime.now())
            f_c = c3.multiselect("Contenedor:", sorted(df_m['contenedor'].unique().astype(str)))
            f_s = st.text_input("SKU:")
            btn_h = st.button("🔍 Filtrar Historial")

        df_m['fecha_dt'] = pd.to_datetime(df_m['fecha_hora'], errors='coerce', dayfirst=True)
        
        if btn_h:
            # Filtro permisivo: muestra lo que coincide O lo que no se pudo procesar la fecha para no perder datos
            mask = (df_m['fecha_dt'].dt.date >= f_ini) & (df_m['fecha_dt'].dt.date <= f_fin)
            res = df_m[mask | df_m['fecha_dt'].isna()]
            if f_c: res = res[res['contenedor'].astype(str).isin(f_c)]
            if f_s: res = res[res['sku'].astype(str).str.contains(f_s, case=False)]
            st.dataframe(res.drop(columns=['fecha_dt']), use_container_width=True)
        else:
            st.dataframe(df_m.head(50), use_container_width=True)

# --- 4. PACKING LIST (FILTRO CONTENEDOR + BUSCAR) ---
elif menu == "📋 Packing List":
    st.header("Cruce de Recepción")
    df_p = cargar_datos_limpios(ws_pl)
    df_m = cargar_datos_limpios(ws_mov)
    
    with st.container(border=True):
        cont_f = st.selectbox("Contenedor:", ["Todos"] + sorted(df_p['contenedor'].unique().astype(str)))
        btn_pl = st.button("🔍 Cargar Reporte")
    
    if btn_pl:
        real = df_m[df_m['tipo_mov']=="INGRESO_PL"]
        real['cantidad'] = pd.to_numeric(real['cantidad'], errors='coerce').fillna(0)
        sum_r = real.groupby(['sku', 'contenedor'])['cantidad'].sum().reset_index()
        res = pd.merge(df_p, sum_r, on=['sku', 'contenedor'], how='left').fillna(0)
        if cont_f != "Todos": res = res[res['contenedor'].astype(str) == cont_f]
        st.dataframe(res, use_container_width=True)

# --- 5. INSIGHTS ---
elif menu == "💡 Insights":
    st.header("Análisis Inteligente")
    df_i = cargar_datos_limpios(ws_inv)
    df_m = cargar_datos_limpios(ws_mov)
    
    if not df_i.empty:
        c1, c2 = st.columns(2)
        df_i['fv_dt'] = pd.to_datetime(df_i['fecha_vencimiento'], errors='coerce', dayfirst=True)
        with c1:
            st.subheader("🚨 Vencimientos (60 días)")
            prox = df_i[df_i['fv_dt'] <= (datetime.now() + timedelta(days=60))]
            st.dataframe(prox[['sku', 'contenedor', 'fecha_vencimiento', 'stock_actual']].sort_values('fv_dt'))
        with c2:
            st.subheader("🐢 Antigüedad (FIFO)")
            df_m['fecha_dt'] = pd.to_datetime(df_m['fecha_hora'], errors='coerce', dayfirst=True)
            ent = df_m[df_m['tipo_mov']=="INGRESO_PL"].groupby(['sku', 'contenedor'])['fecha_dt'].min().reset_index()
            res = pd.merge(df_i[pd.to_numeric(df_i['stock_actual'])>0], ent, on=['sku', 'contenedor'], how='left')
            st.dataframe(res[['sku', 'contenedor', 'fecha_dt', 'stock_actual']].sort_values('fecha_dt'))
