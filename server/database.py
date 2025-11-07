import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import json

class Database:
    def __init__(self, db_path="home_automation.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Create a new database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Devices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                ip_address TEXT NOT NULL,
                last_seen TIMESTAMP,
                current_color TEXT DEFAULT 'OFF',
                status TEXT DEFAULT 'online'
            )
        ''')
        
        # Commands table
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
        
        # Energy logs table
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
        
        conn.commit()
        conn.close()
        print("[DATABASE] Tables initialized successfully")
    
    def upsert_device(self, device_id: str, ip_address: str, current_color: str = None):
        """Insert or update device information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if current_color:
            cursor.execute('''
                INSERT INTO devices (device_id, ip_address, last_seen, current_color, status)
                VALUES (?, ?, ?, ?, 'online')
                ON CONFLICT(device_id) DO UPDATE SET
                    ip_address=excluded.ip_address,
                    last_seen=excluded.last_seen,
                    current_color=excluded.current_color,
                    status='online'
            ''', (device_id, ip_address, datetime.now(), current_color))
        else:
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
    
    def update_device_color(self, device_id: str, color: str):
        """Update device current color"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE devices 
            SET current_color = ?, last_seen = ?
            WHERE device_id = ?
        ''', (color, datetime.now(), device_id))
        
        conn.commit()
        conn.close()
    
    def get_device(self, device_id: str) -> Optional[Dict]:
        """Get device information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM devices WHERE device_id = ?', (device_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_all_devices(self) -> List[Dict]:
        """Get all devices"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM devices ORDER BY last_seen DESC')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def add_command(self, command_text: str, command_sent: str, device_id: str, success: bool = True):
        """Log a command"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO commands (command_text, command_sent, device_id, success)
            VALUES (?, ?, ?, ?)
        ''', (command_text, command_sent, device_id, 1 if success else 0))
        
        conn.commit()
        conn.close()
    
    def get_recent_commands(self, limit: int = 50) -> List[Dict]:
        """Get recent commands"""
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
        """Log energy consumption"""
        energy_wh = (power_watts * duration_seconds) / 3600  # Convert to Wh
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO energy_logs (device_id, power_watts, duration_seconds, energy_wh, color)
            VALUES (?, ?, ?, ?, ?)
        ''', (device_id, power_watts, duration_seconds, energy_wh, color))
        
        conn.commit()
        conn.close()
    
    def get_energy_stats(self, device_id: str = None, hours: int = 24) -> Dict:
        """Get energy consumption statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if device_id:
            cursor.execute('''
                SELECT 
                    SUM(energy_wh) as total_energy_wh,
                    SUM(duration_seconds) as total_duration,
                    AVG(power_watts) as avg_power,
                    COUNT(*) as entries
                FROM energy_logs
                WHERE device_id = ? 
                AND timestamp >= datetime('now', '-' || ? || ' hours')
            ''', (device_id, hours))
        else:
            cursor.execute('''
                SELECT 
                    SUM(energy_wh) as total_energy_wh,
                    SUM(duration_seconds) as total_duration,
                    AVG(power_watts) as avg_power,
                    COUNT(*) as entries
                FROM energy_logs
                WHERE timestamp >= datetime('now', '-' || ? || ' hours')
            ''', (hours,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return {'total_energy_wh': 0, 'total_duration': 0, 'avg_power': 0, 'entries': 0}
    
    def get_energy_timeline(self, device_id: str = None, hours: int = 24) -> List[Dict]:
        """Get energy consumption over time"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if device_id:
            cursor.execute('''
                SELECT 
                    datetime(timestamp) as time,
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
                    datetime(timestamp) as time,
                    SUM(energy_wh) as energy_wh,
                    AVG(power_watts) as power_watts,
                    color
                FROM energy_logs
                WHERE timestamp >= datetime('now', '-' || ? || ' hours')
                GROUP BY datetime(timestamp), color
                ORDER BY timestamp ASC
            ''', (hours,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]