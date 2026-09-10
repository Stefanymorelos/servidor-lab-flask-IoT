# Servidor Lab Flask + ESP32 (IoT)

Pipeline IoT extremo a extremo desplegado en AWS: un servidor Flask corriendo en
una instancia EC2 recibe datos vía HTTP (GET/POST), y un cliente ESP32 se
conecta por WiFi para transmitir información en tiempo real. El proyecto
explora 4 estrategias distintas de persistencia sobre esos datos. Desarrollado
en el marco del curso de laboratorio de IoT.

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
                          -----------------------------------------------
                          |            |            |                   |
                       SQLite      MariaDB         RDS                  S3
                      (archivo    (motor local   (motor externo    (almacenamiento
                       local)      en la EC2)     administrado)     de objetos)
```

Ver también `docs/diagrama.png` para el diagrama visual del flujo general.

- **Cliente (ESP32):** se conecta a una red WiFi y realiza peticiones HTTP
  GET y POST periódicas contra el servidor.
- **Servidor (EC2 + Flask):** expone rutas CRUD para ingesta y consulta de
  datos: `POST /data`, `GET /registros`, `GET /registros/<id>`,
  `PUT /registros/<id>`, `DELETE /registros/<id>`.
- **Persistencia (systemd):** el servidor corre como servicio del sistema
  (servidor.service), configurado con reinicio automático.

## Estructura del repositorio

```
server/
  server.py             -> servidor Flask ACTUAL (version S3, la ultima etapa)
  servidor.service       -> unit file de systemd
esp32/
  esp32_cliente.ino      -> cliente ESP32: conecta WiFi y dispara GET/POST al servidor
  esp32_scan_wifi.ino    -> utilidad de diagnostico: escanea redes WiFi visibles
docs/
  diagrama.png            -> diagrama de arquitectura general
  evidencia_logs.txt      -> logs de las primeras corridas (servidor sin persistencia)
  sqlite/
    server_sqlite.py      -> copia congelada: CRUD sobre SQLite
    evidencia_sqlite.txt  -> logs de las pruebas CRUD sobre SQLite
  mariadb/
    server_mariadb.py     -> copia congelada: CRUD sobre MariaDB (motor local en la EC2)
    evidencia_mariadb.txt -> logs de las pruebas CRUD sobre MariaDB
  rds/
    server_rds.py         -> copia congelada: CRUD sobre RDS MySQL (contrasena oculta)
    evidencia_rds.txt     -> logs de las pruebas CRUD sobre RDS
  s3/
    server_s3.py           -> copia congelada: CRUD sobre S3 (boto3)
    evidencia_s3.txt       -> logs de las pruebas CRUD sobre S3
    bucket_s3.png           -> captura del objeto JSON guardado en el bucket
```

## Despliegue del servidor (AWS EC2)

1. Crear una instancia EC2 (Amazon Linux 2023, t3.micro).
2. Configurar el Security Group: abrir el puerto 80 (HTTP, origen 0.0.0.0/0)
   y el puerto 22 (SSH, restringido a la IP propia).
3. Conectarse por SSH y preparar el entorno:

```bash
sudo yum install -y python3 python3-pip
pip3 install flask
sudo pip3 install flask mysql-connector-python boto3
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
6. Compilar y subir. Abrir el Serial Monitor a 115200 baud.

Nota: si el ESP32 no logra conectarse al WiFi, usar
esp32/esp32_scan_wifi.ino para listar las redes visibles y confirmar el
nombre exacto (SSID) — es sensible a mayúsculas/minúsculas.

## Las 4 estrategias de almacenamiento

### 1. SQLite (archivo local)
CRUD completo sobre un archivo `datos.db` dentro de la propia instancia EC2,
usando el módulo `sqlite3` de Python. Sin dependencias externas.
Código y evidencia: `docs/sqlite/`.

### 2. MariaDB (motor local)
CRUD completo sobre una base de datos MySQL/MariaDB instalada en la misma
instancia EC2 (`sudo yum install mariadb105-server`), usando
`mysql-connector-python`. Usuario dedicado `app_user` con permisos acotados
a la base `lab_iot`.
Código y evidencia: `docs/mariadb/`.

### 3. RDS MySQL (motor externo administrado)
CRUD completo sobre una instancia RDS MySQL separada de la EC2. Configurada
con **Public access = No** y un Security Group que solo permite conexiones
al puerto 3306 desde el Security Group de la propia instancia EC2 — nunca
desde internet.
Código y evidencia: `docs/rds/` (contraseña reemplazada por un placeholder
en el código congelado, por seguridad).

### 4. S3 (almacenamiento de objetos)
Cada mensaje se guarda como un objeto JSON individual (`mensajes/<id>.json`)
en un bucket S3 privado (**Block all public access** activado), usando
`boto3`. La autenticación se resuelve con un IAM role (`LabInstanceProfile`)
asignado a la instancia EC2 — sin credenciales de AWS hardcodeadas en el
código.
Código y evidencia: `docs/s3/`.

## Pruebas realizadas (resumen)

Para cada una de las 4 etapas se probó el ciclo completo en Postman:
- `POST /data` (Create)
- `GET /registros` y `GET /registros/<id>` (Read)
- `PUT /registros/<id>` (Update)
- `DELETE /registros/<id>` (Delete)

Todas las operaciones respondieron `200 OK` (o `404` para ids inexistentes,
como comportamiento esperado). Además, se validó el flujo end-to-end con
hardware real (ESP32 vía hotspot móvil) contra la etapa sin persistencia.
Evidencia detallada en cada subcarpeta de `docs/`.

## Problemas encontrados y solución

| Problema | Causa | Solución |
|---|---|---|
| pip3 install flask con --break-system-packages fallaba | Versión antigua de pip | Instalar sin la flag |
| systemd fallaba con Permission denied (puerto 80) | Servicio corría como ec2-user | Cambiar a User=root en servidor.service |
| esptool no conectaba al subir el sketch | ESP32 no entraba en modo flasheo | Mantener BOOT presionado durante la subida |
| ESP32 no conectaba al hotspot del iPhone | SSID mal escrito (case-sensitive) | Verificar con esp32_scan_wifi.ino, activar "Maximizar compatibilidad" |
| SyntaxError al reiniciar tras editar server.py | Caracter de más (~) al final del archivo | Revisar con nano antes de guardar |
| SSH timeout al reconectar un día después | Sesión de AWS Academy Lab expiró, IP nueva | Reiniciar el Lab, tomar la IP nueva desde la consola EC2 |
| ModuleNotFoundError (mysql / boto3) tras pip install | La librería se instaló solo para ec2-user, no para root (quien corre el servicio) | Reinstalar con sudo pip3 install ... |
| Unknown database 'lab_iot' en RDS | No se definió "Initial database name" al crear la instancia RDS | Crear la base manualmente: mysql -h <endpoint> -u admin -p, luego CREATE DATABASE lab_iot; |

## Seguridad y limpieza de recursos

Siguiendo la recomendación del curso, al finalizar la presentación del
proyecto se deben destruir los recursos creados en AWS:

1. **RDS:** RDS > Databases > database-1 > Actions > Delete (sin snapshot
   final si no se necesita conservar backup).
2. **S3:** vaciar el bucket (Empty) y luego eliminarlo (Delete bucket).
3. **EC2:** Instance state > Terminate instance (borra también los datos de
   SQLite y MariaDB locales; sacar evidencia antes si hace falta).

Mientras el proyecto sigue en desarrollo o pendiente de mostrar, los
recursos permanecen activos pero configurados con el menor acceso posible:
RDS sin acceso público, S3 con "Block all public access", y credenciales de
RDS excluidas del código versionado en Git.