
#define LED_BUILTIN 2

// the setup function runs once when you press reset or power the board
void setup() {
  // initialize digital pin LED_BUILTIN as an output.
  pinMode(LED_BUILTIN, OUTPUT);
// pinMode(KY_003_PIN, INPUT_PULLUP);
}

// the loop function runs over and over again forever
void loop() {
  digitalWrite(LED_BUILTIN, HIGH);  // change state of the LED by setting the pin to the HIGH voltage level
  delay(5000);                      // wait for a second
  digitalWrite(LED_BUILTIN, LOW);   // change state of the LED by setting the pin to the LOW voltage level
  delay(5000);       
  
 // if (digitalRead(KY_003_PIN) == LOW)  {
 //     digitalWrite(LED_BUILTIN, HIGH);
//  } else {
//      digitalWrite(LED_BUILTIN, LOW); 
//  }
      
 //  delay(100);     // wait for a second
}