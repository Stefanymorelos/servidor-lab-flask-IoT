#include <WiFi.h>
#include <HTTPClient.h>

// ---------- CONFIGURACION ----------
const char* ssid     = "iPhone de Stefany";
const char* password = "TU_CONTRASENA_AQUI";

// IP publica de tu instancia EC2 (la misma que usaste en Postman)
const char* servidor_get  = "http://100.58.219.41/";
const char* servidor_post = "http://100.58.219.41/data";
// ------------------------------------

void conectarWiFi() {
  Serial.print("Conectando a WiFi: ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi conectado!");
  Serial.print("IP del ESP32: ");
  Serial.println(WiFi.localIP());
}

void hacerGET() {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin(servidor_get);

  int codigoRespuesta = http.GET();

  if (codigoRespuesta > 0) {
    String respuesta = http.getString();
    Serial.print("GET -> Codigo: ");
    Serial.println(codigoRespuesta);
    Serial.print("GET -> Respuesta: ");
    Serial.println(respuesta);
  } else {
    Serial.print("Error en GET: ");
    Serial.println(http.errorToString(codigoRespuesta));
  }

  http.end();
}

void hacerPOST() {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin(servidor_post);
  http.addHeader("Content-Type", "application/json");

  String jsonBody = "{\"mensaje\": \"prueba desde ESP32\"}";

  int codigoRespuesta = http.POST(jsonBody);

  if (codigoRespuesta > 0) {
    String respuesta = http.getString();
    Serial.print("POST -> Codigo: ");
    Serial.println(codigoRespuesta);
    Serial.print("POST -> Respuesta: ");
    Serial.println(respuesta);
  } else {
    Serial.print("Error en POST: ");
    Serial.println(http.errorToString(codigoRespuesta));
  }

  http.end();
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  conectarWiFi();
}

void loop() {
  hacerGET();
  delay(2000);

  hacerPOST();
  delay(8000);
}