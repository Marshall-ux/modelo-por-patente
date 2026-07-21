# Consultor de Deuda de Patente y Multas

Aplicación que, a partir de la **patente de un vehículo** y de la **jurisdicción
elegida**, consulta la deuda del automotor.

### Jurisdicciones soportadas

| Jurisdicción | Qué consulta | Portal |
|---|---|---|
| **Santa Fe** | Deuda de patente + **multas de tránsito** (Rosario), con descarga del PDF del recibo | `santafe.gov.ar`, `rosario.gob.ar` |
| **Córdoba** | Impuesto automotor (sin multas) | `rentascordoba.gob.ar` |

Automatiza el navegador con **Playwright** (Chromium headless): completa los
formularios, resuelve el captcha **Altcha** (Santa Fe), sortea el reCAPTCHA v3
(Rosario) y extrae los datos. En Santa Fe, deuda y multas se consultan **en
paralelo**.

Incluye una **interfaz web** (Flask) y una **CLI** de línea de comandos.

## Estructura

```
modelo-por-patente/
├── app.py            # App web Flask + API (/api/consulta, /api/recibo)
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
python cli.py ABC123                          # Santa Fe (por defecto)
python cli.py ABC123 --jurisdiccion cordoba   # Córdoba
python cli.py                                 # pregunta la patente por teclado
```

## API

### `GET /api/jurisdicciones`

Devuelve las jurisdicciones disponibles (para poblar el selector).

### `GET /api/consulta?patente=ABC123&jurisdiccion=santa_fe`

`jurisdiccion` acepta `santa_fe` (default) o `cordoba`. Devuelve deuda y multas
en un solo JSON:

```json
{
  "jurisdiccion": "santa_fe",
  "patente": {
    "success": true,
    "vehicle_data": ["..."],
    "notices": ["..."],
    "debts": [{ "headers": ["..."], "rows": [["..."]] }]
  },
  "multas": {
    "success": true,
    "libre_multas": false,
    "fines": [
      {
        "acta": "...",
        "estado": "...",
        "detalles": { "clave": "valor" },
        "ver_acta": "https://...",
        "ver_recibo": "/api/recibo?patente=...&comprobante=...&tipodeuda=..."
      }
    ]
  }
}
```

Cada bloque trae `"success": false` con `"error"` si esa fuente falla (una puede
fallar sin afectar a la otra).

### `GET /api/recibo?patente=&comprobante=&tipodeuda=`

Descarga el **PDF del recibo** de una multa (los parámetros salen del campo
`ver_recibo` de cada multa). Responde con el archivo PDF (`Content-Type:
application/pdf`) o un JSON de error.

## Configuración

| Variable | Default   | Descripción                     |
|----------|-----------|---------------------------------|
| `HOST`   | `0.0.0.0` | Interfaz de escucha (app.py)    |
| `PORT`   | `9000`    | Puerto de escucha               |

## Notas

- Depende de la estructura de los portales públicos de Santa Fe y Rosario; si
  cambian, los selectores del scraper pueden requerir ajustes. El módulo de
  multas usa técnicas anti-detección para el reCAPTCHA v3, más sensibles a
  cambios del sitio.
- Uso previsto: consulta de información pública. Respetá los términos de uso de
  los portales y evitá volúmenes de consulta abusivos.
