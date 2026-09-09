\# Servidor Lab Flask + ESP32 (IoT)



Pipeline IoT extremo a extremo desplegado en AWS: un servidor Flask corriendo en

una instancia EC2 recibe datos vía HTTP (GET/POST), y un cliente ESP32 se

conecta por WiFi para transmitir información en tiempo real. Proyecto

desarrollado en el marco del curso de laboratorio de IoT.



\## Arquitectura



```

\[ESP32] --WiFi--> \[Internet] --HTTP:80--> \[AWS EC2 / Security Group]

&#x20;                                                 |

&#x20;                                         \[Flask server.py]

&#x20;                                                 |

&#x20;                                         (systemd: servidor.service)

&#x20;                                                 |

&#x20;                                        stdout / journalctl -u servidor -f

```



\- \*\*Cliente (ESP32):\*\* se conecta a una red WiFi y realiza peticiones HTTP

&#x20; GET y POST periódicas contra el servidor.

\- \*\*Servidor (EC2 + Flask):\*\* expone dos rutas:

&#x20; - `GET /` → responde `hola mundo` (health check simple).

&#x20; - `POST /data` → recibe un JSON, lo imprime en consola y responde

&#x20;   `{"status": "ok", "received": {...}}`.

\- \*\*Persistencia (systemd):\*\* el servidor corre como servicio del sistema

&#x20; (`servidor.service`), configurado con `Restart=always`, para que sobreviva

&#x20; al cierre de la sesión SSH o a un reinicio de la instancia.



\## Estructura del repositorio



```

server/

&#x20; server.py           -> servidor Flask (GET / y POST /data)

&#x20; servidor.service     -> unit file de systemd para correr el servidor como servicio

esp32/

&#x20; esp32\_cliente.ino    -> cliente ESP32: conecta WiFi y dispara GET/POST al servidor

&#x20; esp32\_scan\_wifi.ino  -> utilidad de diagnóstico: escanea redes WiFi visibles

docs/

&#x20; (diagramas, capturas y notas adicionales)

```



\## Despliegue del servidor (AWS EC2)



1\. Crear una instancia EC2 (Amazon Linux 2023, t3.micro).

2\. Configurar el Security Group: abrir el puerto 80 (HTTP, origen 0.0.0.0/0)

&#x20;  y el puerto 22 (SSH, restringido a la IP propia).

3\. Conectarse por SSH y preparar el entorno:

&#x20;  ```bash

&#x20;  sudo yum install -y python3 python3-pip

&#x20;  pip3 install flask

&#x20;  ```

4\. Copiar `server/server.py` a la instancia (por ejemplo en

&#x20;  `/home/ec2-user/servidor/server.py`).

5\. Instalar como servicio systemd:

&#x20;  ```bash

&#x20;  sudo cp servidor.service /etc/systemd/system/servidor.service

&#x20;  sudo systemctl daemon-reload

&#x20;  sudo systemctl enable servidor

&#x20;  sudo systemctl start servidor

&#x20;  sudo systemctl status servidor

&#x20;  ```

6\. Ver logs en vivo:

&#x20;  ```bash

&#x20;  sudo journalctl -u servidor -f

&#x20;  ```



\## Cliente ESP32 (Arduino IDE)



1\. Instalar Arduino IDE 2.x.

2\. Agregar el Boards Manager URL de Espressif:

&#x20;  `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package\_esp32\_index.json`

3\. Instalar el paquete \*\*esp32 by Espressif Systems\*\* desde el Boards Manager.

4\. Seleccionar la placa \*\*ESP32 Dev Module\*\* y el puerto COM correspondiente.

5\. Abrir `esp32/esp32\_cliente.ino`, editar `ssid` y `password` con la red WiFi

&#x20;  real, y `servidor\_get` / `servidor\_post` con la IP pública actual de la

&#x20;  instancia EC2.

6\. Compilar y subir. Abrir el Serial Monitor a 115200 baud para ver el

&#x20;  resultado de cada GET/POST.



> \*\*Nota:\*\* si el ESP32 no logra conectarse al WiFi, usar

> `esp32/esp32\_scan\_wifi.ino` para listar las redes visibles y confirmar el

> nombre exacto (SSID) — es sensible a mayúsculas/minúsculas.



\## Pruebas realizadas



\- \*\*Postman:\*\*

&#x20; - `GET http://<IP\_PUBLICA>/` → `200 OK`, body `hola mundo`.

&#x20; - `POST http://<IP\_PUBLICA>/data` con body raw JSON

&#x20;   `{"mensaje": "prueba desde postman"}` → `200 OK`, respuesta con

&#x20;   `status: ok` y el mensaje reflejado.

\- \*\*Hardware (ESP32) vía hotspot móvil:\*\* mismo flujo GET/POST confirmado

&#x20; end-to-end, con el mensaje recibido y registrado en los logs del servidor

&#x20; (`journalctl -u servidor -f`).



\## Problemas encontrados y solución



| Problema | Causa | Solución |

|---|---|---|

| `pip3 install flask --break-system-packages` fallaba | Versión antigua de pip que no soporta esa flag | Instalar sin la flag: `pip3 install flask` |

| Servicio systemd fallaba con `Permission denied` | El puerto 80 requiere privilegios y el servicio corría con `User=ec2-user` | Cambiar a `User=root` en `servidor.service` |

| `esptool` no lograba conectar al subir el sketch (`No serial data received`) | El ESP32 no entraba en modo de flasheo automáticamente | Mantener presionado el botón \*\*BOOT\*\* durante la subida |

| ESP32 nunca conectaba al hotspot del iPhone | Hotspot apagado / SSID mal escrito (case-sensitive: `iPhone`, no `Iphone`/`iphone`) | Activar "Maximizar compatibilidad" en el hotspot, verificar el SSID exacto con `esp32\_scan\_wifi.ino` |



\## Próximos pasos



Explorar distintas estrategias de persistencia de los datos recibidos en

`/data`, documentadas en subcarpetas futuras de este repo:



1\. \*\*Archivo simple (SQLite):\*\* script CRUD sobre un archivo `.db` local.

2\. \*\*Motor local (MariaDB):\*\* base de datos SQL corriendo en la misma EC2.

3\. \*\*Motor externo (RDS MySQL):\*\* base de datos administrada por AWS.

4\. \*\*Almacenamiento de objetos (S3):\*\* guardar los datos usando `boto3`.

