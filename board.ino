#include <WiFi.h>
#include <WiFiUdp.h>
#include "driver/i2s.h"

// --- Configuration ---
const char* ssid = "Abhi nav";
const char* password = "00000001";
const char* udpAddress = "192.168.37.139"; // <-- IMPORTANT: Make sure this is your computer's IP

// --- Dedicated Ports ---
const int udpAudioPort = 12345;   // Port for sending audio
const int udpControlPort = 12346; // Port for commands and status

// --- Hardware Pin Assignments ---
const int redLedPin = 18;
const int greenLedPin = 22;
const int blueLedPin = 19;

// --- NEW: Audio Activity LED ---
const int audioActivityLedPin = 23;     // LED to show when sound is detected
const int AUDIO_THRESHOLD = 100;      // <-- *** TUNE THIS VALUE ***
                                      

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

// --- Status Update Timer ---
unsigned long lastStatusUpdate = 0;
const unsigned long statusUpdateInterval = 5000; // Send status every 5 seconds

// --- Current LED State ---
String currentColor = "OFF";

// --- Two UDP Objects ---
WiFiUDP udpAudio;   // For sending audio
WiFiUDP udpControl; // For commands and status

// --- Helper function to control the RGB LED ---
void setLedColor(int red, int green, int blue) {
  digitalWrite(redLedPin, red);
  digitalWrite(greenLedPin, green);
  digitalWrite(blueLedPin, blue);
}

// --- Function to update current color state ---
void updateColorState(String color) {
  currentColor = color;
  Serial.printf("[STATE] Current color updated to: %s\n", color.c_str());
}

// --- Function to send status update to server ---
void sendStatusUpdate() {
  String statusMessage = "STATUS:" + currentColor;
  // Send status over the CONTROL port
  udpControl.beginPacket(udpAddress, udpControlPort);
  udpControl.print(statusMessage);
  udpControl.endPacket();
  Serial.printf("[STATUS] Sent status update: %s\n", statusMessage.c_str());
}

void setup() {
  Serial.begin(115200);
  Serial.println("\n\n--- ESP32 Voice Streamer (Dashboard Edition) ---");

  // Setup LED pins
  pinMode(redLedPin, OUTPUT);
  pinMode(greenLedPin, OUTPUT);
  pinMode(blueLedPin, OUTPUT);
  setLedColor(LOW, LOW, LOW); // Start with all LEDs off
  Serial.println("[SETUP] RGB LED GPIOs initialized.");

  // --- NEW: Setup Audio Activity LED ---
  pinMode(audioActivityLedPin, OUTPUT);
  digitalWrite(audioActivityLedPin, LOW); // Start with it off
  Serial.println("[SETUP] Audio Activity LED initialized on GPIO 23.");

  // Connect to WiFi
  Serial.printf("[SETUP] Connecting to WiFi: %s\n", ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[SETUP] WiFi Connected!");
  Serial.print("[INFO] ESP32 IP Address: ");
  Serial.println(WiFi.localIP());

  // Initialize I2S microphone
  Serial.println("[SETUP] Configuring I2S...");
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
  Serial.println("[SETUP] I2S driver installed successfully.");

  // Start listening on the CONTROL port
  udpControl.begin(udpControlPort);
  Serial.printf("[SETUP] UDP listener for commands started on port %d.\n", udpControlPort);
  Serial.printf("[SETUP] UDP sender for audio will use port %d.\n", udpAudioPort);
  
  // Send initial status
  delay(1000);
  sendStatusUpdate();
  
  Serial.println("----------------------------------------");
  Serial.println("[INFO] System ready! Streaming audio and accepting commands...");
  Serial.println("----------------------------------------");
}

void loop() {
  // 1. Read and send audio data
  size_t bytesRead = 0;
  esp_err_t result = i2s_read(I2S_PORT, &audio_buffer, audio_buffer_size * sizeof(int16_t), &bytesRead, portMAX_DELAY);

  int average_magnitude = 0;
  int samples_read = 0;

  if (result == ESP_OK && bytesRead > 0) {
    
    // --- NEW: Robust Audio Activity Logic ---
    
    // Calculate how many 16-bit samples we actually read
    samples_read = bytesRead / sizeof(int16_t);

    uint64_t total_magnitude = 0;
    for (int i = 0; i < samples_read; i++) {
      total_magnitude += abs(audio_buffer[i]);
    }

    // Prevent division by zero
    if (samples_read > 0) {
      average_magnitude = total_magnitude / samples_read;
    }
    
    // Control the LED
    if (average_magnitude > AUDIO_THRESHOLD) {
      digitalWrite(audioActivityLedPin, HIGH); // Sound detected
    } else {
      digitalWrite(audioActivityLedPin, LOW);  // Silence
    }
    // --- END OF NEW LOGIC ---

    // Send audio over the AUDIO port (No change)
    udpAudio.beginPacket(udpAddress, udpAudioPort);
    udpAudio.write((const uint8_t*)audio_buffer, bytesRead);
    udpAudio.endPacket();
  }

  // --- CRITICAL DEBUGGING ---
  // This will print every loop.
  // We need to see these numbers.
  Serial.printf("Bytes Read: %d, \t Audio Level: %d\n", bytesRead, average_magnitude);


  // 2. Check for incoming commands from the server (uses udpControl)
  int packetSize = udpControl.parsePacket();
  if (packetSize) {
    char incomingPacket[32];
    int len = udpControl.read(incomingPacket, 31);
    if (len > 0) {
      incomingPacket[len] = 0;
    }
    Serial.printf("\n>>> [COMMAND] Received command: '%s'\n", incomingPacket);

    // Handle color commands
    if (strcmp(incomingPacket, "COLOR_RED") == 0) {
      setLedColor(HIGH, LOW, LOW);
      updateColorState("RED");
    } else if (strcmp(incomingPacket, "COLOR_GREEN") == 0) {
      setLedColor(LOW, HIGH, LOW);
      updateColorState("GREEN");
    } else if (strcmp(incomingPacket, "COLOR_BLUE") == 0) {
      setLedColor(LOW, LOW, HIGH);
      updateColorState("BLUE");
    } else if (strcmp(incomingPacket, "COLOR_WHITE") == 0) {
      setLedColor(HIGH, HIGH, HIGH);
      updateColorState("WHITE");
    } else if (strcmp(incomingPacket, "COLOR_OFF") == 0) {
      setLedColor(LOW, LOW, LOW);
      updateColorState("OFF");
    } else if (strcmp(incomingPacket, "COLOR_PURPLE") == 0) {
      setLedColor(HIGH, LOW, HIGH);
      updateColorState("PURPLE");
    } else if (strcmp(incomingPacket, "COLOR_YELLOW") == 0) {
      setLedColor(HIGH, HIGH, LOW);
      updateColorState("YELLOW");
    }
    
    // Send immediate status update after command
    sendStatusUpdate();
    
    Serial.printf(">>> [LED] Updated to: %s\n\n", currentColor.c_str());
  }

  // 3. Send periodic status updates (uses udpControl)
  unsigned long currentMillis = millis();
  if (currentMillis - lastStatusUpdate >= statusUpdateInterval) {
    sendStatusUpdate();
    lastStatusUpdate = currentMillis;
  }
}