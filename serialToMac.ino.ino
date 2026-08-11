void setup() {
  Serial.begin(9600); // Set the same baud rate in Python
}

void loop() {
  if (Serial.available() > 0) {
    // Read the incoming string until a newline character
    String incoming = Serial.readStringUntil('\n');
    
    // Print a response back to Python
    Serial.print("Mac sent: ");
    Serial.println(incoming);
  }
}
