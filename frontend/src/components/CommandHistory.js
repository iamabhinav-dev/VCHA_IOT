import React from 'react';
import { CheckCircle, XCircle, MessageSquare } from 'lucide-react';
import './CommandHistory.css';

function CommandHistory({ commands }) {
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  return (
    <div className="command-history">
      {commands.length === 0 ? (
        <div className="no-commands">
          <MessageSquare size={48} color="#ccc" />
          <p>No commands yet</p>
        </div>
      ) : (
        <div className="command-list">
          {commands.map((cmd) => (
            <div key={cmd.id} className={`command-item ${cmd.success ? 'success' : 'failed'}`}>
              <div className="command-icon">
                {cmd.success ? (
                  <CheckCircle size={20} color="#22c55e" />
                ) : (
                  <XCircle size={20} color="#ef4444" />
                )}
              </div>
              <div className="command-content">
                <div className="command-text">{cmd.command_text || 'Unknown'}</div>
                <div className="command-meta">
                  <span className="command-action">{cmd.command_sent}</span>
                  <span className="command-device">{cmd.device_id}</span>
                  <span className="command-time">{formatTimestamp(cmd.timestamp)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default CommandHistory;
