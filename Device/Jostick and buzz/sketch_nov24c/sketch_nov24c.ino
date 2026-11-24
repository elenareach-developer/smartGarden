
// ESP32 + Joystick + Passive Buzzer
// Left  = Low tone
// Right = High tone
// Up    = Fast beeps
// Press = Short melody

#define JOY_X 5
#define JOY_Y 4
#define JOY_SW 2
#define BUZZER_PIN 21

int melody[] = {
  262, 330, 392, 523, 392, 523
};

int noteDuration = 180;

void setup() {
  Serial.begin(115200);

  pinMode(JOY_X, INPUT);
  pinMode(JOY_Y, INPUT);
  pinMode(JOY_SW, INPUT_PULLUP);

  pinMode(BUZZER_PIN, OUTPUT);

  Serial.println("Joystick Music Instrument Ready!");
}

void playMelody() {
  for (int i = 0; i < 6; i++) {
    if (digitalRead(JOY_SW) == HIGH) {
      tone(BUZZER_PIN, melody[i]);
      delay(noteDuration);
      noTone(BUZZER_PIN);
      delay(50);
    }
  }
}

void loop() {
  int x = analogRead(JOY_X);
  int y = analogRead(JOY_Y);
  int button = digitalRead(JOY_SW);

  Serial.print("X: ");
  Serial.print(x);
  Serial.print(" Y: ");
  Serial.println(y);

  // Press joystick: play melody
  if (button == LOW) {
    noTone(BUZZER_PIN);
    playMelody();
  }

  // Move left: low tone
  else if (x < 1200) {
    tone(BUZZER_PIN, 200);
  }

  // Move right: high tone
  else if (x > 2800) {
    tone(BUZZER_PIN, 1000);
  }

  // Move up: fast beeps
  else if (y > 2800) {
    tone(BUZZER_PIN, 700);
    delay(100);
    noTone(BUZZER_PIN);
    delay(100);
  }

  // Center: silence
  else {
    noTone(BUZZER_PIN);
  }

  delay(20);
}
