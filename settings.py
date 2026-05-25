"""
config/settings.py
Configuración central del WMS MASEF.
Carga credenciales desde variables de entorno (.env).
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Google Sheets ──────────────────────────────────────────
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
SPREADSHEET_ID          = os.getenv("SPREADSHEET_ID", "")          # ID del Google Sheet
SHEET_NAME              = os.getenv("SHEET_NAME", "TRAZABILIDAD")  # Pestaña con la data

# ── App Flask ──────────────────────────────────────────────
FLASK_HOST  = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT  = int(os.getenv("FLASK_PORT", 5000))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"

# ── Columnas esperadas en el Sheet ─────────────────────────
COLUMNAS = {
    "fecha":     "FECHA",
    "sku":       "SKU MASEF",
    "desc":      "DESCRIPTION",
    "ctn":       "CTN",
    "estado":    "ESTADO",
    "vcto":      "FECHA VCTO",
    "units":     "TOTAL UNIT",
    "guia":      "GUIA",
    "tipo_mov":  "TIPO DE MOVIMIENTO",
    "tienda":    "Tienda",
}

# Tipos que suman al stock
MOVIMIENTOS_ENTRADA = {"INGRESO", "AJUSTE-IN"}
# Tipos que restan al stock
MOVIMIENTOS_SALIDA  = {"SALIDA", "AJUSTE-OUT", "MERMA"}
