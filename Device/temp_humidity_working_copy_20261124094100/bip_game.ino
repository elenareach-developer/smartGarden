
#define JOY_X 2
#define JOY_Y 4
#define JOY_SW 5

void setup() {
  Serial.begin(115200);
  pinMode(JOY_SW, INPUT_PULLUP);

  Serial.println("Joystick test started!");
}

void loop() {
  int x = analogRead(JOY_X);
  int y = analogRead(JOY_Y);
  int button = digitalRead(JOY_SW);

  Serial.print("X: ");
  Serial.print(x);

  Serial.print(" | Y: ");
  Serial.print(y);

  Serial.print(" | BUTTON: ");
  Serial.println(button);

  delay(200);
}
