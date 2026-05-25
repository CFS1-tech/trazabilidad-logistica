"""
reports/stock_report.py
Lógica de reporte de stock con filtro histórico por fecha de corte.
"""

import pandas as pd
from config.settings import MOVIMIENTOS_ENTRADA, MOVIMIENTOS_SALIDA


def calcular_stock(df: pd.DataFrame, fecha_corte: str) -> pd.DataFrame:
    """
    Calcula el stock acumulado desde el inicio hasta `fecha_corte` (inclusive).

    Args:
        df:           DataFrame de trazabilidad (columnas internas).
        fecha_corte:  Fecha string 'YYYY-MM-DD' o datetime.

    Returns:
        DataFrame con columnas:
            sku, desc, ingresos, salidas, stock, ultima_fecha
    """
    corte = pd.to_datetime(fecha_corte)
    sub   = df[df["fecha"] <= corte].copy()

    def signo(tipo):
        if tipo in MOVIMIENTOS_ENTRADA:
            return 1
        if tipo in MOVIMIENTOS_SALIDA:
            return -1
        return 0

    sub["delta"] = sub.apply(lambda r: signo(r["tipo_mov"]) * r["units"], axis=1)

    # Ingresos y salidas brutas
    ent = (
        sub[sub["tipo_mov"].isin(MOVIMIENTOS_ENTRADA)]
        .groupby(["sku", "desc"])["units"]
        .sum()
        .rename("ingresos")
    )
    sal = (
        sub[sub["tipo_mov"].isin(MOVIMIENTOS_SALIDA)]
        .groupby(["sku", "desc"])["units"]
        .sum()
        .rename("salidas")
    )
    stock = (
        sub.groupby(["sku", "desc"])["delta"]
        .sum()
        .rename("stock")
    )
    ultima = (
        sub.groupby(["sku", "desc"])["fecha"]
        .max()
        .rename("ultima_fecha")
    )

    result = (
        pd.concat([ent, sal, stock, ultima], axis=1)
        .fillna(0)
        .reset_index()
    )
    result["ingresos"]    = result["ingresos"].astype(int)
    result["salidas"]     = result["salidas"].astype(int)
    result["stock"]       = result["stock"].astype(int)
    result["ultima_fecha"] = pd.to_datetime(result["ultima_fecha"]).dt.strftime("%Y-%m-%d")

    return result.sort_values("stock", ascending=False)


def resumen_stock(df: pd.DataFrame, fecha_corte: str) -> dict:
    """Métricas agregadas para las tarjetas del dashboard."""
    corte = pd.to_datetime(fecha_corte)
    sub   = df[df["fecha"] <= corte]
    return {
        "total_skus":    int(sub[sub["tipo_mov"].isin(MOVIMIENTOS_ENTRADA)]["sku"].nunique()),
        "total_unidades": int(calcular_stock(df, fecha_corte)["stock"].clip(lower=0).sum()),
        "ingresos_acum": int(sub[sub["tipo_mov"] == "INGRESO"]["units"].sum()),
        "salidas_acum":  int(sub[sub["tipo_mov"] == "SALIDA"]["units"].sum()),
    }
