# ══════════════════════════════════════════════════════════════════════════════
# VISTA: STOCK
# ══════════════════════════════════════════════════════════════════════════════
if vista == "📦  Stock":
    st.markdown("## 📦 Reporte de Stock")
    st.caption("Stock acumulado hasta la fecha de corte. El cálculo considera todos los movimientos.")

    # ── Métricas globales arriba ──
    # El stock REAL considera TODOS los movimientos
    sub_global = df[df["FECHA"].dt.date <= date.today()].copy()

    total_entradas = int(
        sub_global[sub_global["TOTAL UNIT"] > 0]["TOTAL UNIT"].sum()
    )

    total_salidas = int(
        sub_global[sub_global["TOTAL UNIT"] < 0]["TOTAL UNIT"].sum() * -1
    )

    # Stock neto por SKU considerando TODO
    neto_sku = sub_global.groupby("SKU MASEF")["TOTAL UNIT"].sum()

    # Solo SKUs con stock positivo
    skus_positivos = neto_sku[neto_sku > 0].index

    df_positivos = sub_global[
        sub_global["SKU MASEF"].isin(skus_positivos)
    ].copy()

    # SOLO ocultar visualmente estado MERMA
    df_positivos = df_positivos[df_positivos["ESTADO"] != "MERMA"]

    por_estado = (
        df_positivos
        .groupby("ESTADO")["TOTAL UNIT"]
        .sum()
    )

    por_estado = por_estado[por_estado > 0]

    total_neto = int(neto_sku[neto_sku > 0].sum())

    cols_metrics = st.columns(1 + len(por_estado))

    cols_metrics[0].metric("Total en stock", f"{total_neto:,}")

    for i, (estado, unidades) in enumerate(por_estado.items()):
        cols_metrics[1 + i].metric(
            estado,
            f"{int(unidades):,}"
        )

    st.divider()

    # ── Filtros ──
    with st.form("form_stock"):

        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

        with col1:
            fecha_corte = st.date_input(
                "📅 Fecha de corte",
                value=date.today(),
                min_value=df["FECHA"].min().date(),
                max_value=date.today()
            )

        with col2:
            buscar = st.text_input(
                "🔎 Buscar SKU o descripción",
                placeholder="ej: NUTELLA"
            )

        with col3:
            estados_opts = ["Todos"] + sorted(
                df["ESTADO"].dropna().unique().tolist()
            )

            f_estado = st.selectbox(
                "🏷️ Estado",
                estados_opts
            )

        with col4:
            st.write("")
            st.write("")
            st.form_submit_button(
                "🔍 Buscar",
                use_container_width=True
            )

    # ── Calcular stock ──
    # IMPORTANTE:
    # Se calcula con TODOS los movimientos
    stock_df = calcular_stock(df, fecha_corte)

    # Solo ocultar visualmente MERMA
    stock_df = stock_df[stock_df["ESTADO"] != "MERMA"]

    # ── Filtros adicionales ──
    if buscar:
        mask = (
            stock_df["SKU MASEF"].str.contains(buscar, case=False, na=False)
            |
            stock_df["DESCRIPTION"].str.contains(buscar, case=False, na=False)
        )

        stock_df = stock_df[mask]

    if f_estado != "Todos":
        stock_df = stock_df[
            stock_df["ESTADO"] == f_estado
        ]

    # ── Tabla ──
    st.markdown(
        f"**Detalle de stock** — {len(stock_df)} SKUs"
    )

    display = stock_df[
        [
            "SKU MASEF",
            "DESCRIPTION",
            "CTN",
            "ESTADO",
            "FECHA VCTO",
            "Stock",
        ]
    ].rename(columns={
        "SKU MASEF": "SKU",
        "DESCRIPTION": "Descripción",
        "FECHA VCTO": "Vencimiento",
        "Stock": "Unidades en Stock",
    })

    max_stock = (
        int(stock_df["Stock"].max())
        if len(stock_df)
        else 1
    )

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Unidades en Stock":
            st.column_config.ProgressColumn(
                "Unidades en Stock",
                min_value=0,
                max_value=max_stock,
                format="%d"
            )
        }
    )

    botones_descarga(display, "stock")
