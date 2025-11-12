import React from 'react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './EnergyChart.css';

function EnergyChart({ timeline }) {
  const formatTime = (timeStr) => {
    if (!timeStr) return '';
    const date = new Date(timeStr);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatEnergy = (value) => {
    if (value < 1) return `${(value * 1000).toFixed(2)} mWh`;
    return `${value.toFixed(3)} Wh`;
  };

  const formatPower = (value) => {
    if (value < 1) return `${(value * 1000).toFixed(2)} mW`;
    return `${value.toFixed(3)} W`;
  };

  // Process data for chart
  const chartData = timeline.map((entry) => ({
    time: formatTime(entry.time),
    energy: parseFloat(entry.energy_wh) || 0,
    power: parseFloat(entry.power_watts) || 0,
    color: entry.color,
  }));

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip">
          <p className="tooltip-time">{payload[0].payload.time}</p>
          <p className="tooltip-color">Color: {payload[0].payload.color}</p>
          <p className="tooltip-energy">Energy: {formatEnergy(payload[0].value)}</p>
          {payload[1] && (
            <p className="tooltip-power">Power: {formatPower(payload[1].value)}</p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="energy-chart">
      <h3>Energy Consumption Over Time</h3>
      
      {chartData.length === 0 ? (
        <div className="no-data">
          <p>No energy data available yet</p>
        </div>
      ) : (
        <>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                <XAxis 
                  dataKey="time" 
                  stroke="#666"
                  style={{ fontSize: '0.85rem' }}
                />
                <YAxis 
                  stroke="#666"
                  style={{ fontSize: '0.85rem' }}
                  tickFormatter={(value) => value < 1 ? `${(value * 1000).toFixed(0)}m` : value.toFixed(2)}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                <Area 
                  type="monotone" 
                  dataKey="energy" 
                  stroke="#ef4444" 
                  fill="#fecaca"
                  name="Energy (Wh)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-container">
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                <XAxis 
                  dataKey="time" 
                  stroke="#666"
                  style={{ fontSize: '0.85rem' }}
                />
                <YAxis 
                  stroke="#666"
                  style={{ fontSize: '0.85rem' }}
                  tickFormatter={(value) => value < 1 ? `${(value * 1000).toFixed(0)}m` : value.toFixed(2)}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="power" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  name="Power (W)"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}

export default EnergyChart;
