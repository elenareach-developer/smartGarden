
#include "DHT.h"

// Pin connected to DHT11 data
#define DHpin 4

// Select sensor type
#define DHTTYPE DHT11

DHT dht(DHpin, DHTTYPE);

void setup() {
  Serial.begin(9600);
  dht.begin();

  Serial.println("DHT11 Sensor Started!");
}

void loop() {

  // Read humidity
  float humidity = dht.readHumidity();

  // Read temperature
  float temperature = dht.readTemperature();

  // Check if readings are valid
  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Sensor reading failed!");
    delay(2000);
    return;
  }

  Serial.print("Humidity = ");
  Serial.print(humidity);
  Serial.println("%");

  Serial.print("Temperature = ");
  Serial.print(temperature);
  Serial.println(" C");

  Serial.println("----------------");

  delay(2000);
}
