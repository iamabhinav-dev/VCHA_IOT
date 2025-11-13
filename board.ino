#include <WiFi.h>
#include <WiFiUdp.h>
#include "driver/i2s.h"

// --- Configuration ---
const char* ssid = "Abhi nav";
const char* password = "00000001";
const char* udpAddress = "192.168.9.139";

// --- Dedicated Ports ---
const int udpAudioPort = 12345;
const int udpControlPort = 12346;

// --- Hardware Pin Assignments ---
// LED 1 (4-pin RGB)
const int redLedPin_1 = 18;
const int greenLedPin_1 = 22;
const int blueLedPin_1 = 19;

// NEW: LED 2 (2-pin LED)
const int led2Pin = 25; // Connect long leg (+) to resistor, then to this pin. Short leg (-) to GND.

const int audioActivityLedPin = 23;
const int buttonPin = 13;

// --- Wake Word Detection Settings ---
const int SILENCE_THRESHOLD = 100;
const int SPEECH_THRESHOLD = 500;
const int WAKE_PATTERN_MIN_MS = 60;
const int WAKE_PATTERN_MAX_MS = 400;
const int SILENCE_AFTER_WAKE_MS = 200;
const int RECORDING_DURATION_MS = 3000;

// --- I2S Microphone Pins ---
#define I2S_WS 2
#define I2S_SD 4
#define I2S_SCK 15
#define I2S_PORT I2S_NUM_0

// --- Audio Settings ---
#define I2S_SAMPLE_RATE 16000
#define I2S_SAMPLE_BITS I2S_BITS_PER_SAMPLE_16BIT
#define I2S_CHANNEL_FORMAT I2S_CHANNEL_FMT_ONLY_LEFT

// --- Audio Buffer ---
const int audio_buffer_size = 1024;
int16_t audio_buffer[audio_buffer_size];

// --- Wake Detection State ---
enum WakeState {
  LISTENING,
  WAKE_DETECTED,
  RECORDING
};

WakeState currentState = LISTENING;
unsigned long speechStartTime = 0;
unsigned long silenceStartTime = 0;
unsigned long recordingStartTime = 0;

// --- Status Update Timer ---
unsigned long lastStatusUpdate = 0;
const unsigned long statusUpdateInterval = 5000;

// --- Current LED State ---
String currentColorLed1 = "OFF"; // Will store color
String currentColorLed2 = "OFF"; // Will store "ON" or "OFF"

// --- UDP Objects ---
WiFiUDP udpAudio;
WiFiUDP udpControl;

// --- Helper Functions ---

// Function for RGB LED 1
void setLed1Color(int red, int green, int blue) {
  digitalWrite(redLedPin_1, red);
  digitalWrite(greenLedPin_1, green);
  digitalWrite(blueLedPin_1, blue);
}

void updateLed1ColorState(String color) {
  currentColorLed1 = color;
}

// NEW: Function for 2-pin LED 2
void setLed2State(int state, String stateName) {
  digitalWrite(led2Pin, state);
  currentColorLed2 = stateName;
}

void sendStatusUpdate() {
  String statusMessage = "STATUS:LED1=" + currentColorLed1 + ",LED2=" + currentColorLed2;
  udpControl.beginPacket(udpAddress, udpControlPort);
  udpControl.print(statusMessage);
  udpControl.endPacket();
  Serial.printf("[STATUS] Sent status update: %s\n", statusMessage.c_str());
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n\n╔════════════════════════════════════════════╗");
  Serial.println("║   ESP32 Voice Control (1x RGB, 1x Simple)  ║");
  Serial.println("╚════════════════════════════════════════════╝\n");

  // Setup LED pins
  pinMode(redLedPin_1, OUTPUT);   // LED 1 (RGB)
  pinMode(greenLedPin_1, OUTPUT);
  pinMode(blueLedPin_1, OUTPUT);
  
  pinMode(led2Pin, OUTPUT); // NEW: Pin for LED 2 (Simple)

  pinMode(audioActivityLedPin, OUTPUT);
  pinMode(buttonPin, INPUT_PULLUP);
  
  // Set both LEDs to OFF
  setLed1Color(LOW, LOW, LOW);
  setLed2State(LOW, "OFF"); // NEW
  
  digitalWrite(audioActivityLedPin, LOW); // Listening LED OFF
  Serial.println("[✓] GPIO pins initialized");

  // Connect to WiFi
  Serial.printf("[WIFI] Connecting to: %s", ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" Connected!");
  Serial.printf("[INFO] ESP32 IP: %s\n", WiFi.localIP().toString().c_str());

  // Initialize I2S
  Serial.println("[I2S] Configuring microphone...");
  i2s_config_t i2s_config = {
      .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
      .sample_rate = I2S_SAMPLE_RATE,
      .bits_per_sample = I2S_SAMPLE_BITS,
      .channel_format = I2S_CHANNEL_FORMAT,
      .communication_format = I2S_COMM_FORMAT_STAND_I2S,
      .intr_alloc_flags = 0,
      .dma_buf_count = 8,
      .dma_buf_len = 64,
      .use_apll = false
  };
  i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
  
  const i2s_pin_config_t pin_config = {
      .bck_io_num = I2S_SCK,
      .ws_io_num = I2S_WS,
      .data_out_num = -1,
      .data_in_num = I2S_SD
  };
  i2s_set_pin(I2S_PORT, &pin_config);
  Serial.println("[✓] I2S initialized");

  // Start UDP
  udpControl.begin(udpControlPort);
  Serial.printf("[UDP] Listening on port %d\n", udpControlPort);
  
  delay(1000);
  sendStatusUpdate();
  
  Serial.println("\n════════════════════════════════════════════");
  Serial.println("  🎤 Make a short sound OR Press Button!");
  Serial.println("  💡 LED OFF = Listening | LED ON = Recording");
  Serial.println("════════════════════════════════════════════\n");
}

void loop() {
  // ═══════════════════════════════════════════════════════════
  // 1. BUTTON CHECK
  // ═══════════════════════════════════════════════════════════
  static bool wasButtonPressed = false;
  
  if (digitalRead(buttonPin) == LOW) {
    if (!wasButtonPressed) {
      Serial.println("\n[BUTTON] ✓✓✓ PRESSED! Starting manual recording...");
      currentState = RECORDING;
      recordingStartTime = millis();
      digitalWrite(audioActivityLedPin, HIGH);
      wasButtonPressed = true;
    }
  } else if (wasButtonPressed) {
    Serial.println("[BUTTON] Released");
    wasButtonPressed = false;
  }

  // ═══════════════════════════════════════════════════════════
  // 2. AUDIO PROCESSING (State Machine)
  // ═══════════════════════════════════════════════════════════
  size_t bytesRead = 0;
  esp_err_t result = i2s_read(I2S_PORT, &audio_buffer, audio_buffer_size * sizeof(int16_t), 
                                &bytesRead, portMAX_DELAY);

  if (result == ESP_OK && bytesRead > 0) {
    int samples_read = bytesRead / sizeof(int16_t);
    uint64_t total_magnitude = 0;
    for (int i = 0; i < samples_read; i++) {
      total_magnitude += abs(audio_buffer[i]);
    }
    int average_magnitude = (samples_read > 0) ? (total_magnitude / samples_read) : 0;
    
    switch (currentState) {
      case LISTENING:
        digitalWrite(audioActivityLedPin, LOW); // LED OFF
        if (average_magnitude > SPEECH_THRESHOLD) {
          if (speechStartTime == 0) {
            speechStartTime = millis();
            Serial.println("[WAKE] Detecting sound pattern...");
          }
        } else {
          if (speechStartTime > 0) {
            unsigned long speechDuration = millis() - speechStartTime;
            Serial.printf("[WAKE] Pattern duration: %lu ms\n", speechDuration);
            
            if (speechDuration >= WAKE_PATTERN_MIN_MS && 
                speechDuration <= WAKE_PATTERN_MAX_MS) {
              Serial.println("\n🔥🔥🔥 WAKE PATTERN DETECTED! 🔥🔥🔥\n");
              currentState = WAKE_DETECTED;
              silenceStartTime = millis();
            } else {
              Serial.println("[WAKE] Pattern too short or too long, ignoring.");
            }
            speechStartTime = 0;
          }
        }
        break;
      
      case WAKE_DETECTED:
        digitalWrite(audioActivityLedPin, LOW); // LED OFF
        if (millis() - silenceStartTime >= SILENCE_AFTER_WAKE_MS) {
          Serial.println("[RECORDING] Starting 3-second recording...");
          currentState = RECORDING;
          recordingStartTime = millis();
        }
        break;
      
      case RECORDING:
        digitalWrite(audioActivityLedPin, HIGH); // LED ON
        
        udpAudio.beginPacket(udpAddress, udpAudioPort);
        udpAudio.write((const uint8_t*)audio_buffer, bytesRead);
        udpAudio.endPacket();
        
        if (millis() - recordingStartTime >= RECORDING_DURATION_MS) {
          Serial.println("\n[RECORDING] Finished. Listening for wake pattern again...");
          currentState = LISTENING;
          speechStartTime = 0;
          silenceStartTime = 0;
        }
        break;
    }
  }

  // ═══════════════════════════════════════════════════════════
  // 3. HANDLE INCOMING COMMANDS (*** MODIFIED LOGIC ***)
  // ═══════════════════════════════════════════════════════════
  int packetSize = udpControl.parsePacket();
  if (packetSize) {
    char incomingPacket[32];
    int len = udpControl.read(incomingPacket, 31);
    if (len > 0) {
      incomingPacket[len] = 0;
    }
    Serial.printf("\n>>> [COMMAND] Received: '%s'\n", incomingPacket);

    // --- LED 1 Commands (RGB) ---
    if (strcmp(incomingPacket, "LED1_RED") == 0) {
      setLed1Color(HIGH, LOW, LOW);
      updateLed1ColorState("RED");
    } else if (strcmp(incomingPacket, "LED1_GREEN") == 0) {
      setLed1Color(LOW, HIGH, LOW);
      updateLed1ColorState("GREEN");
    } else if (strcmp(incomingPacket, "LED1_BLUE") == 0) {
      setLed1Color(LOW, LOW, HIGH);
      updateLed1ColorState("BLUE");
    } else if (strcmp(incomingPacket, "LED1_WHITE") == 0 || strcmp(incomingPacket, "LED1_ON") == 0) {
      setLed1Color(HIGH, HIGH, HIGH);
      updateLed1ColorState("WHITE");
    } else if (strcmp(incomingPacket, "LED1_PURPLE") == 0) {
      setLed1Color(HIGH, LOW, HIGH);
      updateLed1ColorState("PURPLE");
    } else if (strcmp(incomingPacket, "LED1_YELLOW") == 0) {
      setLed1Color(HIGH, HIGH, LOW);
      updateLed1ColorState("YELLOW");
    } else if (strcmp(incomingPacket, "LED1_OFF") == 0) {
      setLed1Color(LOW, LOW, LOW);
      updateLed1ColorState("OFF");
    }

    // --- LED 2 Commands (2-pin ON/OFF) ---
    else if (strcmp(incomingPacket, "LED2_OFF") == 0) {
      setLed2State(LOW, "OFF");
    }
    // Any other "LED2" command (ON, RED, GREEN, etc.) just turns it ON
    else if (strncmp(incomingPacket, "LED2_ON", 5) == 0) {
      setLed2State(HIGH, "ON");
    }

    // --- ALL (Both) Commands ---
    else if (strcmp(incomingPacket, "ALL_OFF") == 0) {
      setLed1Color(LOW, LOW, LOW);
      updateLed1ColorState("OFF");
      setLed2State(LOW, "OFF");
    }
    // Any other "ALL" command sets LED 1's color and turns LED 2 ON
    else if (strcmp(incomingPacket, "ALL_RED") == 0) {
      setLed1Color(HIGH, LOW, LOW);
      updateLed1ColorState("RED");
      setLed2State(HIGH, "ON");
    } else if (strcmp(incomingPacket, "ALL_GREEN") == 0) {
      setLed1Color(LOW, HIGH, LOW);
      updateLed1ColorState("GREEN");
      setLed2State(HIGH, "ON");
    } else if (strcmp(incomingPacket, "ALL_BLUE") == 0) {
      setLed1Color(LOW, LOW, HIGH);
      updateLed1ColorState("BLUE");
      setLed2State(HIGH, "ON");
    } else if (strcmp(incomingPacket, "ALL_WHITE") == 0 || strcmp(incomingPacket, "ALL_ON") == 0) {
      setLed1Color(HIGH, HIGH, HIGH);
      updateLed1ColorState("WHITE");
      setLed2State(HIGH, "ON");
    } else if (strcmp(incomingPacket, "ALL_PURPLE") == 0) {
      setLed1Color(HIGH, LOW, HIGH);
      updateLed1ColorState("PURPLE");
      setLed2State(HIGH, "ON");
    } else if (strcmp(incomingPacket, "ALL_YELLOW") == 0) {
      setLed1Color(HIGH, HIGH, LOW);
      updateLed1ColorState("YELLOW");
      setLed2State(HIGH, "ON");
    }
    
    // Send status update after command
    sendStatusUpdate();
    Serial.printf(">>> [LED] Updated. LED1: %s, LED2: %s\n\n", currentColorLed1.c_str(), currentColorLed2.c_str());
  }

  // ═══════════════════════════════════════════════════════════
  // 4. PERIODIC STATUS UPDATES
  // ═══════════════════════════════════════════════════════════
  unsigned long currentMillis = millis();
  if (currentMillis - lastStatusUpdate >= statusUpdateInterval) {
    sendStatusUpdate();
    lastStatusUpdate = currentMillis;
  }
}