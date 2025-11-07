import socket
import speech_recognition as sr
import pyaudio
import time
import threading
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from datetime import datetime

# (Assuming database.py and energy_simulator.py are present)
from database import Database
from energy_simulator import EnergySimulator

# --- Configuration ---
UDP_IP = "0.0.0.0"
# --- NEW: Dedicated Ports ---
UDP_AUDIO_PORT = 12345   # Port for receiving audio
UDP_CONTROL_PORT = 12346 # Port for commands and status
HTTP_PORT = 5000
SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2
CHANNELS = 1

# --- Audio Buffer Configuration ---
BUFFER_DURATION_SECONDS = 3.0
AUDIO_BYTES_PER_SECOND = SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS
TARGET_BUFFER_SIZE = int(AUDIO_BYTES_PER_SECOND * BUFFER_DURATION_SECONDS)
PACKET_TIMEOUT_SECONDS = 1.0

# --- Global State ---
client_buffers = {}
db = Database()
energy_sim = EnergySimulator()
app = FastAPI(title="Voice Home Automation API")

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WEBSOCKET] New connection. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"[WEBSOCKET] Connection closed. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# --- Pydantic Models (No changes) ---
class ControlCommand(BaseModel):
    device_id: str
    color: str

class DeviceStatus(BaseModel):
    device_id: str
    ip_address: str
    current_color: str
    status: str
    last_seen: Optional[str]

# --- PyAudio & Recognizer (No changes) ---
p = pyaudio.PyAudio()
stream = p.open(format=p.get_format_from_width(SAMPLE_WIDTH),
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                output=True)
r = sr.Recognizer()

# --- NEW: Two UDP Sockets ---
# Socket for AUDIO ONLY
sock_audio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_audio.bind((UDP_IP, UDP_AUDIO_PORT))
sock_audio.setblocking(0)

# Socket for CONTROL ONLY (Commands & Status)
sock_control = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_control.bind((UDP_IP, UDP_CONTROL_PORT))
sock_control.setblocking(0)


# --- Helper Functions ---
def play_audio_in_background(audio_data):
    """Plays the given audio bytes without blocking the main thread."""
    print("[PLAYBACK] Starting background audio playback.")
    stream.write(audio_data)
    print("[PLAYBACK] Background playback finished.")

def get_device_id_from_address(addr):
    """Convert IP address to device ID"""
    return f"esp32_{addr[0].replace('.', '_')}"

async def broadcast_update(update_type: str, data: dict):
    """Broadcast update to all WebSocket clients"""
    message = {
        "type": update_type,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast(message)

def process_audio_buffer(audio_data_bytes, client_address):
    """Processes audio with Google API while playing it back asynchronously."""
    print(f"\n[PROCESS] Processing {len(audio_data_bytes)} bytes for {client_address}...")
    print(f"[PROCESS] Audio duration: {len(audio_data_bytes) / AUDIO_BYTES_PER_SECOND:.2f} seconds")
    
    device_id = get_device_id_from_address(client_address)
    db.upsert_device(device_id, client_address[0])
    
    # Start audio playback in background
    playback_thread = threading.Thread(target=play_audio_in_background, args=(audio_data_bytes,))
    playback_thread.start()

    try:
        audio_data = sr.AudioData(audio_data_bytes, SAMPLE_RATE, SAMPLE_WIDTH)
        
        print("[PROCESS] Sending to Google for recognition...")
        text = r.recognize_google(audio_data)
        print(f"[SUCCESS] Recognized Text: '{text}'")

        # Command logic
        text_lower = text.lower()
        command_to_send = None
        color_name = None

        if "red" in text_lower:
            command_to_send = b"COLOR_RED"
            color_name = "RED"
        elif "green" in text_lower:
            command_to_send = b"COLOR_GREEN"
            color_name = "GREEN"
        elif "blue" in text_lower:
            command_to_send = b"COLOR_BLUE"
            color_name = "BLUE"
        elif "white" in text_lower or "light on" in text_lower:
            command_to_send = b"COLOR_WHITE"
            color_name = "WHITE"
        elif "light off" in text_lower or "turn off" in text_lower:
            command_to_send = b"COLOR_OFF"
            color_name = "OFF"
        elif "purple" in text_lower:
            command_to_send = b"COLOR_PURPLE"
            color_name = "PURPLE"
        elif "yellow" in text_lower:
            command_to_send = b"COLOR_YELLOW"
            color_name = "YELLOW"

        if command_to_send and color_name:
            # --- MODIFIED: Send command over the CONTROL socket ---
            # We use client_address[0] (the IP) and the NEW control port
            control_addr = (client_address[0], UDP_CONTROL_PORT)
            sock_control.sendto(command_to_send, control_addr)
            print(f"[ACTION] Sent '{command_to_send.decode()}' command to {control_addr}")
            
            # (Rest of your database/energy logic is fine)
            energy_data = energy_sim.update_device_state(device_id, color_name)
            if energy_data:
                db.add_energy_log(
                    energy_data['device_id'],
                    energy_data['power_watts'],
                    energy_data['duration_seconds'],
                    energy_data['color']
                )
            
            db.update_device_color(device_id, color_name)
            db.add_command(text, command_to_send.decode(), device_id, True)
            
            asyncio.run(broadcast_update("command_executed", {
                "device_id": device_id,
                "command_text": text,
                "color": color_name,
                "success": True
            }))
            
        else:
            print("[INFO] No command recognized in the text.")
            db.add_command(text, "NONE", device_id, False)
            
            asyncio.run(broadcast_update("command_failed", {
                "device_id": device_id,
                "command_text": text,
                "reason": "No valid color command found"
            }))

    except sr.UnknownValueError:
        print("[ERROR] Google could not understand the audio.")
        db.add_command("UNKNOWN", "ERROR", device_id, False)
    except sr.RequestError as e:
        print(f"[ERROR] Could not request results from Google; {e}")
        db.add_command("ERROR", "ERROR", device_id, False)

# --- MODIFIED: UDP Audio Processing Thread ---
def udp_audio_listener():
    """Main UDP listener loop for AUDIO (runs in separate thread)"""
    print("[UDP_AUDIO] Audio listener thread started")
    print(f"[UDP_AUDIO] Listening on port {UDP_AUDIO_PORT}")
    
    while True:
        try:
            # --- MODIFIED: Use sock_audio ---
            data, addr = sock_audio.recvfrom(2048)
            
            # (Buffer logic is the same, but now only handles audio)
            if addr not in client_buffers:
                client_buffers[addr] = {'buffer': b'', 'last_packet_time': time.time()}
                device_id = get_device_id_from_address(addr)
                db.upsert_device(device_id, addr[0])
                print(f"[INFO] New client connected: {addr}. Creating buffer.")
                
            client_buffers[addr]['buffer'] += data
            client_buffers[addr]['last_packet_time'] = time.time()
            
            if len(client_buffers[addr]['buffer']) >= TARGET_BUFFER_SIZE:
                print(f"[INFO] Client {addr} buffer reached target size. Processing...")
                process_audio_buffer(client_buffers[addr]['buffer'], addr)
                client_buffers[addr]['buffer'] = b''
                
        except BlockingIOError:
            pass

        # (Timeout logic is the same)
        for addr in list(client_buffers.keys()):
            time_since_last_packet = time.time() - client_buffers[addr]['last_packet_time']
            if time_since_last_packet > PACKET_TIMEOUT_SECONDS:
                if len(client_buffers[addr]['buffer']) > AUDIO_BYTES_PER_SECOND * 0.5:
                    print(f"[INFO] Client {addr} timed out. Processing collected audio...")
                    process_audio_buffer(client_buffers[addr]['buffer'], addr)
                else:
                    print(f"[INFO] Client {addr} timed out with insufficient audio. Discarding buffer.")
                del client_buffers[addr]
                print(f"[INFO] Client {addr} buffer cleared after timeout.")
                
        time.sleep(0.01)

# --- NEW: UDP Status Processing Thread ---
def udp_status_listener():
    """Main UDP listener loop for STATUS messages (runs in separate thread)"""
    print("[UDP_STATUS] Status listener thread started")
    print(f"[UDP_STATUS] Listening on port {UDP_CONTROL_PORT}")
    
    while True:
        try:
            # --- MODIFIED: Use sock_control ---
            data, addr = sock_control.recvfrom(128) # Status messages are small
            
            message = data.decode('utf-8')
            
            if message.startswith("STATUS:"):
                color = message.split(":", 1)[1]
                device_id = get_device_id_from_address(addr)
                
                print(f"[STATUS] Received status from {device_id}: {color}")
                
                # Update database
                db.update_device_color(device_id, color)
                
                # Broadcast update to dashboard
                asyncio.run(broadcast_update("status_update", {
                    "device_id": device_id,
                    "color": color
                }))
            
        except BlockingIOError:
            pass
        except Exception as e:
            print(f"[UDP_STATUS] Error: {e}")
            
        time.sleep(0.01)

# --- REST API Endpoints ---

@app.get("/api/devices")
async def get_devices():
    devices = db.get_all_devices()
    return {"devices": devices}

@app.get("/api/devices/{device_id}")
async def get_device(device_id: str):
    device = db.get_device(device_id)
    if device:
        return device
    return {"error": "Device not found"}

@app.post("/api/control")
async def control_device(command: ControlCommand):
    """Manually send command to device"""
    device = db.get_device(command.device_id)
    if not device:
        return {"success": False, "error": "Device not found"}
    
    color_commands = {
        "RED": b"COLOR_RED", "GREEN": b"COLOR_GREEN", "BLUE": b"COLOR_BLUE",
        "WHITE": b"COLOR_WHITE", "OFF": b"COLOR_OFF", "PURPLE": b"COLOR_PURPLE",
        "YELLOW": b"COLOR_YELLOW"
    }
    
    command_bytes = color_commands.get(command.color.upper())
    if not command_bytes:
        return {"success": False, "error": "Invalid color"}
    
    # Get IP from device ID
    if device['ip_address'].startswith('esp32_'):
        ip_address = device['ip_address'].replace('esp32_', '').replace('_', '.')
    else:
        ip_address = device['ip_address']
    
    # --- MODIFIED: Send command over CONTROL port ---
    control_addr = (ip_address, UDP_CONTROL_PORT)
    sock_control.sendto(command_bytes, control_addr)
    
    # (Rest of your database/energy logic is fine)
    energy_data = energy_sim.update_device_state(command.device_id, command.color.upper())
    if energy_data:
        db.add_energy_log(
            energy_data['device_id'],
            energy_data['power_watts'],
            energy_data['duration_seconds'],
            energy_data['color']
        )
    
    db.update_device_color(command.device_id, command.color.upper())
    db.add_command(f"Manual: {command.color}", command_bytes.decode(), command.device_id, True)
    
    await broadcast_update("command_executed", {
        "device_id": command.device_id,
        "command_text": f"Manual: {command.color}",
        "color": command.color.upper(),
        "success": True
    })
    
    return {"success": True, "device_id": command.device_id, "color": command.color}

# (Other API endpoints are fine)
@app.get("/api/commands")
async def get_commands(limit: int = 50):
    commands = db.get_recent_commands(limit)
    return {"commands": commands}

@app.get("/api/energy/stats")
async def get_energy_stats(device_id: Optional[str] = None, hours: int = 24):
    stats = db.get_energy_stats(device_id, hours)
    return stats

@app.get("/api/energy/timeline")
async def get_energy_timeline(device_id: Optional[str] = None, hours: int = 24):
    timeline = db.get_energy_timeline(device_id, hours)
    return {"timeline": timeline}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
async def root():
    return {"message": "Voice Home Automation API", "docs": "/docs"}

# --- Startup ---
@app.on_event("startup")
async def startup_event():
    """Start UDP listener threads on app startup"""
    print("="*50)
    print("Voice Home Automation Server Starting...")
    print(f"HTTP API: http://localhost:{HTTP_PORT}")
    print(f"API Docs: http://localhost:{HTTP_PORT}/docs")
    print(f"UDP Audio Port: {UDP_AUDIO_PORT}")
    print(f"UDP Control Port: {UDP_CONTROL_PORT}")
    print("="*50)
    
    # --- MODIFIED: Start BOTH listener threads ---
    udp_audio_thread = threading.Thread(target=udp_audio_listener, daemon=True)
    udp_audio_thread.start()
    
    udp_status_thread = threading.Thread(target=udp_status_listener, daemon=True)
    udp_status_thread.start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=HTTP_PORT)