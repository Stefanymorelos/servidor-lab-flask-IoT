"""Servidor Flask con CRUD completo sobre RDS MySQL (motor externo administrado por AWS)."""

import json
from datetime import datetime

import mysql.connector
from flask import Flask, jsonify, request

app = Flask(__name__)

DB_CONFIG = {
    "host": "database-1.cydhsnuiiujn.us-east-1.rds.amazonaws.com",
    "port": 3306,
    "user": "admin",
    "password": "TU_CONTRASENA_MAESTRA_AQUI",
    "database": "lab_iot",
}


def obtener_conexion():
    return mysql.connector.connect(**DB_CONFIG)


def inicializar_db():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS mensajes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            mensaje TEXT NOT NULL,
            ip_origen VARCHAR(45),
            fecha DATETIME NOT NULL
        )
        """
    )
    conexion.commit()
    cursor.close()
    conexion.close()


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
    fecha = datetime.now()

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "INSERT INTO mensajes (mensaje, ip_origen, fecha) VALUES (%s, %s, %s)",
        (mensaje, ip_origen, fecha),
    )
    conexion.commit()
    nuevo_id = cursor.lastrowid
    cursor.close()
    conexion.close()

    print(f"[{fecha:%Y-%m-%d %H:%M:%S}] Guardado en RDS (id={nuevo_id}) desde {ip_origen}: {mensaje}")

    return jsonify(status="ok", id=nuevo_id, received=payload), 200


# ---------- READ (todos) ----------
@app.route("/registros", methods=["GET"])
def registros():
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT id, mensaje, ip_origen, fecha FROM mensajes ORDER BY id DESC")
    filas = cursor.fetchall()
    cursor.close()
    conexion.close()

    for fila in filas:
        fila["fecha"] = fila["fecha"].strftime("%Y-%m-%d %H:%M:%S")

    return jsonify(total=len(filas), registros=filas), 200


# ---------- READ (uno solo) ----------
@app.route("/registros/<int:registro_id>", methods=["GET"])
def obtener_registro(registro_id):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, mensaje, ip_origen, fecha FROM mensajes WHERE id = %s",
        (registro_id,),
    )
    fila = cursor.fetchone()
    cursor.close()
    conexion.close()

    if fila is None:
        return jsonify(error=f"No existe un registro con id {registro_id}"), 404

    fila["fecha"] = fila["fecha"].strftime("%Y-%m-%d %H:%M:%S")
    return jsonify(fila), 200


# ---------- UPDATE ----------
@app.route("/registros/<int:registro_id>", methods=["PUT"])
def actualizar_registro(registro_id):
    payload = request.get_json(silent=True, force=True)

    if payload is None or "mensaje" not in payload:
        return jsonify(error="Se esperaba un JSON con el campo 'mensaje'"), 400

    nuevo_mensaje = payload["mensaje"]

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        "UPDATE mensajes SET mensaje = %s WHERE id = %s",
        (nuevo_mensaje, registro_id),
    )
    conexion.commit()
    filas_afectadas = cursor.rowcount
    cursor.close()
    conexion.close()

    if filas_afectadas == 0:
        return jsonify(error=f"No existe un registro con id {registro_id}"), 404

    return jsonify(status="ok", id=registro_id, mensaje_actualizado=nuevo_mensaje), 200


# ---------- DELETE ----------
@app.route("/registros/<int:registro_id>", methods=["DELETE"])
def eliminar_registro(registro_id):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM mensajes WHERE id = %s", (registro_id,))
    conexion.commit()
    filas_afectadas = cursor.rowcount
    cursor.close()
    conexion.close()

    if filas_afectadas == 0:
        return jsonify(error=f"No existe un registro con id {registro_id}"), 404

    return jsonify(status="ok", id_eliminado=registro_id), 200


if __name__ == "__main__":
    inicializar_db()
    app.run(host="0.0.0.0", port=80, debug=False)