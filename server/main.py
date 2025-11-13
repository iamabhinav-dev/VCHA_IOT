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

# Import updated helper files
from database import Database
from energy_simulator import EnergySimulator

# --- Configuration ---
UDP_IP = "0.0.0.0"
UDP_AUDIO_PORT = 12345
UDP_CONTROL_PORT = 12346
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

# --- Pydantic Models ---
class ControlCommand(BaseModel):
    device_id: str
    led_id: str  # "LED1", "LED2", or "ALL"
    color: str

class DeviceStatus(BaseModel):
    device_id: str
    ip_address: str
    status: str
    last_seen: Optional[str]
    current_color_led1: Optional[str]
    current_color_led2: Optional[str]

# --- PyAudio & Recognizer ---
p = pyaudio.PyAudio()
stream = p.open(format=p.get_format_from_width(SAMPLE_WIDTH),
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                output=True)
r = sr.Recognizer()

# --- UDP Sockets ---
sock_audio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_audio.bind((UDP_IP, UDP_AUDIO_PORT))
sock_audio.setblocking(0)

sock_control = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_control.bind((UDP_IP, UDP_CONTROL_PORT))
sock_control.setblocking(0)

# --- Helper Functions ---
def play_audio_in_background(audio_data):
    print("[PLAYBACK] Starting background audio playback.")
    stream.write(audio_data)
    print("[PLAYBACK] Background playback finished.")

def get_device_id_from_address(addr):
    return f"esp32_{addr[0].replace('.', '_')}"

async def broadcast_update(update_type: str, data: dict):
    message = {
        "type": update_type,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast(message)

# --- FIXED: process_audio_buffer ---
def process_audio_buffer(audio_data_bytes, client_address):
    """Processes audio and handles correct ON/OFF logic for LED 1"""
    print(f"\n[PROCESS] Processing {len(audio_data_bytes)} bytes for {client_address}...")
    
    device_id = get_device_id_from_address(client_address)
    db.upsert_device(device_id, client_address[0])
    
    playback_thread = threading.Thread(target=play_audio_in_background, args=(audio_data_bytes,))
    playback_thread.start()

    try:
        audio_data = sr.AudioData(audio_data_bytes, SAMPLE_RATE, SAMPLE_WIDTH)
        print("[PROCESS] Sending to Google for recognition...")
        text = r.recognize_google(audio_data)
        print(f"[SUCCESS] Recognized Text: '{text}'")

        # --- Normalize text to fix "one"/"two"/"to" ambiguity ---
        text_normalized = text.lower()
        text_normalized = text_normalized.replace(" light one", " light 1")
        text_normalized = text_normalized.replace(" led one", " led 1")
        text_normalized = text_normalized.replace(" light two", " light 2")
        text_normalized = text_normalized.replace(" led two", " led 2")
        text_normalized = text_normalized.replace(" light to", " light 2")
        text_normalized = text_normalized.replace(" led to", " led 2")

        words = text_normalized.split()
        
        command_to_send = None
        color_command_part = None 
        led_id = "ALL"
        led_command_part = "ALL_"

        # --- Detect LED ID by looking for "one", "two", "to", "1", "2" in the words ---
        if "one" in words or "1" in words:
            led_id = "LED1"
            led_command_part = "LED1_"
        elif "two" in words or "to" in words or "2" in words:
            led_id = "LED2"
            led_command_part = "LED2_"
        elif "all" in words or "both" in words:
            led_id = "ALL"
            led_command_part = "ALL_"

        # --- Find color/action from normalized text and words ---
        if "off" in words:
            color_command_part = "OFF"
        elif "on" in words:
            color_command_part = "ON"
        elif "red" in words:
            color_command_part = "RED"
        elif "green" in words:
            color_command_part = "GREEN"
        elif "blue" in words:
            color_command_part = "BLUE"
        elif "white" in words:
            color_command_part = "WHITE"
        elif "purple" in words:
            color_command_part = "PURPLE"
        elif "yellow" in words:
            color_command_part = "YELLOW"
        
        if color_command_part:
            # Determine the actual command to send to ESP32 and logical state for DB/Energy Sim
            color_for_led1_logic = None
            color_for_led2_logic = None
            color_for_esp = color_command_part

            if led_id == "LED1":
                # LED1 supports full RGB colors
                color_for_led1_logic = color_command_part
                color_for_esp = color_command_part
            elif led_id == "LED2":
                # LED2 only supports ON/OFF
                if color_command_part == "OFF":
                    color_for_esp = "OFF"
                    color_for_led2_logic = "OFF"
                else:
                    color_for_esp = "ON"
                    color_for_led2_logic = "ON"
            elif led_id == "ALL":
                # For ALL: LED1 gets the color, LED2 gets ON/OFF
                if color_command_part == "OFF":
                    color_for_led1_logic = "OFF"
                    color_for_led2_logic = "OFF"
                    color_for_esp = "OFF"
                elif color_command_part == "ON":
                    color_for_led1_logic = "WHITE"
                    color_for_led2_logic = "ON"
                    color_for_esp = "WHITE"
                else:
                    color_for_led1_logic = color_command_part
                    color_for_led2_logic = "ON"
                    color_for_esp = color_command_part
            
            command_str = f"{led_command_part}{color_for_esp}"
            command_to_send = command_str.encode('utf-8')

            # Send command to ESP32
            control_addr = (client_address[0], UDP_CONTROL_PORT)
            sock_control.sendto(command_to_send, control_addr)
            print(f"[ACTION] Sent '{command_str}' command to {control_addr}")
            
            # Update DB and Energy Sim
            if color_for_led1_logic:
                db.update_device_color(device_id, "LED1", color_for_led1_logic)
                energy_logs_1 = energy_sim.update_device_state(device_id, "LED1", color_for_led1_logic)
                for log in energy_logs_1:
                    db.add_energy_log(log['device_id'], log['power_watts'], log['duration_seconds'], log['color'])

            if color_for_led2_logic:
                db.update_device_color(device_id, "LED2", color_for_led2_logic)
                energy_logs_2 = energy_sim.update_device_state(device_id, "LED2", color_for_led2_logic)
                for log in energy_logs_2:
                    db.add_energy_log(log['device_id'], log['power_watts'], log['duration_seconds'], log['color'])
            
            db.add_command(text, command_str, device_id, True)
            
            asyncio.run(broadcast_update("command_executed", {
                "device_id": device_id,
                "command_text": text,
                "led_id": led_id,
                "color_led1": color_for_led1_logic,
                "color_led2": color_for_led2_logic,
                "success": True
            }))
            
        else:
            print("[INFO] No command recognized in the text.")
            asyncio.run(broadcast_update("command_failed", {
                "device_id": device_id,
                "command_text": text,
                "reason": "No valid command found"
            }))

    except sr.UnknownValueError:
        print("[ERROR] Google could not understand the audio.")
    except sr.RequestError as e:
        print(f"[ERROR] Could not request results from Google; {e}")

# --- UDP Audio Thread ---
def udp_audio_listener():
    """Main UDP listener loop for AUDIO (runs in separate thread)"""
    print("[UDP_AUDIO] Audio listener thread started")
    print(f"[UDP_AUDIO] Listening on port {UDP_AUDIO_PORT}")
    
    while True:
        try:
            data, addr = sock_audio.recvfrom(2048)
            
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

        for addr in list(client_buffers.keys()):
            time_since_last_packet = time.time() - client_buffers[addr]['last_packet_time']
            if time_since_last_packet > PACKET_TIMEOUT_SECONDS:
                if len(client_buffers[addr]['buffer']) > AUDIO_BYTES_PER_SECOND * 0.5:
                    print(f"[INFO] Client {addr} timed out. Processing collected audio...")
                    process_audio_buffer(client_buffers[addr]['buffer'], addr)
                else:
                    print(f"[INFO] Client {addr} timed out with insufficient audio. Discarding buffer.")
                del client_buffers[addr]
                
        time.sleep(0.01)

# --- UDP Status Thread ---
def udp_status_listener():
    """Main UDP listener loop for STATUS messages (runs in separate thread)"""
    print("[UDP_STATUS] Status listener thread started")
    print(f"[UDP_STATUS] Listening on port {UDP_CONTROL_PORT}")
    
    while True:
        try:
            data, addr = sock_control.recvfrom(128)
            message = data.decode('utf-8')
            
            if message.startswith("STATUS:"):
                device_id = get_device_id_from_address(addr)
                status_part = message.split(":", 1)[1].strip()
                
                color_led1 = "UNKNOWN"
                color_led2 = "UNKNOWN"
                
                try:
                    parts = status_part.split(',')
                    if len(parts) == 2:
                        color_led1 = parts[0].split('=')[1]
                        color_led2 = parts[1].split('=')[1]
                except Exception as e:
                    print(f"[STATUS] Error parsing status message: {e} - Msg: {message}")

                print(f"[STATUS] Received from {device_id}: LED1={color_led1}, LED2={color_led2}")
                
                db.update_device_color(device_id, "LED1", color_led1)
                db.update_device_color(device_id, "LED2", color_led2)
                
                asyncio.run(broadcast_update("status_update", {
                    "device_id": device_id,
                    "color_led1": color_led1,
                    "color_led2": color_led2
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
    """Manually send command to device, handling correct LED1 logic"""
    device = db.get_device(command.device_id)
    if not device:
        return {"success": False, "error": "Device not found"}
    
    led_id_upper = command.led_id.upper()
    color_upper = command.color.upper()
    
    valid_leds = ["LED1", "LED2", "ALL"]
    valid_colors_rgb = ["RED", "GREEN", "BLUE", "WHITE", "OFF", "PURPLE", "YELLOW"]
    valid_colors_simple = ["ON", "OFF"]
    
    if led_id_upper not in valid_leds:
        return {"success": False, "error": f"Invalid led_id. Must be one of {valid_leds}"}

    color_for_esp = color_upper
    if led_id_upper == "LED1":
        # LED1 supports RGB colors
        if color_upper not in valid_colors_rgb:
            return {"success": False, "error": f"Invalid color for LED1. Must be one of {valid_colors_rgb}"}
            
    elif led_id_upper == "LED2":
        # LED2 only supports ON/OFF
        if color_upper not in valid_colors_simple:
            color_for_esp = "ON" if color_upper != "OFF" else "OFF"
            
    elif led_id_upper == "ALL":
        if color_upper == "ON":
            color_for_esp = "WHITE"
        elif color_upper not in valid_colors_rgb:
             return {"success": False, "error": f"Invalid color. Must be one of {valid_colors_rgb}"}

    command_str = f"{led_id_upper}_{color_for_esp}"
    command_bytes = command_str.encode('utf-8')
    
    if 'ip_address' not in device:
         return {"success": False, "error": "Device IP not found in database."}
    
    ip_address = device['ip_address'].replace('esp32_', '').replace('_', '.')
    
    control_addr = (ip_address, UDP_CONTROL_PORT)
    sock_control.sendto(command_bytes, control_addr)
    
    color_for_led1_logic = None
    color_for_led2_logic = None

    if led_id_upper == "LED1":
        # LED1 gets the actual color
        color_for_led1_logic = color_upper
    elif led_id_upper == "LED2":
        # LED2 gets ON/OFF only
        color_for_led2_logic = "ON" if color_upper != "OFF" else "OFF"
    elif led_id_upper == "ALL":
        # LED1 gets color, LED2 gets ON/OFF
        color_for_led1_logic = color_upper
        color_for_led2_logic = "ON" if color_upper != "OFF" else "OFF"

    if color_for_led1_logic:
        db.update_device_color(command.device_id, "LED1", color_for_led1_logic)
        energy_logs_1 = energy_sim.update_device_state(command.device_id, "LED1", color_for_led1_logic)
        for log in energy_logs_1:
            db.add_energy_log(log['device_id'], log['power_watts'], log['duration_seconds'], log['color'])

    if color_for_led2_logic:
        db.update_device_color(command.device_id, "LED2", color_for_led2_logic)
        energy_logs_2 = energy_sim.update_device_state(command.device_id, "LED2", color_for_led2_logic)
        for log in energy_logs_2:
            db.add_energy_log(log['device_id'], log['power_watts'], log['duration_seconds'], log['color'])
    
    db.add_command(f"Manual: {command_str}", command_bytes.decode(), command.device_id, True)
    
    await broadcast_update("command_executed", {
        "device_id": command.device_id,
        "command_text": f"Manual: {command_str}",
        "led_id": led_id_upper,
        "color_led1": color_for_led1_logic,
        "color_led2": color_for_led2_logic,
        "success": True
    })
    
    return {"success": True, "device_id": command.device_id, "led_id": led_id_upper, "color": color_upper}

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
    print("="*50)
    print("Voice Home Automation Server Starting...")
    print(f"HTTP API: http://localhost:{HTTP_PORT}")
    print(f"API Docs: http://localhost:{HTTP_PORT}/docs")
    print(f"UDP Audio Port: {UDP_AUDIO_PORT}")
    print(f"UDP Control Port: {UDP_CONTROL_PORT}")
    print("="*50)
    
    udp_audio_thread = threading.Thread(target=udp_audio_listener, daemon=True)
    udp_audio_thread.start()
    
    udp_status_thread = threading.Thread(target=udp_status_listener, daemon=True)
    udp_status_thread.start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=HTTP_PORT)