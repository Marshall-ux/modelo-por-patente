"""Aplicación web Flask para consultar deuda de patente (Santa Fe) y multas
de tránsito (Rosario) de un vehículo.

Expone la interfaz web (templates/index.html) y dos endpoints JSON/archivo:
  - GET /api/consulta?patente=...            -> deuda + multas
  - GET /api/recibo?patente=&comprobante=&tipodeuda=  -> PDF del recibo

La lógica de scraping vive en scraper.py.
"""

import asyncio
import os
from io import BytesIO

from flask import Flask, jsonify, render_template, request, send_file

from scraper import consultar_todo, download_receipt_pdf_data

app = Flask(__name__)


def _run_async(coro):
    """Ejecuta una corrutina en un event loop propio (Flask es síncrono)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/consulta")
def api_consulta():
    patente = request.args.get("patente", "")
    if not patente:
        return jsonify({"success": False, "error": "Patente vacía"})

    try:
        result = _run_async(consultar_todo(patente))
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": f"Error del servidor: {str(e)}"})


@app.route("/api/recibo")
def api_recibo():
    patente = request.args.get("patente", "")
    comprobante = request.args.get("comprobante", "")
    tipodeuda = request.args.get("tipodeuda", "")

    if not patente or not comprobante or not tipodeuda:
        return jsonify({"success": False, "error": "Faltan parámetros obligatorios"}), 400

    try:
        pdf_bytes = _run_async(
            download_receipt_pdf_data(patente, comprobante, tipodeuda)
        )
        return send_file(
            BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"recibo_{patente}_{comprobante.replace(' ', '_')}.pdf",
        )
    except Exception as e:
        return jsonify(
            {"success": False, "error": f"Error al generar/descargar recibo: {str(e)}"}
        ), 500


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "9000"))
    print(f"[+] Servidor de patentes y multas iniciando en http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
