"""Aplicación web Flask para consultar la deuda de patentes de Santa Fe.

Expone una interfaz web (templates/index.html) y una API JSON en /api/consulta.
La lógica de scraping vive en scraper.py.
"""

import asyncio
import os

from flask import Flask, jsonify, render_template, request

from scraper import consultar_patente_data

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/consulta")
def api_consulta():
    patente = request.args.get("patente", "")
    if not patente:
        return jsonify({"success": False, "error": "Patente vacía"})

    # Ejecutar el scraper async dentro del hilo síncrono de Flask
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(consultar_patente_data(patente))
        loop.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": f"Error del servidor: {str(e)}"})


if __name__ == "__main__":
    # host/puerto configurables por variables de entorno (útil en Docker)
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "9000"))
    print(f"[+] Servidor de patentes iniciando en http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
