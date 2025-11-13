from datetime import datetime
from typing import Dict, List, Optional

class EnergySimulator:
    """Simulates energy for one RGB LED (LED1) and one simple 2-pin LED (LED2)"""
    
    # Power map for LED 1 (RGB)
    POWER_MAP_LED1 = {
        'RED': 0.066,
        'GREEN': 0.066,
        'BLUE': 0.066,
        'WHITE': 0.198,    # R+G+B
        'PURPLE': 0.132,   # R+B
        'YELLOW': 0.132,   # R+G
        'OFF': 0.0
    }
    
    # Power map for LED 2 (simple 2-pin)
    # Assuming a standard 5mm LED @ 20mA * 3.3V
    POWER_MAP_LED2 = {
        'ON': 0.066,
        'OFF': 0.0
    }
    
    def __init__(self):
        # State tracking is unchanged
        self.device_states: Dict[str, Dict[str, Dict]] = {}
    
    # NEW: get_power_consumption now needs to know *which* LED
    def get_power_consumption(self, led_id: str, color: str) -> float:
        """Get power consumption in Watts for a given LED and color"""
        color_upper = color.upper()
        if led_id == "LED1":
            return self.POWER_MAP_LED1.get(color_upper, 0.0)
        elif led_id == "LED2":
            return self.POWER_MAP_LED2.get(color_upper, 0.0)
        return 0.0

    def _get_default_led_state(self, time: datetime) -> Dict:
        """Returns a default OFF state for a single LED"""
        return {'color': 'OFF', 'last_update': time, 'power': 0.0}

    # MODIFIED: _update_single_led_state
    def _update_single_led_state(self, device_id: str, led_id: str, new_color: str) -> Optional[Dict]:
        """
        Internal helper to update one LED and return its previous energy log.
        """
        current_time = datetime.now()
        # Get power using the new helper function
        new_power = self.get_power_consumption(led_id, new_color) 
        new_color_upper = new_color.upper()

        if device_id not in self.device_states:
            self.device_states[device_id] = {
                'LED1': self._get_default_led_state(current_time),
                'LED2': self._get_default_led_state(current_time)
            }

        prev_state = self.device_states[device_id][led_id]
        duration_seconds = (current_time - prev_state['last_update']).total_seconds()
        prev_power = prev_state['power']
        prev_color = prev_state['color']
        
        self.device_states[device_id][led_id] = {
            'color': new_color_upper,
            'last_update': current_time,
            'power': new_power
        }
        
        return {
            'device_id': device_id,
            'color': f"{led_id}_{prev_color}", # e.g., "LED1_OFF" or "LED2_RED"
            'power_watts': prev_power,
            'duration_seconds': duration_seconds,
            'timestamp': prev_state['last_update']
        }

    # MODIFIED: update_device_state
    def update_device_state(self, device_id: str, led_id: str, new_color: str) -> List[Dict]:
        """
        Update device state and calculate energy consumed.
        """
        led_id_upper = led_id.upper()
        new_color_upper = new_color.upper()
        logs_to_return: List[Dict] = []
        
        if led_id_upper == "ALL":
            # "ALL" command implies a state for both LEDs
            # LED1 gets the actual color
            color_for_led1 = new_color_upper
            # LED2 gets ON/OFF
            color_for_led2 = "ON" if new_color_upper != "OFF" else "OFF"

            log1 = self._update_single_led_state(device_id, "LED1", color_for_led1)
            log2 = self._update_single_led_state(device_id, "LED2", color_for_led2)
            if log1: logs_to_return.append(log1)
            if log2: logs_to_return.append(log2)
        
        elif led_id_upper in ["LED1", "LED2"]:
            # Update just the one LED specified
            log = self._update_single_led_state(device_id, led_id_upper, new_color_upper)
            if log: logs_to_return.append(log)
            
        return logs_to_return
    
    def get_current_power(self, device_id: str) -> float:
        """Get total current power draw for a device (sum of both LEDs)"""
        if device_id in self.device_states:
            power1 = self.device_states[device_id].get('LED1', {}).get('power', 0.0)
            power2 = self.device_states[device_id].get('LED2', {}).get('power', 0.0)
            return power1 + power2
        return 0.0
    
    def get_device_state(self, device_id: str) -> Dict:
        """Get complete current state of a device"""
        if device_id in self.device_states:
            return self.device_states[device_id].copy()
        
        default_time = datetime.now()
        return {
            'LED1': self._get_default_led_state(default_time),
            'LED2': self._get_default_led_state(default_time)
        }