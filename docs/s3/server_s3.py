"""Servidor Flask con CRUD completo sobre S3 (almacenamiento de objetos) usando boto3."""

import json
import time
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from flask import Flask, jsonify, request

app = Flask(__name__)

BUCKET_NAME = "ab-iot-stefany-2026"
PREFIX = "mensajes/"

s3 = boto3.client("s3")


def clave(registro_id):
    return f"{PREFIX}{registro_id}.json"


@app.route("/", methods=["GET"])
def index():
    return "hola mundo", 200


# ---------- CREATE ----------
@app.route("/data", methods=["POST"])
def data():
    payload = request.get_json(silent=True, force=True)

    if payload is None:
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Cuerpo no es JSON valido:")
        print(request.get_data(as_text=True))
        return jsonify(error="Se esperaba un cuerpo JSON valido"), 400

    mensaje = payload.get("mensaje", json.dumps(payload, ensure_ascii=False))
    ip_origen = request.remote_addr
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    nuevo_id = str(int(time.time() * 1000))  # timestamp en ms, unico y ordenable

    objeto = {
        "id": nuevo_id,
        "mensaje": mensaje,
        "ip_origen": ip_origen,
        "fecha": fecha,
    }

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=clave(nuevo_id),
        Body=json.dumps(objeto, ensure_ascii=False),
        ContentType="application/json",
    )

    print(f"[{fecha}] Guardado en S3 (id={nuevo_id}) desde {ip_origen}: {mensaje}")

    return jsonify(status="ok", id=nuevo_id, received=payload), 200


# ---------- READ (todos) ----------
@app.route("/registros", methods=["GET"])
def registros():
    resultado = []
    paginador = s3.get_paginator("list_objects_v2")

    for pagina in paginador.paginate(Bucket=BUCKET_NAME, Prefix=PREFIX):
        for item in pagina.get("Contents", []):
            respuesta = s3.get_object(Bucket=BUCKET_NAME, Key=item["Key"])
            objeto = json.loads(respuesta["Body"].read())
            resultado.append(objeto)

    resultado.sort(key=lambda x: x["id"], reverse=True)

    return jsonify(total=len(resultado), registros=resultado), 200


# ---------- READ (uno solo) ----------
@app.route("/registros/<registro_id>", methods=["GET"])
def obtener_registro(registro_id):
    try:
        respuesta = s3.get_object(Bucket=BUCKET_NAME, Key=clave(registro_id))
        objeto = json.loads(respuesta["Body"].read())
        return jsonify(objeto), 200
    except ClientError as error:
        if error.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return jsonify(error=f"No existe un registro con id {registro_id}"), 404
        raise


# ---------- UPDATE ----------
@app.route("/registros/<registro_id>", methods=["PUT"])
def actualizar_registro(registro_id):
    payload = request.get_json(silent=True, force=True)

    if payload is None or "mensaje" not in payload:
        return jsonify(error="Se esperaba un JSON con el campo 'mensaje'"), 400

    try:
        respuesta = s3.get_object(Bucket=BUCKET_NAME, Key=clave(registro_id))
        objeto = json.loads(respuesta["Body"].read())
    except ClientError as error:
        if error.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return jsonify(error=f"No existe un registro con id {registro_id}"), 404
        raise

    objeto["mensaje"] = payload["mensaje"]

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=clave(registro_id),
        Body=json.dumps(objeto, ensure_ascii=False),
        ContentType="application/json",
    )

    return jsonify(status="ok", id=registro_id, mensaje_actualizado=payload["mensaje"]), 200


# ---------- DELETE ----------
@app.route("/registros/<registro_id>", methods=["DELETE"])
def eliminar_registro(registro_id):
    try:
        s3.head_object(Bucket=BUCKET_NAME, Key=clave(registro_id))
    except ClientError as error:
        if error.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return jsonify(error=f"No existe un registro con id {registro_id}"), 404
        raise

    s3.delete_object(Bucket=BUCKET_NAME, Key=clave(registro_id))

    return jsonify(status="ok", id_eliminado=registro_id), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)