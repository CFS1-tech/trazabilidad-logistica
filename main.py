"""
app/main.py
API Flask del WMS MASEF.
Endpoints:
  GET  /api/stock          → reporte de stock con filtro de fecha
  GET  /api/trazabilidad   → movimientos con filtros CTN/SKU/tipo
  GET  /api/filtros        → opciones para dropdowns de la UI
  GET  /api/health         → estado del servicio
"""

from flask import Flask, jsonify, request
from utils.sheets_connector import cargar_trazabilidad
from reports.stock_report import calcular_stock, resumen_stock
from reports.trazabilidad_report import filtrar_trazabilidad, opciones_filtros
from config.settings import FLASK_HOST, FLASK_PORT, FLASK_DEBUG
from datetime import date
import pandas as pd

app = Flask(__name__)

# ── Cache simple en memoria (recarga cada llamada; usa Redis en producción) ──
_cache: dict = {}


def get_df() -> pd.DataFrame:
    """Obtiene el DataFrame desde Sheets (con cache por sesión)."""
    if "df" not in _cache:
        _cache["df"] = cargar_trazabilidad()
    return _cache["df"]


def invalidar_cache():
    _cache.clear()


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "version": "1.0.0"})


@app.get("/api/stock")
def api_stock():
    """
    Query params:
      fecha_corte  (str, YYYY-MM-DD) – default: hoy
      sku          (str, opcional)   – filtrar por SKU
      buscar       (str, opcional)   – búsqueda libre en descripción
    """
    fecha_corte = request.args.get("fecha_corte", str(date.today()))
    sku_filtro  = request.args.get("sku", "").strip()
    buscar      = request.args.get("buscar", "").strip().lower()

    df   = get_df()
    data = calcular_stock(df, fecha_corte)

    if sku_filtro:
        data = data[data["sku"] == sku_filtro]
    if buscar:
        data = data[
            data["sku"].str.lower().str.contains(buscar) |
            data["desc"].str.lower().str.contains(buscar)
        ]

    metricas = resumen_stock(df, fecha_corte)

    return jsonify({
        "fecha_corte": fecha_corte,
        "metricas":    metricas,
        "total":       len(data),
        "rows":        data.to_dict(orient="records"),
    })


@app.get("/api/trazabilidad")
def api_trazabilidad():
    """
    Query params:
      ctn          (str, opcional)
      sku          (str, opcional)
      tipo_mov     (str, opcional) – INGRESO | SALIDA | AJUSTE-IN | AJUSTE-OUT | MERMA
      fecha_desde  (str, YYYY-MM-DD, opcional)
      fecha_hasta  (str, YYYY-MM-DD, opcional)
      page         (int, default 1)
      page_size    (int, default 50)
    """
    ctn         = request.args.get("ctn")
    sku         = request.args.get("sku")
    tipo_mov    = request.args.get("tipo_mov")
    fecha_desde = request.args.get("fecha_desde")
    fecha_hasta = request.args.get("fecha_hasta")
    page        = int(request.args.get("page", 1))
    page_size   = int(request.args.get("page_size", 50))

    df   = get_df()
    data = filtrar_trazabilidad(df, ctn, sku, tipo_mov, fecha_desde, fecha_hasta)

    total  = len(data)
    start  = (page - 1) * page_size
    end    = start + page_size
    rows   = data.iloc[start:end].to_dict(orient="records")

    return jsonify({
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "pages":     -(-total // page_size),  # ceil
        "rows":      rows,
    })


@app.get("/api/filtros")
def api_filtros():
    """Devuelve las opciones únicas para los dropdowns de la UI."""
    df = get_df()
    return jsonify(opciones_filtros(df))


@app.post("/api/refresh")
def api_refresh():
    """Fuerza recarga del Google Sheet (invalida cache)."""
    invalidar_cache()
    return jsonify({"status": "cache_cleared"})


# ── Dev server ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
