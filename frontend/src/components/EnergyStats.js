import React from 'react';
import { Zap, Clock, Activity, BarChart3 } from 'lucide-react';
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
        <div className="stat-icon" style={{ background: '#fee2e2' }}>
          <Zap size={24} color="#ef4444" />
        </div>
        <div className="stat-content">
          <p className="stat-label">Total Energy</p>
          <p className="stat-value">{formatEnergy(stats.total_energy_wh)}</p>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon" style={{ background: '#dbeafe' }}>
          <Clock size={24} color="#3b82f6" />
        </div>
        <div className="stat-content">
          <p className="stat-label">Total Duration</p>
          <p className="stat-value">{formatDuration(stats.total_duration)}</p>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon" style={{ background: '#dcfce7' }}>
          <Activity size={24} color="#22c55e" />
        </div>
        <div className="stat-content">
          <p className="stat-label">Avg Power</p>
          <p className="stat-value">{formatPower(stats.avg_power)}</p>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon" style={{ background: '#fef3c7' }}>
          <BarChart3 size={24} color="#eab308" />
        </div>
        <div className="stat-content">
          <p className="stat-label">Events</p>
          <p className="stat-value">{stats.entries || 0}</p>
        </div>
      </div>
    </div>
  );
}

export default EnergyStats;
