# Voice-Controlled Home Automation (VCHA) - Setup Guide

## 🔧 Prerequisites

1. **Python 3.8+** installed
2. **Node.js 16+** installed
3. **ESP32** with code uploaded
4. **Same WiFi Network** - All devices must be connected to the same WiFi

## 📡 Network Setup

### Step 1: Find Your Computer's IP Address

**On Windows (Command Prompt):**
```cmd
ipconfig
```
Look for "IPv4 Address" under your WiFi adapter (e.g., `192.168.1.100`)

**On Mac/Linux (Terminal):**
```bash
ifconfig
# or
ip addr show
```

### Step 2: Update ESP32 Code

Open `board.ino` and update this line with your computer's IP:
```cpp
const char* udpAddress = "192.168.YOUR.IP"; // Replace with your IP
```

### Step 3: Verify WiFi Connection

Make sure:
- ✅ Your computer is connected to WiFi: `"Abhi nav"`
- ✅ ESP32 will connect to the same WiFi
- ✅ Both are on the same network

---

## 🖥️ Starting the Backend Server

### 1. Install Python Dependencies

Open **Command Prompt** or **Terminal** in the project root:

```cmd
cd c:\VCHA_IOT\server
pip install -r requirements.txt
```

**Note:** If you get PyAudio installation errors on Windows:
```cmd
pip install pipwin
pipwin install pyaudio
```

### 2. Start the Server

```cmd
python main.py
```

You should see:
```
==================================================
Voice Home Automation Server Starting...
HTTP API: http://localhost:5000
API Docs: http://localhost:5000/docs
UDP Audio Port: 12345
UDP Control Port: 12346
==================================================
```

The server is now running! ✅

---

## 🎨 Starting the Frontend Dashboard

### 1. Install Node Dependencies

Open a **new terminal/command prompt**:

```cmd
cd c:\VCHA_IOT\frontend
npm install
```

### 2. Start the React App

```cmd
npm start
```

The dashboard will automatically open at `http://localhost:3000` 🎉

---

## 🤖 Starting the ESP32

1. Upload `board.ino` to your ESP32 using Arduino IDE
2. Open Serial Monitor (115200 baud)
3. ESP32 will connect to WiFi and start streaming

You should see in Serial Monitor:
```
--- ESP32 Voice Streamer (Dashboard Edition) ---
[SETUP] WiFi Connected!
[INFO] ESP32 IP Address: 192.168.x.x
[SETUP] System ready!
```

---

## 🎯 Complete Startup Sequence

### Terminal 1 - Backend Server:
```cmd
cd c:\VCHA_IOT\server
python main.py
```

### Terminal 2 - Frontend Dashboard:
```cmd
cd c:\VCHA_IOT\frontend
npm start
```

### Arduino IDE - ESP32:
- Upload code
- Open Serial Monitor
- Verify connection

---

## ✅ Verification Checklist

- [ ] Computer and ESP32 on same WiFi
- [ ] Backend server running on port 5000
- [ ] Frontend dashboard open at localhost:3000
- [ ] ESP32 serial monitor shows "WiFi Connected"
- [ ] Dashboard shows "🟢 Connected" status
- [ ] Device appears in dashboard

---

## 🐛 Troubleshooting

### Server won't start?
- Check if port 5000 is already in use
- Verify Python dependencies are installed
- Try: `pip install --upgrade -r requirements.txt`

### Dashboard shows "Disconnected"?
- Ensure backend server is running first
- Check browser console for errors (F12)
- Verify the server URL in frontend/.env

### ESP32 not appearing in dashboard?
- Verify WiFi credentials in board.ino
- Check UDP address matches your computer's IP
- Look at ESP32 Serial Monitor for connection status
- Make sure both devices are on the same network

### PyAudio installation fails?
**Windows:**
```cmd
pip install pipwin
pipwin install pyaudio
```

**Mac:**
```bash
brew install portaudio
pip install pyaudio
```

**Linux:**
```bash
sudo apt-get install portaudio19-dev
pip install pyaudio
```

---

## 🎤 Testing Voice Commands

Try saying:
- "Turn on red light"
- "Turn on green light"
- "Turn on blue light"
- "Turn on white light"
- "Turn off light"
- "Purple light"
- "Yellow light"

---

## 📊 API Documentation

Once the server is running, visit:
- **Swagger Docs:** http://localhost:5000/docs
- **ReDoc:** http://localhost:5000/redoc

---

## 🔌 Ports Used

| Service | Port | Protocol |
|---------|------|----------|
| Backend HTTP API | 5000 | HTTP |
| Frontend Dashboard | 3000 | HTTP |
| Audio Streaming | 12345 | UDP |
| Control & Status | 12346 | UDP |

---

## 💡 Quick Commands Reference

**Start Everything:**
```cmd
# Terminal 1
cd c:\VCHA_IOT\server && python main.py

# Terminal 2
cd c:\VCHA_IOT\frontend && npm start
```

**Stop Everything:**
- Press `Ctrl+C` in both terminals
- ESP32 will keep running until you unplug it

---

Happy automating! 🏠✨
