"""
reports/trazabilidad_report.py
Reporte de trazabilidad con filtros: CTN, SKU, tipo de movimiento.
"""

import pandas as pd


def filtrar_trazabilidad(
    df: pd.DataFrame,
    ctn:      str | None = None,
    sku:      str | None = None,
    tipo_mov: str | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
) -> pd.DataFrame:
    """
    Filtra el DataFrame de trazabilidad según los parámetros indicados.
    Todos los parámetros son opcionales; si son None/vacío se ignoran.

    Returns:
        DataFrame ordenado por fecha descendente con columnas para la vista.
    """
    result = df.copy()

    if ctn:
        result = result[result["ctn"].str.strip() == str(ctn).strip()]
    if sku:
        result = result[result["sku"].str.strip() == str(sku).strip()]
    if tipo_mov:
        result = result[result["tipo_mov"] == tipo_mov]
    if fecha_desde:
        result = result[result["fecha"] >= pd.to_datetime(fecha_desde)]
    if fecha_hasta:
        result = result[result["fecha"] <= pd.to_datetime(fecha_hasta)]

    result = result.sort_values("fecha", ascending=False).reset_index(drop=True)

    # Formatear fechas para presentación
    result["fecha_str"] = result["fecha"].dt.strftime("%Y-%m-%d")
    result["vcto_str"]  = result["vcto"].dt.strftime("%Y-%m-%d").where(result["vcto"].notna(), "")

    return result[[
        "fecha_str", "ctn", "sku", "desc",
        "tipo_mov", "units", "estado",
        "guia", "tienda", "vcto_str",
    ]].rename(columns={
        "fecha_str": "fecha",
        "vcto_str":  "fecha_vcto",
        "desc":      "descripcion",
        "units":     "unidades",
        "tipo_mov":  "tipo_movimiento",
    })


def opciones_filtros(df: pd.DataFrame) -> dict:
    """Devuelve listas únicas para poblar los dropdowns de la UI."""
    return {
        "ctns":  sorted(df["ctn"].dropna().unique().tolist()),
        "skus":  sorted(df["sku"].dropna().unique().tolist()),
        "tipos": sorted(df["tipo_mov"].dropna().unique().tolist()),
    }
