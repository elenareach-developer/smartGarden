// Smart Orchid: ESP32 + DHT11 → отправка температуры и влажности в приложение по Wi-Fi.
// Основано на temp_humidity_working_copy (DHT11 на пине 4).
// Нужны библиотеки: "DHT sensor library" (Adafruit) и "Adafruit Unified Sensor".
// Настройки Wi-Fi и сервера — в secrets.h (см. secrets.example.h).

#include <WiFi.h>
#include <HTTPClient.h>
#include "DHT.h"
#include "secrets.h"

#define DHT_PIN  4
#define DHT_TYPE DHT11

const unsigned long READ_INTERVAL_MS = 5000;    // DHT11 нельзя опрашивать чаще ~1 раза в секунду
const unsigned long SEND_INTERVAL_MS = 60000;   // раз в минуту отправляем среднее за минуту

DHT dht(DHT_PIN, DHT_TYPE);

float sumT = 0, sumH = 0;
int samples = 0;
unsigned long lastRead = 0, lastSend = 0;

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.print("Подключение к Wi-Fi ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Wi-Fi подключён, IP ESP32: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("Wi-Fi не подключился — попробую снова позже");
  }
}

String readingJson(const char* metric, float value) {
  return String("{\"plant_id\":") + PLANT_ID +
         ",\"metric\":\"" + metric + "\",\"value\":" + String(value, 1) +
         ",\"source\":\"iot\",\"hardware_id\":\"" + HARDWARE_ID + "\"}";
}

bool sendToApp(float temperature, float humidity) {
  connectWiFi();
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  http.begin(String(SERVER_URL) + "/api/sensors/readings");
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(8000);

  String body = String("{\"readings\":[") +
                readingJson("temperature", temperature) + "," +
                readingJson("air_humidity", humidity) + "]}";
  int code = http.POST(body);
  String answer = http.getString();
  http.end();

  if (code == 201) {
    Serial.println("✓ Отправлено в Smart Orchid");
    return true;
  }
  Serial.print("✗ Ошибка отправки, HTTP ");
  Serial.println(code);   // -1: сервер недоступен (IP? --host 0.0.0.0? брандмауэр?)
  Serial.println(answer); // 404: датчик не зарегистрирован; 422: ошибка данных
  return false;
}

void setup() {
  Serial.begin(9600);
  dht.begin();
  Serial.println("DHT11 Sensor Started!");
  connectWiFi();
}

void loop() {
  unsigned long now = millis();

  if (now - lastRead >= READ_INTERVAL_MS) {
    lastRead = now;
    float humidity = dht.readHumidity();
    float temperature = dht.readTemperature();
    if (isnan(humidity) || isnan(temperature)) {
      Serial.println("Sensor reading failed!");
    } else {
      // тот же формат, что в исходном скетче — его понимает и USB-мост
      Serial.print("Humidity = ");    Serial.print(humidity);    Serial.println("%");
      Serial.print("Temperature = "); Serial.print(temperature); Serial.println(" C");
      Serial.println("----------------");
      sumT += temperature;
      sumH += humidity;
      samples++;
    }
  }

  if (now - lastSend >= SEND_INTERVAL_MS && samples > 0) {
    lastSend = now;
    sendToApp(sumT / samples, sumH / samples);
    sumT = sumH = 0;
    samples = 0;
  }
}
