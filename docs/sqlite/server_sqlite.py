"""Servidor Flask con CRUD completo sobre SQLite."""

import json
import sqlite3
from datetime import datetime

from flask import Flask, jsonify, request

app = Flask(__name__)

DB_PATH = "datos.db"


def inicializar_db():
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS mensajes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensaje TEXT NOT NULL,
            ip_origen TEXT,
            fecha TEXT NOT NULL
        )
        """
    )
    conexion.commit()
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
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    cursor.execute(
        "INSERT INTO mensajes (mensaje, ip_origen, fecha) VALUES (?, ?, ?)",
        (mensaje, ip_origen, fecha),
    )
    conexion.commit()
    nuevo_id = cursor.lastrowid
    conexion.close()

    print(f"[{fecha}] Guardado en SQLite (id={nuevo_id}) desde {ip_origen}: {mensaje}")

    return jsonify(status="ok", id=nuevo_id, received=payload), 200


# ---------- READ (todos) ----------
@app.route("/registros", methods=["GET"])
def registros():
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()
    cursor.execute("SELECT id, mensaje, ip_origen, fecha FROM mensajes ORDER BY id DESC")
    filas = cursor.fetchall()
    conexion.close()

    resultado = [dict(fila) for fila in filas]
    return jsonify(total=len(resultado), registros=resultado), 200


# ---------- READ (uno solo) ----------
@app.route("/registros/<int:registro_id>", methods=["GET"])
def obtener_registro(registro_id):
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()
    cursor.execute(
        "SELECT id, mensaje, ip_origen, fecha FROM mensajes WHERE id = ?",
        (registro_id,),
    )
    fila = cursor.fetchone()
    conexion.close()

    if fila is None:
        return jsonify(error=f"No existe un registro con id {registro_id}"), 404

    return jsonify(dict(fila)), 200


# ---------- UPDATE ----------
@app.route("/registros/<int:registro_id>", methods=["PUT"])
def actualizar_registro(registro_id):
    payload = request.get_json(silent=True, force=True)

    if payload is None or "mensaje" not in payload:
        return jsonify(error="Se esperaba un JSON con el campo 'mensaje'"), 400

    nuevo_mensaje = payload["mensaje"]

    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    cursor.execute(
        "UPDATE mensajes SET mensaje = ? WHERE id = ?",
        (nuevo_mensaje, registro_id),
    )
    conexion.commit()
    filas_afectadas = cursor.rowcount
    conexion.close()

    if filas_afectadas == 0:
        return jsonify(error=f"No existe un registro con id {registro_id}"), 404

    return jsonify(status="ok", id=registro_id, mensaje_actualizado=nuevo_mensaje), 200


# ---------- DELETE ----------
@app.route("/registros/<int:registro_id>", methods=["DELETE"])
def eliminar_registro(registro_id):
    conexion = sqlite3.connect(DB_PATH)
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM mensajes WHERE id = ?", (registro_id,))
    conexion.commit()
    filas_afectadas = cursor.rowcount
    conexion.close()

    if filas_afectadas == 0:
        return jsonify(error=f"No existe un registro con id {registro_id}"), 404

    return jsonify(status="ok", id_eliminado=registro_id), 200


if __name__ == "__main__":
    inicializar_db()
    app.run(host="0.0.0.0", port=80, debug=False)