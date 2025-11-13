import React from 'react';
import { Wifi } from 'lucide-react';
import './DeviceCard.css';

function DeviceCard({ device, onControl }) {
  const COLORS = [
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

        <div className="device-toggle">
          <button
            className={`toggle-btn ${device.current_color !== 'OFF' ? 'active' : ''}`}
            onClick={() => onControl(device.device_id, device.current_color === 'OFF' ? 'WHITE' : 'OFF')}
            disabled={!isOnline()}
            aria-label="Toggle device power"
          >
            <div className="toggle-track">
              <div className="toggle-thumb" />
            </div>
          </button>
        </div>
      </div>

      <div className="color-selector-section">
        <h4>Color Select</h4>
        <div className="color-swatches">
          {COLORS.map((option) => (
            <button
              key={option.name}
              type="button"
              className={`color-swatch-btn ${device.current_color === option.name ? 'active' : ''}`}
              onClick={() => onControl(device.device_id, option.name)}
              aria-label={option.name}
              disabled={!isOnline()}
              style={{ backgroundColor: option.color }}
            />
          ))}
        </div>
      </div>
    </>
  );
}

export default DeviceCard;
