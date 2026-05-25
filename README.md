# WMS MASEF — Warehouse Management System

API Python (Flask) conectada a Google Sheets como base de datos.

## Estructura del proyecto

```
wms_masef/
├── app/
│   └── main.py                  # Flask API — todos los endpoints
├── config/
│   └── settings.py              # Variables de configuración
├── reports/
│   ├── stock_report.py          # Lógica: stock histórico por fecha
│   └── trazabilidad_report.py   # Lógica: filtros CTN / SKU / tipo
├── utils/
│   └── sheets_connector.py      # Conexión Google Sheets API
├── .env.example                 # Variables de entorno (copia a .env)
├── requirements.txt
└── README.md
```

## Setup rápido

### 1. Credenciales Google

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un proyecto → Habilita **Google Sheets API** y **Google Drive API**
3. `IAM & Admin` → `Service Accounts` → `Create` → descarga el JSON
4. Guarda el JSON como `credentials.json` en la raíz del proyecto
5. Comparte tu Google Sheet con el email del service account (editor)

### 2. Variables de entorno

```bash
cp .env.example .env
# Edita .env con tu SPREADSHEET_ID y rutas
```

El `SPREADSHEET_ID` está en la URL del Sheet:
`https://docs.google.com/spreadsheets/d/**SPREADSHEET_ID**/edit`

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Correr la app

```bash
python app/main.py
```

La API estará en `http://localhost:5000`

---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/health` | Estado del servicio |
| GET | `/api/stock` | Reporte de stock con filtro de fecha |
| GET | `/api/trazabilidad` | Movimientos con filtros CTN/SKU/tipo |
| GET | `/api/filtros` | Opciones para dropdowns de la UI |
| POST | `/api/refresh` | Invalida cache y recarga el Sheet |

### Ejemplos de uso

```bash
# Stock al 2026-03-01
curl "http://localhost:5000/api/stock?fecha_corte=2026-03-01"

# Stock filtrando por SKU
curl "http://localhost:5000/api/stock?fecha_corte=2026-03-01&sku=1030013"

# Trazabilidad de un contenedor
curl "http://localhost:5000/api/trazabilidad?ctn=12323"

# Trazabilidad filtrando por tipo
curl "http://localhost:5000/api/trazabilidad?tipo_mov=INGRESO&fecha_desde=2026-01-01"

# Forzar recarga del Sheet
curl -X POST "http://localhost:5000/api/refresh"
```

---

## Estructura del Google Sheet

La pestaña `TRAZABILIDAD` debe tener exactamente estas columnas:

| FECHA | SKU MASEF | DESCRIPTION | CTN | ESTADO | FECHA VCTO | TOTAL UNIT | GUIA | TIPO DE MOVIMIENTO | Tienda |
|-------|-----------|-------------|-----|--------|------------|------------|------|--------------------|--------|

Los tipos de movimiento válidos son:
- **INGRESO** — entrada de mercadería
- **SALIDA** — despacho a tienda/cliente
- **AJUSTE-IN** — ajuste positivo de inventario
- **AJUSTE-OUT** — ajuste negativo de inventario
- **MERMA** — pérdida/daño

---

## Repositorio GitHub

```bash
git init
git add .
git commit -m "feat: WMS MASEF — API Flask + Google Sheets"
git remote add origin https://github.com/TU_USUARIO/wms-masef.git
git push -u origin main
```

> **Importante**: agrega `credentials.json` y `.env` al `.gitignore` — nunca subas credenciales.

```gitignore
credentials.json
.env
__pycache__/
*.pyc
```
