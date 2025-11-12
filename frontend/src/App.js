import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';
import DeviceCard from './components/DeviceCard';
import CommandHistory from './components/CommandHistory';
import EnergyStats from './components/EnergyStats';
import EnergyChart from './components/EnergyChart';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:5000/ws';

function App() {
  const [devices, setDevices] = useState([]);
  const [commands, setCommands] = useState([]);
  const [energyStats, setEnergyStats] = useState(null);
  const [energyTimeline, setEnergyTimeline] = useState([]);
  const [wsStatus, setWsStatus] = useState('Disconnected');
  const [selectedHours, setSelectedHours] = useState(24);

  // Fetch devices
  const fetchDevices = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/devices`);
      setDevices(response.data.devices || []);
    } catch (error) {
      console.error('Error fetching devices:', error);
    }
  }, []);

  // Fetch commands
  const fetchCommands = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/commands?limit=20`);
      setCommands(response.data.commands || []);
    } catch (error) {
      console.error('Error fetching commands:', error);
    }
  }, []);

  // Fetch energy stats
  const fetchEnergyStats = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/energy/stats?hours=${selectedHours}`);
      setEnergyStats(response.data);
    } catch (error) {
      console.error('Error fetching energy stats:', error);
    }
  }, [selectedHours]);

  // Fetch energy timeline
  const fetchEnergyTimeline = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/energy/timeline?hours=${selectedHours}`);
      setEnergyTimeline(response.data.timeline || []);
    } catch (error) {
      console.error('Error fetching energy timeline:', error);
    }
  }, [selectedHours]);

  // Control device
  const controlDevice = async (deviceId, color) => {
    try {
      await axios.post(`${API_BASE_URL}/api/control`, {
        device_id: deviceId,
        color: color
      });
      // Refresh data after control
      setTimeout(() => {
        fetchDevices();
        fetchCommands();
      }, 500);
    } catch (error) {
      console.error('Error controlling device:', error);
      alert('Failed to control device');
    }
  };

  // WebSocket connection
  useEffect(() => {
    let ws;
    let reconnectTimeout;

    const connectWebSocket = () => {
      ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setWsStatus('Connected');
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('WebSocket message:', message);

          if (message.type === 'command_executed' || message.type === 'status_update') {
            fetchDevices();
            fetchCommands();
            fetchEnergyStats();
            fetchEnergyTimeline();
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setWsStatus('Error');
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setWsStatus('Disconnected');
        // Attempt to reconnect after 5 seconds
        reconnectTimeout = setTimeout(connectWebSocket, 5000);
      };
    };

    connectWebSocket();

    return () => {
      if (ws) {
        ws.close();
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
  }, [fetchDevices, fetchCommands, fetchEnergyStats, fetchEnergyTimeline]);

  // Initial data fetch
  useEffect(() => {
    fetchDevices();
    fetchCommands();
    fetchEnergyStats();
    fetchEnergyTimeline();
  }, [fetchDevices, fetchCommands, fetchEnergyStats, fetchEnergyTimeline]);

  // Periodic refresh (backup in case WebSocket fails)
  useEffect(() => {
    const interval = setInterval(() => {
      fetchDevices();
      fetchCommands();
      fetchEnergyStats();
      fetchEnergyTimeline();
    }, 10000); // Refresh every 10 seconds

    return () => clearInterval(interval);
  }, [fetchDevices, fetchCommands, fetchEnergyStats, fetchEnergyTimeline]);

  return (
    <div className="App">
      <header className="app-header">
        <div className="header-content">
          <h1>🏠 Voice-Controlled Home Automation</h1>
          <div className="header-status">
            <span className={`ws-status ${wsStatus.toLowerCase()}`}>
              {wsStatus === 'Connected' ? '🟢' : '🔴'} {wsStatus}
            </span>
          </div>
        </div>
      </header>

      <main className="app-main">
        <section className="devices-section">
          <h2>Connected Devices</h2>
          <div className="devices-grid">
            {devices.length === 0 ? (
              <div className="no-devices">
                <p>No devices connected yet...</p>
                <p className="hint">Make sure your ESP32 is running and connected to WiFi</p>
              </div>
            ) : (
              devices.map((device) => (
                <DeviceCard
                  key={device.device_id}
                  device={device}
                  onControl={controlDevice}
                />
              ))
            )}
          </div>
        </section>

        <div className="dashboard-grid">
          <section className="energy-section">
            <div className="section-header">
              <h2>Energy Monitoring</h2>
              <select
                value={selectedHours}
                onChange={(e) => setSelectedHours(Number(e.target.value))}
                className="time-selector"
              >
                <option value={1}>Last Hour</option>
                <option value={6}>Last 6 Hours</option>
                <option value={24}>Last 24 Hours</option>
                <option value={168}>Last Week</option>
              </select>
            </div>
            
            {energyStats && <EnergyStats stats={energyStats} />}
            
            {energyTimeline.length > 0 && (
              <EnergyChart timeline={energyTimeline} />
            )}
          </section>

          <section className="commands-section">
            <h2>Command History</h2>
            <CommandHistory commands={commands} />
          </section>
        </div>
      </main>
    </div>
  );
}

export default App;
