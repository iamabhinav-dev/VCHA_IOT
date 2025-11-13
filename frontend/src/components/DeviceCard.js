import React from 'react';
import { Wifi, Lightbulb } from 'lucide-react';
import './DeviceCard.css';

function DeviceCard({ device, onControl }) {
  const RGB_COLORS = [
    { name: 'RED', color: '#ef4444' },
    { name: 'GREEN', color: '#22c55e' },
    { name: 'BLUE', color: '#3b82f6' },
    { name: 'WHITE', color: '#ffffff' },
    { name: 'PURPLE', color: '#a855f7' },
    { name: 'YELLOW', color: '#eab308' },
  ];

  const isOnline = () => {
    if (!device.last_seen) return false;
    const lastSeen = new Date(device.last_seen);
    const now = new Date();
    const diffMs = now - lastSeen;
    return diffMs < 30000;
  };

  const led1State = device.current_color_led1 || 'OFF';
  const led2State = device.current_color_led2 || 'OFF';

  return (
    <>
      <div className="device-card-inline">
        <div className="device-visual">
          <img 
            src="/esp32.jpg" 
            alt="ESP32 Device"
            className="device-image"
          />
        </div>
        
        <div className="device-details">
          <div className="device-name-row">
            <h3>{device.device_id}</h3>
            <span className={`inline-status ${isOnline() ? 'online' : 'offline'}`}>
              <span className="status-dot-inline" />
              {isOnline() ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>
          <div className="device-ip-row">
            <Wifi size={14} /> {device.ip_address}
          </div>
        </div>
      </div>

      {/* LED 1 Control - Toggle + RGB Colors */}
      <div className="led-control-row">
        <div className="led-row-header">
          <div className="led-info">
            <Lightbulb size={16} />
            <h4>LED 1 (RGB)</h4>
            <span className={`led-status ${led1State !== 'OFF' ? 'led-on' : 'led-off'}`}>
              {led1State}
            </span>
          </div>
          <button
            className={`toggle-btn ${led1State !== 'OFF' ? 'active' : ''}`}
            onClick={() => {
              const command = led1State === 'OFF' ? 'WHITE' : 'OFF';
              console.log(`[LED1 Toggle] Current: ${led1State}, Sending: LED1, ${command}`);
              onControl(device.device_id, 'LED1', command);
            }}
            disabled={!isOnline()}
            aria-label="Toggle LED 1"
          >
            <div className="toggle-track">
              <div className="toggle-thumb" />
            </div>
          </button>
        </div>
        <div className="color-swatches">
          {RGB_COLORS.map((option) => (
            <button
              key={option.name}
              type="button"
              className={`color-swatch-btn ${led1State === option.name ? 'active' : ''}`}
              onClick={() => {
                console.log(`[LED1 Color] Sending: LED1, ${option.name}`);
                onControl(device.device_id, 'LED1', option.name);
              }}
              aria-label={option.name}
              disabled={!isOnline()}
              style={{ backgroundColor: option.color }}
            />
          ))}
        </div>
      </div>

      {/* LED 2 Control - Simple Toggle Only */}
      <div className="led-control-row">
        <div className="led-row-header">
          <div className="led-info">
            <Lightbulb size={16} />
            <h4>LED 2 (Simple)</h4>
            <span className={`led-status ${led2State === 'ON' ? 'led-on' : 'led-off'}`}>
              {led2State}
            </span>
          </div>
          <button
            className={`toggle-btn ${led2State === 'ON' ? 'active' : ''}`}
            onClick={() => {
              const command = led2State === 'OFF' ? 'ON' : 'OFF';
              console.log(`[LED2 Toggle] Current: ${led2State}, Sending: LED2, ${command}`);
              onControl(device.device_id, 'LED2', command);
            }}
            disabled={!isOnline()}
            aria-label="Toggle LED 2"
          >
            <div className="toggle-track">
              <div className="toggle-thumb" />
            </div>
          </button>
        </div>
      </div>
    </>
  );
}

export default DeviceCard;
