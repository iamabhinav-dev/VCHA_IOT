import React from 'react';
import { Power, Wifi, Clock } from 'lucide-react';
import './DeviceCard.css';

const COLORS = [
  { name: 'RED', color: '#ef4444', icon: '🔴' },
  { name: 'GREEN', color: '#22c55e', icon: '🟢' },
  { name: 'BLUE', color: '#3b82f6', icon: '🔵' },
  { name: 'WHITE', color: '#ffffff', icon: '⚪' },
  { name: 'PURPLE', color: '#a855f7', icon: '🟣' },
  { name: 'YELLOW', color: '#eab308', icon: '🟡' },
  { name: 'OFF', color: '#1f2937', icon: '⚫' },
];

function DeviceCard({ device, onControl }) {
  const currentColorObj = COLORS.find(c => c.name === device.current_color) || COLORS[6];
  
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    
    if (diffSecs < 60) return `${diffSecs}s ago`;
    if (diffSecs < 3600) return `${Math.floor(diffSecs / 60)}m ago`;
    if (diffSecs < 86400) return `${Math.floor(diffSecs / 3600)}h ago`;
    return date.toLocaleString();
  };

  const isOnline = () => {
    if (!device.last_seen) return false;
    const lastSeen = new Date(device.last_seen);
    const now = new Date();
    const diffMs = now - lastSeen;
    return diffMs < 30000; // Consider online if seen within 30 seconds
  };

  return (
    <div className="device-card">
      <div className="device-header">
        <div className="device-info">
          <h3>{device.device_id}</h3>
          <div className="device-meta">
            <span className="device-ip">
              <Wifi size={14} /> {device.ip_address}
            </span>
            <span className={`device-status ${isOnline() ? 'online' : 'offline'}`}>
              {isOnline() ? '● Online' : '● Offline'}
            </span>
          </div>
        </div>
      </div>

      <div className="device-current-state">
        <div 
          className="color-preview" 
          style={{ 
            backgroundColor: currentColorObj.color,
            boxShadow: device.current_color !== 'OFF' 
              ? `0 0 20px ${currentColorObj.color}` 
              : 'none'
          }}
        >
          <span className="color-icon">{currentColorObj.icon}</span>
        </div>
        <div className="state-info">
          <p className="current-color">{device.current_color}</p>
          <p className="last-update">
            <Clock size={14} /> {formatTimestamp(device.last_seen)}
          </p>
        </div>
      </div>

      <div className="device-controls">
        <p className="controls-label">Control Light:</p>
        <div className="color-buttons">
          {COLORS.map((colorOption) => (
            <button
              key={colorOption.name}
              className={`color-btn ${device.current_color === colorOption.name ? 'active' : ''}`}
              style={{
                backgroundColor: colorOption.color,
                border: device.current_color === colorOption.name 
                  ? '3px solid #667eea' 
                  : '2px solid #ddd'
              }}
              onClick={() => onControl(device.device_id, colorOption.name)}
              title={colorOption.name}
              disabled={!isOnline()}
            >
              {colorOption.icon}
            </button>
          ))}
        </div>
        
        <button
          className="power-btn"
          onClick={() => onControl(device.device_id, 'OFF')}
          disabled={!isOnline()}
        >
          <Power size={18} /> Turn Off
        </button>
      </div>
    </div>
  );
}

export default DeviceCard;
