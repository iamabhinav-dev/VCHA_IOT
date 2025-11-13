import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './EnergyChart.css';

function EnergyChart({ timeline }) {
  // Debug logging
  console.log('=== ENERGY CHART DEBUG ===');
  console.log('Timeline data:', timeline);
  console.log('Timeline length:', timeline?.length);
  
  const formatTime = (timeStr) => {
    if (!timeStr) return '';
    const date = new Date(timeStr);
    // Check if date is valid
    if (isNaN(date.getTime())) return timeStr;
    
    // Format in local timezone
    return date.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit',
      hour12: false 
    });
  };

  const formatEnergy = (value) => {
    if (value < 1) return `${(value * 1000).toFixed(2)} mWh`;
    return `${value.toFixed(3)} Wh`;
  };

  const formatPower = (value) => {
    if (value < 1) return `${(value * 1000).toFixed(2)} mW`;
    return `${value.toFixed(3)} W`;
  };

  // Process data for chart - calculate cumulative energy
  let cumulativeEnergy = 0;
  const chartData = timeline.map((entry, index) => {
    cumulativeEnergy += parseFloat(entry.energy_wh) || 0;
    return {
      time: formatTime(entry.time || entry.time_hour),
      energy: cumulativeEnergy,
      power: parseFloat(entry.power_watts) || 0,
      energyDelta: parseFloat(entry.energy_wh) || 0,
      color: entry.color || 'N/A',
      index: index
    };
  });
  
  console.log('Processed chart data:', chartData);
  console.log('Chart data length:', chartData.length);
  
  // Add a starting point at 0 if we have data
  if (chartData.length > 0) {
    const firstTime = new Date(timeline[0].time || timeline[0].time_hour);
    firstTime.setMinutes(firstTime.getMinutes() - 1);
    chartData.unshift({
      time: formatTime(firstTime.toISOString()),
      energy: 0,
      power: 0,
      energyDelta: 0,
      color: 'Start',
      index: -1
    });
  }

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="custom-tooltip">
          <p className="tooltip-time">{data.time}</p>
          {data.color !== 'Start' && <p className="tooltip-color">Color: {data.color}</p>}
          <p className="tooltip-energy">Total: {formatEnergy(payload[0].value)}</p>
          {data.energyDelta > 0 && (
            <p className="tooltip-delta">+{formatEnergy(data.energyDelta)}</p>
          )}
          {payload[1] && data.power > 0 && (
            <p className="tooltip-power">Power: {formatPower(payload[1].value)}</p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="energy-chart-dual">
      {chartData.length === 0 ? (
        <div className="no-data">
          <p>No energy data available yet</p>
        </div>
      ) : (
        <div className="charts-grid">
          <div className="chart-box">
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
                <XAxis 
                  dataKey="time" 
                  stroke="#868e96"
                  style={{ fontSize: '0.75rem' }}
                  tick={{ fill: '#868e96' }}
                />
                <YAxis 
                  stroke="#868e96"
                  style={{ fontSize: '0.75rem' }}
                  tick={{ fill: '#868e96' }}
                  tickFormatter={(value) => value < 1 ? `${(value * 1000).toFixed(0)}m` : value.toFixed(1)}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area 
                  type="monotone" 
                  dataKey="energy" 
                  stroke="#4c6ef5" 
                  fill="#a5c6ff"
                  strokeWidth={2}
                  isAnimationActive={true}
                  animationDuration={300}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-box">
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" />
                <XAxis 
                  dataKey="time" 
                  stroke="#868e96"
                  style={{ fontSize: '0.75rem' }}
                  tick={{ fill: '#868e96' }}
                />
                <YAxis 
                  stroke="#868e96"
                  style={{ fontSize: '0.75rem' }}
                  tick={{ fill: '#868e96' }}
                  tickFormatter={(value) => value < 1 ? `${(value * 1000).toFixed(0)}m` : value.toFixed(1)}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area 
                  type="monotone" 
                  dataKey="power" 
                  stroke="#20c997" 
                  fill="#96f2d7"
                  strokeWidth={2}
                  isAnimationActive={true}
                  animationDuration={300}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}

export default EnergyChart;
