import React from 'react';
import './EnergyStats.css';

function EnergyStats({ stats }) {
  const formatEnergy = (wh) => {
    if (!wh) return '0 Wh';
    if (wh < 1) return `${(wh * 1000).toFixed(2)} mWh`;
    return `${wh.toFixed(3)} Wh`;
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0s';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) return `${hours}h ${minutes}m`;
    if (minutes > 0) return `${minutes}m ${secs}s`;
    return `${secs}s`;
  };

  const formatPower = (watts) => {
    if (!watts) return '0 W';
    if (watts < 1) return `${(watts * 1000).toFixed(2)} mW`;
    return `${watts.toFixed(3)} W`;
  };

  return (
    <div className="energy-stats">
      <div className="stat-card">
        <p className="stat-label">Total Energy</p>
        <p className="stat-value">{formatEnergy(stats.total_energy_wh)}</p>
      </div>

      <div className="stat-card">
        <p className="stat-label">Total Duration</p>
        <p className="stat-value">{formatDuration(stats.total_duration)}</p>
      </div>

      <div className="stat-card">
        <p className="stat-label">Avg Power</p>
        <p className="stat-value">{formatPower(stats.avg_power)}</p>
      </div>

      <div className="stat-card">
        <p className="stat-label">Events</p>
        <p className="stat-value">{stats.entries || 0}</p>
      </div>
    </div>
  );
}

export default EnergyStats;
