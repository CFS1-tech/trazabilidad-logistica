"""
utils/sheets_connector.py
Conexión con Google Sheets API usando gspread + service account.

SETUP RÁPIDO:
1. En Google Cloud Console → APIs & Services → Credentials → Create Service Account
2. Descarga el JSON → guárdalo como credentials.json en la raíz del proyecto
3. Comparte el Google Sheet con el email del service account
4. Pon el SPREADSHEET_ID en tu .env
"""

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from config.settings import GOOGLE_CREDENTIALS_JSON, SPREADSHEET_ID, SHEET_NAME, COLUMNAS

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _get_client() -> gspread.Client:
    creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_JSON, scopes=SCOPES)
    return gspread.authorize(creds)


def cargar_trazabilidad() -> pd.DataFrame:
    """Lee la hoja TRAZABILIDAD del Google Sheet y devuelve un DataFrame limpio."""
    client = _get_client()
    sh     = client.open_by_key(SPREADSHEET_ID)
    ws     = sh.worksheet(SHEET_NAME)
    data   = ws.get_all_records()
    df     = pd.DataFrame(data)

    # Renombrar a nombres internos
    rev_map = {v: k for k, v in COLUMNAS.items()}
    df.rename(columns=rev_map, inplace=True)

    # Tipos
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["vcto"]  = pd.to_datetime(df["vcto"],  errors="coerce")
    df["units"] = pd.to_numeric(df["units"], errors="coerce").fillna(0).astype(int)
    df["sku"]   = df["sku"].astype(str)
    df["ctn"]   = df["ctn"].astype(str)

    return df.dropna(subset=["fecha"])


def agregar_fila(fila: dict) -> None:
    """Agrega una fila nueva al Sheet (para ingresos/salidas desde la app)."""
    client = _get_client()
    sh     = client.open_by_key(SPREADSHEET_ID)
    ws     = sh.worksheet(SHEET_NAME)
    # Orden de columnas del sheet
    orden  = list(COLUMNAS.values())
    row    = [str(fila.get(COLUMNAS[k], "")) for k in COLUMNAS]
    ws.append_row(row, value_input_option="USER_ENTERED")
