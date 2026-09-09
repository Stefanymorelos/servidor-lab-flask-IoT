"""Servidor Flask minimo que recibe JSON en /data y lo imprime en terminal."""

import json
from datetime import datetime

from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "hola mundo", 200

@app.route("/data", methods=["POST"])
def data():
    payload = request.get_json(silent=True, force=True)

    if payload is None:
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Cuerpo no es JSON valido:")
        print(request.get_data(as_text=True))
        return jsonify(error="Se esperaba un cuerpo JSON valido"), 400

    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Mensaje recibido de {request.remote_addr}:")
    print(json.dumps(payload, indent=2, ensure_ascii=False), flush=True)

    return jsonify(status="ok", received=payload), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)