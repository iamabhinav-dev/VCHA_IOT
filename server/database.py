import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Optional
import json

class Database:
    def __init__(self, db_path="home_automation.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                ip_address TEXT NOT NULL,
                last_seen TIMESTAMP,
                current_color_led1 TEXT DEFAULT 'OFF',
                current_color_led2 TEXT DEFAULT 'OFF',
                status TEXT DEFAULT 'online'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                command_text TEXT,
                command_sent TEXT,
                device_id TEXT,
                success INTEGER DEFAULT 1,
                FOREIGN KEY (device_id) REFERENCES devices(device_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS energy_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                device_id TEXT,
                power_watts REAL,
                duration_seconds REAL,
                energy_wh REAL,
                color TEXT,
                FOREIGN KEY (device_id) REFERENCES devices(device_id)
            )
        ''')

        try:
            cursor.execute("ALTER TABLE devices ADD COLUMN current_color_led1 TEXT DEFAULT 'OFF'")
            cursor.execute("ALTER TABLE devices ADD COLUMN current_color_led2 TEXT DEFAULT 'OFF'")
            print("[DATABASE] Migrated devices table: Added LED1/LED2 columns.")
        except sqlite3.OperationalError:
            pass 

        conn.commit()
        conn.close()
        print("[DATABASE] Tables initialized successfully")
    
    def upsert_device(self, device_id: str, ip_address: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO devices (device_id, ip_address, last_seen, status)
            VALUES (?, ?, ?, 'online')
            ON CONFLICT(device_id) DO UPDATE SET
                ip_address=excluded.ip_address,
                last_seen=excluded.last_seen,
                status='online'
        ''', (device_id, ip_address, datetime.now()))
        
        conn.commit()
        conn.close()
    
    # --- MODIFIED: update_device_color (New "ALL" Logic) ---
    def update_device_color(self, device_id: str, led_id: str, color: str):
        """
        Updates the color for a specific LED (or all) for a device.
        """
        now = datetime.now()
        led_id_upper = led_id.upper()
        color_upper = color.upper()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if led_id_upper == "ALL":
                # LED1 gets the color, LED2 gets ON/OFF
                color_led1 = color_upper
                color_led2 = "ON" if color_upper != "OFF" else "OFF"
                
                sql = """
                UPDATE devices 
                SET current_color_led1 = ?, current_color_led2 = ?, last_seen = ? 
                WHERE device_id = ?
                """
                cursor.execute(sql, (color_led1, color_led2, now, device_id))
            
            elif led_id_upper == "LED1":
                # LED1 stores actual RGB colors
                sql = "UPDATE devices SET current_color_led1 = ?, last_seen = ? WHERE device_id = ?"
                cursor.execute(sql, (color_upper, now, device_id))
            
            elif led_id_upper == "LED2":
                # LED2 only stores ON or OFF
                color_led2 = "ON" if color_upper != "OFF" else "OFF"
                sql = "UPDATE devices SET current_color_led2 = ?, last_seen = ? WHERE device_id = ?"
                cursor.execute(sql, (color_led2, now, device_id))
            
            else:
                 cursor.execute("UPDATE devices SET last_seen = ? WHERE device_id = ?", (now, device_id))
            
        except Exception as e:
            print(f"[DATABASE] Error in update_device_color: {e}")
        finally:
            conn.commit()
            conn.close()
    
    def get_device(self, device_id: str) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM devices WHERE device_id = ?', (device_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_all_devices(self) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM devices ORDER BY last_seen DESC')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def add_command(self, command_text: str, command_sent: str, device_id: str, success: bool = True):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO commands (command_text, command_sent, device_id, success)
            VALUES (?, ?, ?, ?)
        ''', (command_text, command_sent, device_id, 1 if success else 0))
        
        conn.commit()
        conn.close()
    
    def get_recent_commands(self, limit: int = 50) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM commands 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def add_energy_log(self, device_id: str, power_watts: float, duration_seconds: float, color: str):
        energy_wh = (power_watts * duration_seconds) / 3600
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO energy_logs (device_id, power_watts, duration_seconds, energy_wh, color)
            VALUES (?, ?, ?, ?, ?)
        ''', (device_id, power_watts, duration_seconds, energy_wh, color))
        
        conn.commit()
        conn.close()
    
    def get_energy_stats(self, device_id: str = None, hours: int = 24) -> Dict:
        conn = self.get_connection()
        cursor = conn.cursor()
        
        base_query = " FROM energy_logs WHERE timestamp >= datetime('now', '-' || ? || ' hours') "
        params = [hours]
        
        if device_id:
            base_query += " AND device_id = ? "
            params.append(device_id)
            
        cursor.execute(f'''
            SELECT 
                SUM(energy_wh) as total_energy_wh,
                SUM(duration_seconds) as total_duration,
                AVG(power_watts) as avg_power,
                COUNT(*) as entries
            {base_query}
        ''', tuple(params))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row['total_energy_wh'] is not None:
            return dict(row)
        return {'total_energy_wh': 0, 'total_duration': 0, 'avg_power': 0, 'entries': 0}
    
    def get_energy_timeline(self, device_id: str = None, hours: int = 24) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Always return individual records for better timeline visualization
        if device_id:
            cursor.execute('''
                SELECT 
                    strftime('%Y-%m-%dT%H:%M:%S', timestamp, 'localtime') as time,
                    energy_wh,
                    power_watts,
                    color
                FROM energy_logs
                WHERE device_id = ?
                AND timestamp >= datetime('now', '-' || ? || ' hours')
                ORDER BY timestamp ASC
            ''', (device_id, hours))
        else:
            cursor.execute('''
                SELECT 
                    strftime('%Y-%m-%dT%H:%M:%S', timestamp, 'localtime') as time,
                    energy_wh,
                    power_watts,
                    color,
                    device_id
                FROM energy_logs
                WHERE timestamp >= datetime('now', '-' || ? || ' hours')
                ORDER BY timestamp ASC
                LIMIT 100
            ''', (hours,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]