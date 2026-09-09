# Servidor Lab Flask + ESP32 (IoT)

Pipeline IoT extremo a extremo desplegado en AWS: un servidor Flask corriendo en
una instancia EC2 recibe datos vía HTTP (GET/POST), y un cliente ESP32 se
conecta por WiFi para transmitir información en tiempo real. Proyecto
desarrollado en el marco del curso de laboratorio de IoT.

## Arquitectura

```
[ESP32] --WiFi--> [Internet] --HTTP:80--> [AWS EC2 / Security Group]
                                                  |
                                          [Flask server.py]
                                                  |
                                          (systemd: servidor.service)
                                                  |
                                         stdout / journalctl -u servidor -f
```

Ver también `docs/diagrama.png` para el diagrama visual del flujo completo.

- **Cliente (ESP32):** se conecta a una red WiFi y realiza peticiones HTTP
  GET y POST periódicas contra el servidor.
- **Servidor (EC2 + Flask):** expone dos rutas:
  - `GET /` responde `hola mundo` (health check simple).
  - `POST /data` recibe un JSON, lo imprime en consola y responde
    con status ok y el mensaje recibido.
- **Persistencia (systemd):** el servidor corre como servicio del sistema
  (servidor.service), configurado con reinicio automático, para que sobreviva
  al cierre de la sesión SSH o a un reinicio de la instancia.

## Estructura del repositorio

```
server/
  server.py           -> servidor Flask (GET / y POST /data)
  servidor.service     -> unit file de systemd para correr el servidor como servicio
esp32/
  esp32_cliente.ino    -> cliente ESP32: conecta WiFi y dispara GET/POST al servidor
  esp32_scan_wifi.ino  -> utilidad de diagnóstico: escanea redes WiFi visibles
docs/
  diagrama.png          -> diagrama de arquitectura del pipeline
  evidencia_logs.txt    -> logs reales de las corridas exitosas del servidor
```

## Despliegue del servidor (AWS EC2)

1. Crear una instancia EC2 (Amazon Linux 2023, t3.micro).
2. Configurar el Security Group: abrir el puerto 80 (HTTP, origen 0.0.0.0/0)
   y el puerto 22 (SSH, restringido a la IP propia).
3. Conectarse por SSH y preparar el entorno:

```bash
sudo yum install -y python3 python3-pip
pip3 install flask
```

4. Copiar server/server.py a la instancia (por ejemplo en
   /home/ec2-user/servidor/server.py).
5. Instalar como servicio systemd:

```bash
sudo cp servidor.service /etc/systemd/system/servidor.service
sudo systemctl daemon-reload
sudo systemctl enable servidor
sudo systemctl start servidor
sudo systemctl status servidor
```

6. Ver logs en vivo:

```bash
sudo journalctl -u servidor -f
```

## Cliente ESP32 (Arduino IDE)

1. Instalar Arduino IDE 2.x.
2. Agregar el Boards Manager URL de Espressif:
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
3. Instalar el paquete esp32 by Espressif Systems desde el Boards Manager.
4. Seleccionar la placa ESP32 Dev Module y el puerto COM correspondiente.
5. Abrir esp32/esp32_cliente.ino, editar ssid y password con la red WiFi
   real, y servidor_get / servidor_post con la IP pública actual de la
   instancia EC2.
6. Compilar y subir. Abrir el Serial Monitor a 115200 baud para ver el
   resultado de cada GET/POST.

Nota: si el ESP32 no logra conectarse al WiFi, usar
esp32/esp32_scan_wifi.ino para listar las redes visibles y confirmar el
nombre exacto (SSID) — es sensible a mayúsculas/minúsculas.

## Pruebas realizadas

- Postman:
  - GET http://IP_PUBLICA/ responde 200 OK, body hola mundo.
  - POST http://IP_PUBLICA/data con body raw JSON
    {"mensaje": "prueba desde postman"} responde 200 OK, con
    status ok y el mensaje reflejado.
- Hardware (ESP32) vía hotspot móvil: mismo flujo GET/POST confirmado
  end-to-end, con el mensaje recibido y registrado en los logs del servidor
  (journalctl -u servidor -f). Evidencia completa en docs/evidencia_logs.txt.

## Problemas encontrados y solución

| Problema | Causa | Solución |
|---|---|---|
| pip3 install flask con la flag break-system-packages fallaba | Versión antigua de pip que no soporta esa flag | Instalar sin la flag: pip3 install flask |
| Servicio systemd fallaba con Permission denied | El puerto 80 requiere privilegios y el servicio corría con User=ec2-user | Cambiar a User=root en servidor.service |
| esptool no lograba conectar al subir el sketch (No serial data received) | El ESP32 no entraba en modo de flasheo automáticamente | Mantener presionado el botón BOOT durante la subida |
| ESP32 nunca conectaba al hotspot del iPhone | Hotspot apagado / SSID mal escrito (sensible a mayúsculas: iPhone, no Iphone/iphone) | Activar "Maximizar compatibilidad" en el hotspot, verificar el SSID exacto con esp32_scan_wifi.ino |

## Próximos pasos

Explorar distintas estrategias de persistencia de los datos recibidos en
/data, documentadas en subcarpetas futuras de este repo:

1. Archivo simple (SQLite): script CRUD sobre un archivo .db local.
2. Motor local (MariaDB): base de datos SQL corriendo en la misma EC2.
3. Motor externo (RDS MySQL): base de datos administrada por AWS.
4. Almacenamiento de objetos (S3): guardar los datos usando boto3.