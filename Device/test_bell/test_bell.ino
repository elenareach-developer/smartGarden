
#define BUZZER 21

void setup() {
  pinMode(BUZZER, OUTPUT);
}

void loop() {
  // High tone
  tone(BUZZER, 1000);
  delay(500);

  // Silence
  noTone(BUZZER);
  delay(500);

  // Low tone
  tone(BUZZER, 500);
  delay(500);

  // Silence
  noTone(BUZZER);
  delay(500);
}
