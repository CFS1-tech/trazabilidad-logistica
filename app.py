# =========================================================
# SISTEMA LOGÍSTICO CARCASAS - VERSIÓN PRO OPTIMIZADA (RECUENTO=1)
# =========================================================

import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date, datetime
import os
import plotly.express as px
import plotly.graph_objects as go

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Sistema Logístico Carcasas", page_icon="📦", layout="wide")

# 2. LOGO Y ESTILOS
def cargar_estilos():
    st.markdown("""
        <style>
        .stDataFrame { font-size: 12px; }
        .apertura-card {
            background-color: #ffffff; padding: 20px; border-radius: 12px;
            border-left: 6px solid #6c5ce7; box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            margin-bottom: 15px; min-height: 140px;
        }
        .tienda-titulo { color: #2d3436; font-size: 1.1em; font-weight: 700; }
        .desc-tienda { color: #636e72; font-size: 0.85em; }
        .fecha-est { color: #d63031; font-weight: bold; font-size: 0.9em; margin-top: 10px; }
        .titulo-seccion {
            color: #2d3436; font-weight: bold; font-size: 1.5rem;
            margin-top: 25px; margin-bottom: 15px;
            border-bottom: 3px solid #2d9e6b; padding-bottom: 8px;
        }
        </style>
        """, unsafe_allow_html=True)

@st.cache_data
def mostrar_logo():
    if os.path.exists("CARCASAS.png"): st.image("CARCASAS.png", width=250)

cargar_estilos()
mostrar_logo()

# 3. CONEXIÓN Y CARGA
@st.cache_resource
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Error de conexión: {e}"); return None

client = conectar_google()

def abrir_archivo_dinamico(nombre_o_id):
    if len(nombre_o_id) > 25:
        return client.open_by_key(nombre_o_id)
    return client.open(nombre_o_id)

@st.cache_data(ttl=600)
def cargar_datos_completos():
    def fetch(nombre_o_id, hoja=None):
        try:
            sh = abrir_archivo_dinamico(nombre_o_id)
            wks = sh.worksheet(hoja) if hoja else sh.sheet1
            data = wks.get_all_records()
            if not data: return pd.DataFrame()
            df = pd.DataFrame(data)
            df.columns = [str(c).strip().upper() for c in df.columns]
            return df.astype(str)
        except: return pd.DataFrame()

    df_import_raw = fetch("Consolidado - Carcasas")

    if not df_import_raw.empty and "RECUENTO" in df_import_raw.columns:
        df_import_filtered = df_import_raw[df_import_raw["RECUENTO"].isin(["1", "1.0"])].copy()
    else:
        df_import_filtered = df_import_raw

    return df_import_filtered, fetch("RECEPCION_IMPORTACIONES", "MOVIMIENTOS"), fetch("TIENDAS CARCASAS")


# =========================================================
# MÓDULO: DASH DESPACHOS
# =========================================================

ORDEN_MESES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
               "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]

# Paleta verde → amarillo
COLORES_TIENDAS = [
    "#1a7a4a", "#2d9e6b", "#3dbb7e", "#5dcf96", "#85dcaa",
    "#b5e878", "#cef250", "#e8d44d", "#f0c040", "#f5a623",
    "#f7c948", "#a8d85a", "#72c472", "#4db88c", "#2eaa82",
    "#6bcf85", "#d4e84a", "#f2d740", "#e8b830", "#c8e06a",
]

GREEN_MAIN   = "#2d9e6b"
YELLOW_MAIN  = "#c8e06a"
GREEN_DARK   = "#1a7a4a"
GREEN_LIGHT  = "#85dcaa"


@st.cache_data(ttl=600)
def cargar_despachos():
    try:
        sh = client.open("CONSOLIDADO_DESPACHOS")
        wks = sh.sheet1
        all_values = wks.get_all_values()
        if not all_values or len(all_values) < 2:
            return pd.DataFrame()

        raw_headers = all_values[0]
        rows = all_values[1:]

        # Limpiar headers duplicados / vacíos
        headers = []
        seen = {}
        for i, h in enumerate(raw_headers):
            h_clean = str(h).strip()
            if h_clean == "":
                h_clean = f"_col_{i}"
            key = h_clean.lower()
            if key in seen:
                seen[key] += 1
                h_clean = f"{h_clean}_{seen[key]}"
            else:
                seen[key] = 0
            headers.append(h_clean)

        df = pd.DataFrame(rows, columns=headers)

        # Normalizar nombres de columna a minúsculas para acceso uniforme
        df.columns = [c.strip().lower() for c in df.columns]

        # Eliminar columnas fantasma
        df = df[[c for c in df.columns if not c.startswith("_col_")]]

        # Eliminar filas vacías
        df = df[df.apply(lambda r: r.astype(str).str.strip().ne("").any(), axis=1)].reset_index(drop=True)

        # Tipos
        df["unidades"] = pd.to_numeric(df.get("unidades", 0), errors="coerce").fillna(0).astype(int)

        # Normalizar columna mes → MAYÚSCULAS
        col_mes = next((c for c in df.columns if "mes" in c), None)
        if col_mes:
            df["mes"] = df[col_mes].astype(str).str.strip().str.upper()
        else:
            df["mes"] = "SIN MES"

        # Columna SKU sin punto
        col_sku = next((c for c in df.columns if "codigo_color_sin_punto" in c), None)
        if col_sku:
            df["sku"] = df[col_sku].astype(str).str.strip()
        else:
            df["sku"] = df.get("codigo_color", pd.Series([""] * len(df))).astype(str).str.strip()

        # Descripción producto
        col_desc = next((c for c in df.columns if "descripci" in c.lower()), None)
        df["descripcion"] = df[col_desc].astype(str).str.strip() if col_desc else ""

        # Tienda
        df["codigo_departamento"] = df.get("codigo_departamento", pd.Series([""] * len(df))).astype(str).str.strip()

        if "nombre_departamento" in df.columns:
            df["nombre_tienda"] = df["nombre_departamento"].astype(str).str.replace(
                r"^\d+\.-\s*", "", regex=True
            ).str.strip()
            df["nombre_departamento_full"] = df["nombre_departamento"].astype(str).str.strip()
        else:
            df["nombre_tienda"] = df["codigo_departamento"]
            df["nombre_departamento_full"] = df["codigo_departamento"]

        return df
    except Exception as e:
        st.error(f"❌ Error cargando CONSOLIDADO_DESPACHOS: {e}")
        return pd.DataFrame()


def _ordenar_meses(df, col="mes"):
    df = df.copy()
    df["_orden_mes"] = df[col].map(
        {m: i for i, m in enumerate(ORDEN_MESES)}
    ).fillna(99)
    return df.sort_values("_orden_mes").drop(columns=["_orden_mes"])


def _filtros_sidebar_despachos(df):
    """Devuelve df filtrado según los filtros en sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Filtros Despachos")

    # Filtro tienda
    tiendas_opts = sorted(df["nombre_tienda"].unique().tolist())
    sel_tiendas = st.sidebar.multiselect(
        "Tiendas",
        options=["TODAS"] + tiendas_opts,
        default=["TODAS"],
        key="sb_tiendas"
    )

    # Filtro mes
    meses_opts = sorted(df["mes"].unique(), key=lambda m: ORDEN_MESES.index(m) if m in ORDEN_MESES else 99)
    sel_meses = st.sidebar.multiselect(
        "Meses",
        options=["TODOS"] + meses_opts,
        default=["TODOS"],
        key="sb_meses"
    )

    df_f = df.copy()
    if "TODAS" not in sel_tiendas and sel_tiendas:
        df_f = df_f[df_f["nombre_tienda"].isin(sel_tiendas)]
    if "TODOS" not in sel_meses and sel_meses:
        df_f = df_f[df_f["mes"].isin(sel_meses)]

    return df_f


def _render_metricas_despachos(df):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 Total unidades", f"{int(df['unidades'].sum()):,}")
    c2.metric("🎨 SKUs únicos", f"{df['sku'].nunique():,}")
    c3.metric("🏪 Tiendas activas", df["codigo_departamento"].nunique())
    c4.metric("📅 Meses con data", df["mes"].nunique())


def _render_top10(df, n=10):
    st.markdown('<div class="titulo-seccion">🏆 Top 10 SKUs despachados</div>', unsafe_allow_html=True)

    col_f1, col_f2, col_f3 = st.columns(3)

    # Filtro tienda (dentro del gráfico, independiente del sidebar)
    with col_f1:
        tiendas_opts = sorted(df["nombre_tienda"].unique().tolist())
        sel_t = st.multiselect(
            "Tienda(s)",
            options=["TODAS"] + tiendas_opts,
            default=["TODAS"],
            key="top10_tienda"
        )
    with col_f2:
        meses_opts = sorted(df["mes"].unique(), key=lambda m: ORDEN_MESES.index(m) if m in ORDEN_MESES else 99)
        sel_m = st.multiselect(
            "Mes(es)",
            options=["TODOS"] + meses_opts,
            default=["TODOS"],
            key="top10_mes"
        )
    with col_f3:
        n_top = st.selectbox("Mostrar top", options=[5, 10, 15, 20], index=1, key="top10_n")

    df_f = df.copy()
    if "TODAS" not in sel_t and sel_t:
        df_f = df_f[df_f["nombre_tienda"].isin(sel_t)]
    if "TODOS" not in sel_m and sel_m:
        df_f = df_f[df_f["mes"].isin(sel_m)]

    # Agrupar con descripción (tomar la primera descripción asociada a cada SKU)
    desc_map = df_f.groupby("sku")["descripcion"].first().to_dict()

    top = (
        df_f.groupby("sku")["unidades"]
        .sum()
        .nlargest(n_top)
        .reset_index()
        .sort_values("unidades", ascending=True)
    )
    top["descripcion"] = top["sku"].map(desc_map).fillna("")

    # Escala de colores verde → amarillo según posición
    n_bars = len(top)
    colores_barra = [
        f"hsl({int(120 - (i / max(n_bars - 1, 1)) * 60)}, 70%, 45%)"
        for i in range(n_bars)
    ]

    fig = go.Figure(go.Bar(
        x=top["unidades"],
        y=top["sku"],
        orientation="h",
        marker=dict(color=colores_barra),
        text=top["unidades"].apply(lambda v: f"{v:,}"),
        textposition="outside",
        # Hover: SKU + descripción + unidades
        customdata=top[["descripcion"]].values,
        hovertemplate=(
            "<b>SKU: %{y}</b><br>"
            "📦 %{customdata[0]}<br>"
            "Unidades: %{x:,}"
            "<extra></extra>"
        ),
    ))

    fig.update_layout(
        height=max(380, n_top * 38),
        margin=dict(l=10, r=80, t=10, b=30),
        xaxis=dict(showgrid=True, gridcolor="#e8f5ee", title="Unidades"),
        yaxis=dict(showgrid=False, title=""),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Arial", size=12, color="#2d3436"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabla expandible con SKU + descripción
    with st.expander("📋 Ver tabla detalle"):
        tabla = top.sort_values("unidades", ascending=False).reset_index(drop=True)
        tabla.index += 1
        tabla = tabla.rename(columns={"sku": "SKU", "unidades": "Unidades", "descripcion": "Descripción"})
        tabla["Unidades"] = tabla["Unidades"].apply(lambda v: f"{v:,}")
        st.dataframe(tabla[["SKU", "Descripción", "Unidades"]], use_container_width=True)


def _render_evolutivo(df):
    st.markdown('<div class="titulo-seccion">📈 Evolutivo de despachos por mes</div>', unsafe_allow_html=True)

    col_t, col_m = st.columns([2, 2])

    with col_t:
        tiendas_disp = sorted(df["nombre_tienda"].unique().tolist())
        sel_tiendas = st.multiselect(
            "Tienda(s)",
            options=["TODAS"] + tiendas_disp,
            default=["TODAS"],
            key="evol_tiendas"
        )
    with col_m:
        meses_disp = sorted(df["mes"].unique(), key=lambda m: ORDEN_MESES.index(m) if m in ORDEN_MESES else 99)
        sel_meses = st.multiselect(
            "Mes(es)",
            options=meses_disp,
            default=meses_disp,
            key="evol_meses"
        )

    if not sel_meses:
        st.info("Selecciona al menos un mes.")
        return

    df_f = df.copy()
    if "TODAS" not in sel_tiendas and sel_tiendas:
        df_f = df_f[df_f["nombre_tienda"].isin(sel_tiendas)]
    if sel_meses:
        df_f = df_f[df_f["mes"].isin(sel_meses)]

    # Cuando es "TODAS" → línea total; cuando hay selección → una línea por tienda
    modo_total = "TODAS" in sel_tiendas or not sel_tiendas

    fig = go.Figure()

    if modo_total:
        pivot = df_f.groupby("mes")["unidades"].sum().reset_index()
        pivot = _ordenar_meses(pivot)
        fig.add_trace(go.Scatter(
            x=pivot["mes"],
            y=pivot["unidades"],
            mode="lines+markers+text",
            name="TOTAL",
            line=dict(color=GREEN_MAIN, width=3),
            marker=dict(size=10, color=GREEN_MAIN),
            text=pivot["unidades"].apply(lambda v: f"{v:,}"),
            textposition="top center",
            hovertemplate="<b>Total</b><br>Mes: %{x}<br>Unidades: %{y:,}<extra></extra>",
            fill="tozeroy",
            fillcolor="rgba(45,158,107,0.12)",
        ))
    else:
        pivot = (
            df_f.groupby(["mes", "nombre_tienda"])["unidades"]
            .sum()
            .reset_index()
        )
        pivot = _ordenar_meses(pivot)
        tiendas_sel_list = [t for t in sel_tiendas if t != "TODAS"]
        for i, tienda in enumerate(tiendas_sel_list):
            df_t = pivot[pivot["nombre_tienda"] == tienda]
            if df_t.empty:
                continue
            color = COLORES_TIENDAS[i % len(COLORES_TIENDAS)]
            fig.add_trace(go.Scatter(
                x=df_t["mes"],
                y=df_t["unidades"],
                mode="lines+markers+text",
                name=tienda,
                line=dict(color=color, width=2.5),
                marker=dict(size=8, color=color),
                text=df_t["unidades"].apply(lambda v: f"{v:,}"),
                textposition="top center",
                hovertemplate=f"<b>{tienda}</b><br>Mes: %{{x}}<br>Unidades: %{{y:,}}<extra></extra>",
            ))

    fig.update_layout(
        height=420,
        margin=dict(l=10, r=20, t=20, b=80),
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor="#e8f5ee", title="Unidades"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Arial", size=12, color="#2d3436"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="left", x=0),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 Ver tabla pivoteada"):
        if modo_total:
            tabla = pivot.set_index("mes")[["unidades"]]
            tabla.columns = ["Unidades"]
            tabla["Unidades"] = tabla["Unidades"].apply(lambda v: f"{v:,}")
            st.dataframe(tabla, use_container_width=True)
        else:
            tabla = pivot.pivot_table(
                index="nombre_tienda", columns="mes", values="unidades",
                aggfunc="sum", fill_value=0
            )
            cols_ord = [m for m in ORDEN_MESES if m in tabla.columns]
            tabla = tabla[cols_ord]
            tabla["TOTAL"] = tabla.sum(axis=1)
            tabla = tabla.sort_values("TOTAL", ascending=False)
            st.dataframe(tabla.style.format("{:,}"), use_container_width=True)


def _render_heatmap(df):
    st.markdown('<div class="titulo-seccion">🗺️ Mapa de calor tienda × mes</div>', unsafe_allow_html=True)

    pivot = df.groupby(["nombre_tienda", "mes"])["unidades"].sum().reset_index()
    tabla = pivot.pivot_table(index="nombre_tienda", columns="mes", values="unidades", fill_value=0)
    cols_ord = [m for m in ORDEN_MESES if m in tabla.columns]
    tabla = tabla[cols_ord]
    tabla["TOTAL"] = tabla.sum(axis=1)
    tabla = tabla.sort_values("TOTAL", ascending=False).drop(columns=["TOTAL"])

    fig = px.imshow(
        tabla,
        color_continuous_scale=[
            [0.0,  "#f0faf4"],
            [0.25, "#85dcaa"],
            [0.5,  "#3dbb7e"],
            [0.75, "#c8e06a"],
            [1.0,  "#e8a020"],
        ],
        aspect="auto",
        text_auto=True,
        labels=dict(color="Unidades"),
    )
    fig.update_traces(texttemplate="%{z:,}", textfont_size=11)
    fig.update_layout(
        height=max(350, len(tabla) * 32 + 80),
        margin=dict(l=10, r=10, t=20, b=40),
        coloraxis_showscale=False,
        xaxis=dict(side="top", tickfont=dict(size=11)),
        yaxis=dict(tickfont=dict(size=11)),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Arial", size=11, color="#2d3436"),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_dash_despachos():
    df = cargar_despachos()

    if df.empty:
        st.warning("⚠️ Sin datos en CONSOLIDADO_DESPACHOS o error de conexión.")
        return

    columnas_req = {"sku", "unidades", "mes"}
    faltantes = columnas_req - set(df.columns)
    if faltantes:
        st.error(f"❌ Columnas faltantes en el sheet: {', '.join(faltantes)}")
        return

    st.markdown('<div class="titulo-seccion">📊 Dashboard de Despachos</div>', unsafe_allow_html=True)
    _render_metricas_despachos(df)
    st.divider()
    _render_top10(df)
    st.divider()
    _render_evolutivo(df)
    st.divider()
    _render_heatmap(df)


# =========================================================
# 4. FUNCIONES DE PROCESAMIENTO (IMPORTACIONES)
# =========================================================

def update_consolidado_arribo(doc, fecha):
    try:
        sh_cons = abrir_archivo_dinamico("Consolidado - Carcasas")
        wks_cons = sh_cons.sheet1
        all_data = wks_cons.get_all_values()
        headers = [h.upper() for h in all_data[0]]

        col_doc = headers.index("NOMBRE CORREO")
        col_status = headers.index("STATUS")
        col_fecha = headers.index("FCH LLEGADA")
        col_recuento = headers.index("RECUENTO") if "RECUENTO" in headers else None

        cells_to_update = []
        filas_para_traspaso = []

        for i, row in enumerate(all_data[1:], start=2):
            if row[col_doc] == str(doc):
                if col_recuento is not None and str(row[col_recuento]).strip() not in ["1", "1.0"]:
                    continue
                cells_to_update.append(gspread.Cell(i, col_status + 1, "ARRIBADO"))
                cells_to_update.append(gspread.Cell(i, col_fecha + 1, str(fecha)))
                filas_para_traspaso.append(row)

        if cells_to_update:
            wks_cons.update_cells(cells_to_update)

            sh_rec = abrir_archivo_dinamico("RECEPCION_IMPORTACIONES")
            wks_mov = sh_rec.worksheet("MOVIMIENTOS")

            bulk_data = []
            for row in filas_para_traspaso:
                tienda = row[headers.index("TIENDA")].strip()
                if tienda == "4298": dest, proc = "ALMACENAJE", "POR ALMACENAR"
                else:
                    dest = "TIENDA"
                    es_ap = any("APERTURA" in str(row[headers.index(f"X{j}")]).upper()
                                for j in range(1, 10) if f"X{j}" in headers)
                    proc = "APERTURA" if es_ap else "POR DISTRIBUIR"

                col_hora_fech_idx = headers.index("HORA FECH") if "HORA FECH" in headers else 0

                bulk_data.append([
                    row[headers.index("ID_DESPACHO")] if "ID_DESPACHO" in headers else row[0],
                    row[col_doc], row[headers.index("ASN")], tienda,
                    row[headers.index("CANTIDAD")], "Pendiente", str(fecha),
                    row[col_hora_fech_idx], dest, proc, ""
                ])
            wks_mov.append_rows(bulk_data)
            return True
    except Exception as e:
        st.error(f"Error técnico: {e}"); return False


# =========================================================
# 5. UI Y RENDERIZADO
# =========================================================

df_import, df_recep, df_tiendas = cargar_datos_completos()

st.title("📦 Gestión de Importaciones")
menu = st.sidebar.radio("MENÚ PRINCIPAL", [
    "📦 Importaciones",
    "🚚 Distribución",
    "📊 Dash Despachos",
])

# ----------------------------------------------------------
# MENÚ: IMPORTACIONES
# ----------------------------------------------------------
if menu == "📦 Importaciones":
    tab_dash, tab_recep, tab_ops = st.tabs(["📊 Dash Importacion", "📑 Gestión interna", "⚙️ Operaciones"])

    with tab_dash:
        st.subheader("🏪 Próximas Aperturas")
        if not df_tiendas.empty:
            columnas_tiendas_req = ["ESTADO", "FCH ESTIMADA", "TIENDA", "DESCRIPCION"]
            if all(col in df_tiendas.columns for col in columnas_tiendas_req):
                df_ap = df_tiendas[df_tiendas["ESTADO"].str.upper().str.contains("PENDIENTE", na=False)].copy()
                df_ap["FCH_DT"] = pd.to_datetime(df_ap["FCH ESTIMADA"], dayfirst=True, errors='coerce')
                df_filtrado = df_ap[df_ap["FCH_DT"] >= datetime.now()].sort_values("FCH_DT").head(4)
                cols = st.columns(4)
                for i, (_, row) in enumerate(df_filtrado.iterrows()):
                    with cols[i % 4]:
                        st.markdown(f'''<div class="apertura-card">
                            <div class="tienda-titulo">🏪 {row["TIENDA"]}</div>
                            <div class="desc-tienda">{row["DESCRIPCION"]}</div>
                            <div class="fecha-est">📅 {row.get("FCH ESTIMADA","")}</div>
                        </div>''', unsafe_allow_html=True)
            else:
                st.warning("⚠️ Columnas faltantes en 'TIENDAS CARCASAS' (Requiere: ESTADO, FCH ESTIMADA, TIENDA, DESCRIPCION)")

        st.markdown('<div class="titulo-seccion">STATUS GLOBAL</div>', unsafe_allow_html=True)
        if not df_import.empty:
            columnas_import_req = ["NOMBRE CORREO", "HORA FECH", "STATUS", "FCH LLEGADA"]
            columnas_faltantes = [c for c in columnas_import_req if c not in df_import.columns]

            if columnas_faltantes:
                st.error(f"❌ **Estructura incorrecta en la hoja 'Consolidado - Carcasas':** Falta la(s) columna(s): {', '.join(columnas_faltantes)}")
            else:
                m1, m2, m3 = st.columns(3)
                total = df_import["NOMBRE CORREO"].nunique()
                arribados = df_import[df_import["STATUS"] == "ARRIBADO"]["NOMBRE CORREO"].nunique()
                m1.metric("Total Docs", total)
                m2.metric("Arribados", arribados)
                m3.metric("En Tránsito", total - arribados)

                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    st.write("### ⏳ Pendientes")
                    st.dataframe(df_import[df_import["STATUS"] != "ARRIBADO"].groupby(["NOMBRE CORREO", "HORA FECH", "STATUS"]).size().reset_index(name="ASNs"), use_container_width=True, hide_index=True)
                with c2:
                    st.write("### ✅ Arribados")
                    st.dataframe(df_import[df_import["STATUS"] == "ARRIBADO"].groupby(["NOMBRE CORREO", "FCH LLEGADA"]).size().reset_index(name="ASNs"), use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ No hay registros con RECUENTO = 1, o la hoja está vacía.")

    with tab_recep:
        st.markdown("### 🗺️ Dash Recepción")
        if not df_recep.empty:
            columnas_recep_req = ["STATUS_REC", "IMPORTACION", "DESTINO", "PROCESO"]
            if all(col in df_recep.columns for col in columnas_recep_req):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.info("🚨 **PENDIENTE**")
                    df_p = df_recep[df_recep["STATUS_REC"].str.upper() == "PENDIENTE"]
                    if not df_p.empty:
                        st.dataframe(df_p.groupby(["IMPORTACION", "DESTINO", "PROCESO"]).size().reset_index(name="BULTOS"), use_container_width=True, hide_index=True)
                with col2:
                    st.success("🏢 **EN STOCK**")
                    df_s = df_recep[df_recep["STATUS_REC"].str.upper() == "ALMACENADO"]
                    if not df_s.empty:
                        st.dataframe(df_s.groupby(["IMPORTACION", "DESTINO"]).size().reset_index(name="BULTOS"), use_container_width=True, hide_index=True)
                with col3:
                    st.warning("🚚 **PROGRAMADO / ENTREGADO**")
                    df_pe = df_recep[df_recep["STATUS_REC"].str.upper().isin(["PROGRAMADO", "ENTREGADO"])]
                    if not df_pe.empty and "FECHA ENTREGA" in df_recep.columns:
                        st.dataframe(df_pe.groupby(["FECHA ENTREGA", "IMPORTACION", "STATUS_REC"]).size().reset_index(name="BULTOS"), use_container_width=True, hide_index=True)
            else:
                st.warning("⚠️ Estructura incorrecta en la hoja 'RECEPCION_IMPORTACIONES'.")

    with tab_ops:
        st.header("⚙️ Operaciones")
        @st.fragment
        def ops_panel():
            o1, o2 = st.columns(2)
            with o1:
                st.subheader("Confirmar Arribo")
                docs = df_import["NOMBRE CORREO"].unique().tolist() if not df_import.empty and "NOMBRE CORREO" in df_import.columns else []
                if "STATUS" in df_import.columns:
                    docs = df_import[df_import["STATUS"] != "ARRIBADO"]["NOMBRE CORREO"].unique().tolist()

                with st.form("arribo_f", clear_on_submit=True):
                    d = st.selectbox("Documento", docs)
                    f = st.date_input("Fecha LLegada", date.today())
                    if st.form_submit_button("Registrar Arribo"):
                        if update_consolidado_arribo(d, f):
                            st.toast("¡Arribo registrado!", icon="✅")
                            st.cache_data.clear(); st.rerun()
            with o2:
                st.subheader("Confirmar Stock")
                if not df_recep.empty and "STATUS_REC" in df_recep.columns and "ASN" in df_recep.columns:
                    asns = df_recep[df_recep["STATUS_REC"].str.upper() == "PENDIENTE"]["ASN"].unique().tolist()
                    with st.form("stock_f", clear_on_submit=True):
                        a = st.selectbox("ASN", asns)
                        if st.form_submit_button("Confirmar Ingreso"):
                            try:
                                sh_r = abrir_archivo_dinamico("RECEPCION_IMPORTACIONES")
                                w_m = sh_r.worksheet("MOVIMIENTOS")
                                cell = w_m.find(str(a))
                                w_m.update_cell(cell.row, 6, "ALMACENADO")
                                st.toast("Stock actualizado", icon="🏢")
                                st.cache_data.clear(); st.rerun()
                            except: st.error("ASN no encontrado o error de red")
        ops_panel()

# ----------------------------------------------------------
# MENÚ: DISTRIBUCIÓN
# ----------------------------------------------------------
if menu == "🚚 Distribución":
    st.info("Módulo de distribución — agrega aquí tu código existente.")

# ----------------------------------------------------------
# MENÚ: DASH DESPACHOS
# ----------------------------------------------------------
if menu == "📊 Dash Despachos":
    render_dash_despachos()

# ----------------------------------------------------------
# SINCRONIZAR
# ----------------------------------------------------------
if st.sidebar.button("🔄 Sincronizar Todo"):
    st.cache_data.clear(); st.rerun()
