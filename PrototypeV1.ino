#include <WiFiNINA.h>
#include <PubSubClient.h>

//***********Connectivity***************************
#define ssid "Raja Zareef"
#define pass "matstopa"

const char* mqttServer = "mqtt.thingsboard.cloud"; // ThingsBoard MQTT broker URL
const char* deviceId = "level13"; // mqtt client ID

WiFiClient wifiClient;
PubSubClient client(wifiClient);

//**************Ultrasonic sensor*******************
//sensor 1 to check waste level
const int sensor1TrigPin = 2;    // Ultrasonic sensor 1 trigger pin
const int sensor1EchoPin = 3;    // Ultrasonic sensor 1 echo pin
//sensor 2 to check whether bin is opened or closed
const int sensor2TrigPin = 4;    // Ultrasonic sensor 2 trigger pin
const int sensor2EchoPin = 5;    // Ultrasonic sensor 2 echo pin
const int thresholdDistance = 5; // Threshold distance for sensor 2 in centimeters
float duration, distance, level;

void setup() {
  Serial.begin(9600);
  connectWiFi(); //connect to hotspot
  client.setServer(mqttServer, 1883); // MQTT broker port
  pinMode(sensor1TrigPin, OUTPUT);  // Set sensor 1 trigger pin as output
  pinMode(sensor1EchoPin, INPUT);   // Set sensor 1 echo pin as input
  pinMode(sensor2TrigPin, OUTPUT);  // Set sensor 2 trigger pin as output
  pinMode(sensor2EchoPin, INPUT);   // Set sensor 2 echo pin as input
}

void loop() {
  //connect to server first
  if (!client.connected()) {
    reconnect();
  }
  getAndSendLevel();
  delay(30000); //delay 30 seconds before sending the next telemetry
}

//Wifi connection
void connectWiFi() {
  WiFi.begin(ssid, pass);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("Connected to Wi-Fi");
}

//MQTT connection
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect(deviceId)) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void getAndSendLevel() {
  if (IsBinClosed()) {
    // Sensor 2 detected a distance less than the threshold, indicating the bin is closed
    Serial.println("Bin is closed.");

    // Delay to avoid interference from sensor 2
    delay(1000);

    // Proceed to measure distance from sensor 1 for waste level
    digitalWrite(sensor1TrigPin, LOW);
    delayMicroseconds(2);
    digitalWrite(sensor1TrigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(sensor1TrigPin, LOW);
    duration = pulseIn(sensor1EchoPin, HIGH);
    distance = duration * 0.034 / 2;
    level = 35 - distance;

    if(level<=0){
      level = 0;
    }

    // Print the measured distance from sensor 1 to the Serial Monitor
    Serial.print("Sensor 1 Distance: ");
    Serial.print(level);
    Serial.println(" cm");

    // Check if any reads failed and exit early (to try again).
    if (isnan(distance)) {
      Serial.println("Failed to read from Level sensor!");
      return;
    }

    // Publish telemetry data to ThingsBoard using MQTT
    String payload = "{\"Level\": " + String(level, 2) + "}";
    char buffer[payload.length() + 1]; // Add space for null terminator
    payload.toCharArray(buffer, payload.length() + 1); // Convert String to C-style string
    client.publish("v1/devices/me/telemetry", buffer); // Publish the C-style string payload
    Serial.println(buffer);

  } else {
    Serial.println("Bin is open. Please wait for it to close");
  }
    
}

bool IsBinClosed() {
  // Measure distance from sensor 2 to determine whether bin is closed or opened
  digitalWrite(sensor2TrigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(sensor2TrigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(sensor2TrigPin, LOW);
  duration = pulseIn(sensor2EchoPin, HIGH);
  distance = duration * 0.034 / 2;
  Serial.print("Sensor 2 Distance: ");
  Serial.print(distance);
  Serial.println(" cm");
  return (distance <= thresholdDistance);
}