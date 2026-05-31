#include <WiFi.h>
#include <WebServer.h>
#include <PubSubClient.h>
#include <time.h> // Required for real-world time tracking

// --- Network & MQTT Configuration ---
const char* ssid = "<Replace this with your own Wi-Fi name";
const char* password = "<Replace this with your own Wi-Fi password>";

IPAddress mqtt_broker(0, 0, 0, 0); // Replace this with your device's verified working IP structure!
const int mqtt_port = 1883;
const char* mqtt_topic_pub = "esp32/temperature";
const char* mqtt_topic_sub = "esp32/commands";

// --- Time Zone Configuration ---
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 28800;      
const int daylightOffset_sec = 0;

WiFiClient espClient;
PubSubClient mqttClient(espClient);
WebServer server(80);

// --- Global Tracking State ---
unsigned long lastMqttPublish = 0;
unsigned long lastReconnectAttempt = 0;

String bootTime = "Synchronizing...";
String lastMqttConnectTime = "Never";
bool wasMqttConnected = false;

// ==========================================
// 1. Time Helper Function
// ==========================================
String getFormattedTime() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    return "Time Sync Error";
  }
  char timeStringBuff[50];
  // Formats as: YYYY-MM-DD HH:MM:SS
  strftime(timeStringBuff, sizeof(timeStringBuff), "%Y-%m-%d %H:%M:%S", &timeinfo);
  return String(timeStringBuff);
}

// ==========================================
// 2. MQTT Callback & Tracking Logic
// ==========================================
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("MQTT message arrived [");
  Serial.print(topic);
  Serial.print("] Payload: ");
  for (unsigned int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();
}

void reconnectMqtt() {
  unsigned long now = millis();
  if (now - lastReconnectAttempt > 5000) {
    lastReconnectAttempt = now;
    Serial.print("Attempting MQTT connection...");
    String clientId = "ESP32-Swagger-" + String(random(0xffff), HEX);
    
    // --- THE MAGIC HAPPENS HERE ---
    // mqttClient.connect(clientID, willTopic, willQoS, willRetain, willMessage)
    // We set retain to 'true' so anyone who connects later instantly sees the last known status.
    if (mqttClient.connect(clientId.c_str(), "esp32/status", 0, true, "Offline")) {
      Serial.println("connected");
      
      // The moment we successfully connect, we override the Will and announce we are Online!
      // We also retain this message so the dashboard knows we are live.
      mqttClient.publish("esp32/status", "Online", true);
      
      mqttClient.subscribe(mqtt_topic_sub);
      
      // Log the exact time this connection succeeded
      lastMqttConnectTime = getFormattedTime();
    } else {
      Serial.print("failed, state: ");
      Serial.println(mqttClient.state());
    }
  }
}

// ==========================================
// 3. HTTP Route Handlers
// ==========================================
void handleApiTemperature() {
  String json = "{\"temperature\": " + String(currentTemperature) + "}";
  server.send(200, "application/json", json);
}

// NEW: Endpoint to check system times and telemetry states
void handleApiStatus() {
  unsigned long totalSeconds = millis() / 1000;
  unsigned long days = totalSeconds / 86400;
  unsigned long hours = (totalSeconds % 86400) / 3600;
  unsigned long minutes = (totalSeconds % 3600) / 60;
  unsigned long seconds = totalSeconds % 60;

  String uptimeString = String(days) + "d " + String(hours) + "h " + String(minutes) + "m " + String(seconds) + "s";

  String json = "{";
  json += "\"system_status\": \"Online\",";
  json += "\"current_time\": \"" + getFormattedTime() + "\",";
  json += "\"boot_time\": \"" + bootTime + "\",";
  json += "\"uptime\": \"" + uptimeString + "\",";
  json += "\"mqtt_status\": \"" + String(mqttClient.connected() ? "Connected" : "Disconnected") + "\",";
  json += "\"last_mqtt_handshake\": \"" + lastMqttConnectTime + "\"";
  json += "}";
  
  server.send(200, "application/json", json);
}

void handleApiPublish() {
  if (server.hasArg("plain")) {
    String payload = server.arg("plain");
    if (mqttClient.connected()) {
      mqttClient.publish("esp32/custom_publish", payload.c_str());
      server.send(200, "application/json", "{\"status\": \"Published to MQTT\"}");
    } else {
      server.send(503, "application/json", "{\"error\": \"MQTT not connected\"}");
    }
  } else {
    server.send(400, "application/json", "{\"error\": \"No payload provided\"}");
  }
}

// ==========================================
// 4. Updated Swagger Specification
// ==========================================
const char* swaggerJSON = R"rawliteral(
{
  "openapi": "3.0.0",
  "info": {
    "title": "ESP32 Time & Status Monitor",
    "version": "1.1.0",
    "description": "Exposing internal health metrics and tracking connection histories."
  },
  "paths": {
    "/status": {
      "get": {
        "summary": "Get device health, clock synchronization, and connection uptimes",
        "responses": { "200": { "description": "Success" } }
      }
    },
    "/temperature": {
      "get": {
        "summary": "Read current temperature via HTTP",
        "responses": { "200": { "description": "Success" } }
      }
    },
    "/publish": {
      "post": {
        "summary": "Publish a custom message to MQTT",
        "requestBody": {
          "required": true,
          "content": {
            "text/plain": { "schema": { "type": "string", "example": "Hello!" } }
          }
        },
        "responses": { "200": { "description": "Success" } }
      }
    }
  }
}
)rawliteral";

const char* swaggerHTML = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>ESP32 Diagnostics</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.0.0/swagger-ui.css" />
  <style>
    /* Styling to make the banner look sharp and professional */
    #offline-banner {
      display: none; 
      background-color: #ff3b30; 
      color: white; 
      text-align: center; 
      padding: 12px; 
      position: fixed; 
      top: 0; 
      left: 0;
      width: 100%; 
      z-index: 9999; 
      font-family: sans-serif; 
      font-weight: bold;
      box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    /* We will use this class to push the Swagger UI down so the banner doesn't cover the top bar */
    body.offline { padding-top: 45px; } 
  </style>
</head>
<body>
  <div id="offline-banner">⚠️ ESP32 CONNECTION LOST - DEVICE OFFLINE ⚠️</div>
  <div id="swagger-ui"></div>
  
  <script src="https://unpkg.com/swagger-ui-dist@5.0.0/swagger-ui-bundle.js" crossorigin></script>
  <script>
    // 1. Initialize the Swagger UI
    window.onload = () => {
      window.ui = SwaggerUIBundle({ url: '/swagger.json', dom_id: '#swagger-ui' });
    };

    // 2. The Live Watchdog Script
    const banner = document.getElementById('offline-banner');
    const originalBannerText = banner.innerText; 
    
    // NEW: The state tracker! This remembers if we are already offline.
    let isOffline = false; 
    
    setInterval(() => {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000);

      fetch('/status', { 
        method: 'GET', 
        cache: 'no-store', 
        signal: controller.signal
      })
      .then(response => {
        clearTimeout(timeoutId);
        if(response.ok) {
          // If the ESP32 is alive, and we were previously offline: RESET everything!
          if (isOffline) {
            banner.innerText = originalBannerText; // Put the default text back
            banner.style.display = 'none';
            document.body.classList.remove('offline');
            isOffline = false; // Reset the tracker
          }
        } else {
          throw new Error('Bad Server Response');
        }
      })
      .catch(() => {
        // We are offline! 
        // Only grab the time and update the text if this is the FIRST time we noticed it.
        if (!isOffline) {
          const currentTime = new Date().toLocaleTimeString();
          banner.innerText = `⚠️ ESP32 CONNECTION LOST at ${currentTime} ⚠️`;
          banner.style.display = 'block';
          document.body.classList.add('offline');
          
          isOffline = true; // Lock the state so it doesn't update the time again!
        }
      });
    }, 4000);
  </script>
</body>
</html>
)rawliteral";

// ==========================================
// Setup and Main Loop
// ==========================================
void setup() {
  Serial.begin(115200);

  // 1. Connect Wi-Fi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\nWiFi connected.");

  // 2. Initialize and Sync Real Time via NTP
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  Serial.print("Synchronizing internal clock with NTP");
  
  // Wait until time is gathered successfully
  struct tm timeinfo;
  while (!getLocalTime(&timeinfo)) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nTime Synchronized!");
  bootTime = getFormattedTime(); // Mark down exactly when the program setup completed

  // 3. Setup MQTT
  mqttClient.setServer(mqtt_broker, mqtt_port);
  mqttClient.setCallback(mqttCallback);

  // 4. Define HTTP Routes
  server.on("/status", HTTP_GET, handleApiStatus);
  server.on("/temperature", HTTP_GET, handleApiTemperature);
  server.on("/publish", HTTP_POST, handleApiPublish);
  server.on("/swagger.json", HTTP_GET, []() { server.send(200, "application/json", swaggerJSON); });
  server.on("/docs", HTTP_GET, []() { server.send(200, "text/html", swaggerHTML); });

  server.begin();
  Serial.println("System Ready. View diagnostics at http://" + WiFi.localIP().toString() + "/docs");
}

void loop() {
  server.handleClient();

  if (!mqttClient.connected()) {
    reconnectMqtt();
  }
  mqttClient.loop();

  // Handle telemetry streaming
  unsigned long now = millis();
  if (now - lastMqttPublish > 5000) {
    lastMqttPublish = now;
    currentTemperature += 0.05;
    if(currentTemperature > 30.0) currentTemperature = 25.0; 
    
    if (mqttClient.connected()) {
      char tempString[8];
      dtostrf(currentTemperature, 1, 2, tempString);
      mqttClient.publish(mqtt_topic_pub, tempString);
    }
  }
}
