# Servidor Lab Flask + ESP32 (IoT)

Pipeline IoT extremo a extremo desplegado en AWS: un servidor Flask corriendo en
una instancia EC2 recibe datos vía HTTP (GET/POST), y un cliente ESP32 se
conecta por WiFi para transmitir información en tiempo real. Proyecto
desarrollado en el marco del curso de laboratorio de IoT.

> **Nota sobre la IP pública:** este proyecto corre sobre un AWS Academy Lab.
> Cada vez que la sesión del lab expira y se reinicia, la instancia EC2
> conserva sus datos pero **cambia de IP pública**. Verifica la IP actual en
> la consola de EC2 (Instances) antes de conectarte por SSH o de probar los
> endpoints en Postman.

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
- **Servidor (EC2 + Flask):** expone rutas para ingesta y consulta de datos
  (ver "Pruebas realizadas" más abajo para el detalle según la etapa de
  almacenamiento activa).
- **Persistencia (systemd):** el servidor corre como servicio del sistema
  (servidor.service), configurado con reinicio automático, para que sobreviva
  al cierre de la sesión SSH o a un reinicio de la instancia.

## Estructura del repositorio

```
server/
  server.py             -> servidor Flask ACTUAL (refleja la ultima etapa desplegada)
  servidor.service       -> unit file de systemd para correr el servidor como servicio
esp32/
  esp32_cliente.ino      -> cliente ESP32: conecta WiFi y dispara GET/POST al servidor
  esp32_scan_wifi.ino    -> utilidad de diagnostico: escanea redes WiFi visibles
docs/
  diagrama.png            -> diagrama de arquitectura del pipeline
  evidencia_logs.txt      -> logs de las primeras corridas (servidor sin persistencia)
  sqlite/
    server_sqlite.py      -> copia congelada del server.py con CRUD sobre SQLite
    evidencia_sqlite.txt  -> logs de las pruebas CRUD sobre SQLite
  mariadb/                -> (pendiente) copia congelada + evidencia de la etapa MariaDB
  rds/                    -> (pendiente) copia congelada + evidencia de la etapa RDS
  s3/                     -> (pendiente) copia congelada + evidencia de la etapa S3
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
   instancia EC2 (ver nota al inicio de este README).
6. Compilar y subir. Abrir el Serial Monitor a 115200 baud para ver el
   resultado de cada GET/POST.

Nota: si el ESP32 no logra conectarse al WiFi, usar
esp32/esp32_scan_wifi.ino para listar las redes visibles y confirmar el
nombre exacto (SSID) — es sensible a mayúsculas/minúsculas.

## Pruebas realizadas

### Etapa 1 — Servidor sin persistencia (solo impresión en consola)
- Postman: GET http://IP_PUBLICA/ responde 200 OK, body hola mundo.
  POST http://IP_PUBLICA/data con body raw JSON
  {"mensaje": "prueba desde postman"} responde 200 OK.
- Hardware (ESP32) vía hotspot móvil: mismo flujo GET/POST confirmado
  end-to-end. Evidencia en docs/evidencia_logs.txt.

### Etapa 2 — Almacenamiento local con SQLite (CRUD completo)
- POST /data (Create): guarda el mensaje recibido en datos.db.
- GET /registros (Read, todos) y GET /registros/<id> (Read, uno solo).
- PUT /registros/<id> (Update): actualiza el mensaje de un registro.
- DELETE /registros/<id> (Delete): elimina un registro.
- Todas las operaciones probadas en Postman con resultado 200 OK.
  Evidencia y código congelado en docs/sqlite/.

## Problemas encontrados y solución

| Problema | Causa | Solución |
|---|---|---|
| pip3 install flask con la flag break-system-packages fallaba | Versión antigua de pip que no soporta esa flag | Instalar sin la flag: pip3 install flask |
| Servicio systemd fallaba con Permission denied | El puerto 80 requiere privilegios y el servicio corría con User=ec2-user | Cambiar a User=root en servidor.service |
| esptool no lograba conectar al subir el sketch (No serial data received) | El ESP32 no entraba en modo de flasheo automáticamente | Mantener presionado el botón BOOT durante la subida |
| ESP32 nunca conectaba al hotspot del iPhone | Hotspot apagado / SSID mal escrito (sensible a mayúsculas: iPhone, no Iphone/iphone) | Activar "Maximizar compatibilidad" en el hotspot, verificar el SSID exacto con esp32_scan_wifi.ino |
| SyntaxError al reiniciar el servicio tras editar server.py | Un caracter de mas (~) quedo pegado al final del archivo | Revisar y limpiar el archivo con nano antes de guardar |
| SSH timeout al reconectar un dia despues | La sesion de AWS Academy Lab expiro y la instancia se reinicio con una IP publica nueva | Reiniciar el Lab desde AWS Academy, tomar la IP nueva desde la consola EC2 y reconectar |

## Próximos pasos

Completar las estrategias de persistencia restantes, siguiendo el mismo
patrón que SQLite (congelar código y evidencia en su propia subcarpeta de
docs/, y actualizar server/server.py con la versión vigente):

1. ~~Archivo simple (SQLite): script CRUD sobre un archivo .db local.~~ ✅ Completado
2. Motor local (MariaDB): base de datos SQL corriendo en la misma EC2.
3. Motor externo (RDS MySQL): base de datos administrada por AWS.
4. Almacenamiento de objetos (S3): guardar los datos usando boto3.

## Seguridad y limpieza de recursos

Al finalizar las 4 pruebas y presentarlas, se deben destruir los recursos
creados en AWS para evitar exposición innecesaria: terminar instancias RDS,
vaciar y eliminar buckets S3, y detener/terminar la instancia EC2 si ya no
se necesita.