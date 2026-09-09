#include <WiFi.h>

void setup() {
  Serial.begin(115200);
  delay(1000);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  delay(100);
  Serial.println("Escaneando redes WiFi...");
}

void loop() {
  int n = WiFi.scanNetworks();
  Serial.println("Escaneo completo.");

  if (n == 0) {
    Serial.println("No se encontraron redes.");
  } else {
    Serial.print(n);
    Serial.println(" redes encontradas:");
    for (int i = 0; i < n; ++i) {
      Serial.print(i + 1);
      Serial.print(": ");
      Serial.print(WiFi.SSID(i));
      Serial.print("  (Señal: ");
      Serial.print(WiFi.RSSI(i));
      Serial.print(" dBm)  Canal: ");
      Serial.println(WiFi.channel(i));
    }
  }

  Serial.println("");
  delay(5000);
}