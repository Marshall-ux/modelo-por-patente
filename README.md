# Consultor de Deuda de Patentes — Santa Fe

Aplicación que consulta la **deuda de patente de un vehículo** en el portal de la
Provincia de Santa Fe (`https://www.santafe.gov.ar/e-pt-liq-deuda/`).

Automatiza el navegador con **Playwright** (Chromium headless): completa el
formulario, resuelve el captcha **Altcha** (proof-of-work), envía la consulta y
extrae los datos del vehículo, avisos y las tablas de deuda.

Incluye una **interfaz web** (Flask) y una **CLI** de línea de comandos.

## Estructura

```
modelo-por-patente/
├── app.py            # App web Flask + API JSON (/api/consulta)
├── cli.py            # Consulta desde la terminal
├── scraper.py        # Lógica de scraping compartida (Playwright)
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── static/           # Assets (logo)
└── templates/        # index.html (frontend)
```

## Uso con Docker (recomendado)

La imagen se basa en la imagen oficial de Playwright, que ya trae Chromium y
sus dependencias de sistema.

```bash
docker build -t modelo-patente .
docker run --rm -p 9000:9000 modelo-patente
```

Luego abrí <http://localhost:9000>.

## Uso local (sin Docker)

Requiere Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium      # descarga el navegador la primera vez
```

### App web

```bash
python app.py
# http://localhost:9000
```

### CLI

```bash
python cli.py ABC123
python cli.py ABC123 --visible   # muestra el navegador (no headless)
python cli.py                    # pregunta la patente por teclado
```

## API

`GET /api/consulta?patente=ABC123` → JSON

```json
{
  "success": true,
  "vehicle_data": ["..."],
  "notices": ["..."],
  "debts": [{ "headers": ["..."], "rows": [["..."]] }]
}
```

En caso de error: `{ "success": false, "error": "..." }`.

## Configuración

| Variable | Default   | Descripción                     |
|----------|-----------|---------------------------------|
| `HOST`   | `0.0.0.0` | Interfaz de escucha (app.py)    |
| `PORT`   | `9000`    | Puerto de escucha               |

## Notas

- Depende de la estructura del portal público de Santa Fe; si el sitio cambia,
  los selectores del scraper pueden requerir ajustes.
- Uso previsto: consulta de información pública. Respetá los términos de uso del
  portal y evitá volúmenes de consulta abusivos.
