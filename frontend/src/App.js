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
      const response = await axios.get(`${API_BASE_URL}/api/energy/stats?hours=24`);
      console.log('Energy Stats Response:', response.data);
      setEnergyStats(response.data);
    } catch (error) {
      console.error('Error fetching energy stats:', error);
    }
  }, []);

  // Fetch energy timeline
  const fetchEnergyTimeline = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/energy/timeline?hours=24`);
      console.log('Energy Timeline Response:', response.data);
      setEnergyTimeline(response.data.timeline || []);
    } catch (error) {
      console.error('Error fetching energy timeline:', error);
    }
  }, []);

  // Control device
  const controlDevice = async (deviceId, ledId, color) => {
    console.log('=== CONTROL COMMAND ===');
    console.log('Device ID:', deviceId);
    console.log('LED ID:', ledId);
    console.log('Color:', color);
    console.log('Sending to API:', {
      device_id: deviceId,
      led_id: ledId,
      color: color
    });
    
    try {
      const response = await axios.post(`${API_BASE_URL}/api/control`, {
        device_id: deviceId,
        led_id: ledId,
        color: color
      });
      console.log('API Response:', response.data);
      // Refresh data after control
      setTimeout(() => {
        fetchDevices();
        fetchCommands();
        fetchEnergyStats();
        fetchEnergyTimeline();
      }, 500);
    } catch (error) {
      console.error('Error controlling device:', error);
      console.error('Error details:', error.response?.data);
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
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
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
    }, 2000); // Refresh every 2 seconds for more responsive updates

    return () => clearInterval(interval);
  }, [fetchDevices, fetchCommands, fetchEnergyStats, fetchEnergyTimeline]);

  return (
    <div className="App">
      <main className="app-main container">
        <h2>Connected Devices</h2>
        
        {devices.length === 0 ? (
          <div className="no-devices">
            <p>No devices connected yet...</p>
            <p className="hint">Make sure your ESP32 is running and connected to WiFi</p>
          </div>
        ) : (
          devices.map((device) => (
            <div key={device.device_id} className="unified-card">
              <div className="card-main-content">
                <div className="left-content">
                  <DeviceCard
                    device={device}
                    onControl={controlDevice}
                  />
                  
                  <div className="energy-section">
                    <div className="section-header">
                      <h3>Energy Consumption</h3>
                      <h3>Power</h3>
                    </div>
                    {energyStats && <EnergyStats stats={energyStats} />}
                    {energyTimeline.length > 0 && (
                      <EnergyChart timeline={energyTimeline} />
                    )}
                  </div>
                </div>

                <div className="right-content">
                  <h3>Command History</h3>
                  <CommandHistory commands={commands} />
                </div>
              </div>
            </div>
          ))
        )}
      </main>
    </div>
  );
}

export default App;
