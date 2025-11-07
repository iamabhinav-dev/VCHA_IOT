from datetime import datetime
from typing import Dict

class EnergySimulator:
    """Simulates energy consumption based on LED colors"""
    
    # Power consumption estimates for RGB LEDs (in Watts)
    POWER_MAP = {
        'RED': 0.066,      # Single LED: 20mA × 3.3V
        'GREEN': 0.066,
        'BLUE': 0.066,
        'WHITE': 0.198,    # All three LEDs
        'PURPLE': 0.132,   # Red + Blue
        'YELLOW': 0.132,   # Red + Green
        'OFF': 0.0
    }
    
    def __init__(self):
        self.device_states = {}  # Track current state per device
    
    def get_power_consumption(self, color: str) -> float:
        """Get power consumption for a given color in Watts"""
        return self.POWER_MAP.get(color.upper(), 0.0)
    
    def update_device_state(self, device_id: str, new_color: str) -> Dict:
        """
        Update device state and calculate energy consumed since last update
        Returns: dict with power, duration, and energy info
        """
        current_time = datetime.now()
        
        # If device is new or was OFF, initialize
        if device_id not in self.device_states:
            self.device_states[device_id] = {
                'color': 'OFF',
                'last_update': current_time,
                'power': 0.0
            }
            return None  # No energy consumed yet
        
        # Calculate energy consumed in previous state
        prev_state = self.device_states[device_id]
        duration_seconds = (current_time - prev_state['last_update']).total_seconds()
        prev_power = prev_state['power']
        prev_color = prev_state['color']
        
        # Update to new state
        new_power = self.get_power_consumption(new_color)
        self.device_states[device_id] = {
            'color': new_color,
            'last_update': current_time,
            'power': new_power
        }
        
        # Return energy info for the completed period
        return {
            'device_id': device_id,
            'color': prev_color,
            'power_watts': prev_power,
            'duration_seconds': duration_seconds,
            'timestamp': prev_state['last_update']
        }
    
    def get_current_power(self, device_id: str) -> float:
        """Get current power draw for a device"""
        if device_id in self.device_states:
            return self.device_states[device_id]['power']
        return 0.0
    
    def get_device_state(self, device_id: str) -> Dict:
        """Get complete current state of a device"""
        if device_id in self.device_states:
            return self.device_states[device_id].copy()
        return {'color': 'OFF', 'power': 0.0, 'last_update': None}