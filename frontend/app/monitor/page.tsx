'use client';

import React, { useEffect, useState, useRef, useCallback } from 'react';
import axios from 'axios';

interface WorkerInfo {
  name: string;
  video_id?: number;
  since?: string;
  status: string;
}

interface RecentError {
  video_id?: number;
  message: string;
  timestamp: string;
}

interface JobStatusData {
  status: string;
  active_workers: number;
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  throughput_per_min: number;
  workers: WorkerInfo[];
  recent_errors: RecentError[];
}

const JobMonitor: React.FC = () => {
  const [data, setData] = useState<JobStatusData | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [showErrors, setShowErrors] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);

  const resolveBackendOrigin = () => {
    if (typeof window === 'undefined') return 'http://localhost:8004';
    if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, '');
    // If we're on the Next dev server (likely port 3000), point to backend 8004
    const { protocol, hostname, port } = window.location;
    if (port === '3000' || port === '') {
      return `${protocol}//${hostname}:8004`;
    }
    return `${protocol}//${window.location.host}`;
  };

  const connectWebSocket = useCallback(() => {
    try {
      const backendOrigin = resolveBackendOrigin();
      const wsProtocol = backendOrigin.startsWith('https') ? 'wss' : 'ws';
      const httpLess = backendOrigin.replace(/^https?:\/\//, '');
      const wsUrl = `${wsProtocol}://${httpLess}/jobs/status`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected to job monitor');
        setConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const jobData = JSON.parse(event.data);
          setData(jobData);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected from job monitor');
        setConnected(false);
        
        // Attempt to reconnect with exponential backoff
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
        reconnectAttempts.current += 1;
        
        reconnectTimeoutRef.current = setTimeout(() => {
          if (reconnectAttempts.current < 10) {
            console.log(`Attempting to reconnect (attempt ${reconnectAttempts.current})...`);
            connectWebSocket();
          } else {
            setError('Failed to connect after multiple attempts. Please refresh the page.');
          }
        }, delay);
      };

      ws.onerror = () => {
        // Avoid flooding console; keep minimal.
        if (!error) {
          console.error('WebSocket error: connection issue');
        }
        setError('WebSocket connection error');
      };

    } catch (err) {
      console.error('Failed to create WebSocket connection:', err);
      setError('Failed to establish WebSocket connection');
    }
  }, []);

  useEffect(() => {
    connectWebSocket();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connectWebSocket]);

  const handleJobAction = async (action: string) => {
    if (actionLoading) return;
    
    try {
      setActionLoading(action);
      const backendOrigin = resolveBackendOrigin();
      const response = await axios.post(`${backendOrigin}/jobs/${action}`);
      
      if (response.status === 200) {
        console.log(`Job ${action} successful:`, response.data);
      }
    } catch (err) {
      console.error(`Failed to ${action} job:`, err);
      setError(`Failed to ${action} job. Please try again.`);
    } finally {
      setActionLoading(null);
    }
  };

  const formatTime = (timeString?: string) => {
    if (!timeString) return 'N/A';
    const date = new Date(timeString);
    return date.toLocaleTimeString();
  };

  const getElapsedTime = (sinceString?: string) => {
    if (!sinceString) return 'N/A';
    const since = new Date(sinceString);
    const now = new Date();
    const elapsed = Math.floor((now.getTime() - since.getTime()) / 1000);
    
    if (elapsed < 60) return `${elapsed}s`;
    if (elapsed < 3600) return `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`;
    return `${Math.floor(elapsed / 3600)}h ${Math.floor((elapsed % 3600) / 60)}m`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return '#10b981';
      case 'paused': return '#f59e0b';
      case 'idle': return '#6b7280';
      case 'failed': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running': return '▶️';
      case 'paused': return '⏸️';
      case 'idle': return '⏹️';
      case 'failed': return '❌';
      default: return '❓';
    }
  };

  if (!connected && !data) {
    return (
      <div className="monitor-container">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>{error || 'Connecting to job monitor...'}</p>
          {error && (
            <button onClick={connectWebSocket} className="retry-btn">
              Retry Connection
            </button>
          )}
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="monitor-container">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading job data...</p>
        </div>
      </div>
    );
  }

  const total = data.pending + data.processing + data.completed + data.failed;
  const progressPercent = total > 0 ? Math.round((data.completed / total) * 100) : 0;

  return (
    <div className="monitor-container">
      <div className="monitor-header">
        <h1>🔍 Job Monitor</h1>
        <div className="connection-status">
          <span className={`status-indicator ${connected ? 'connected' : 'disconnected'}`}></span>
          {connected ? 'Connected' : 'Disconnected'}
        </div>
      </div>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {/* Job Status Overview */}
      <div className="status-overview">
        <div className="status-card main-status">
          <h2>Job Status</h2>
          <div className="status-display">
            <span 
              className="status-badge"
              style={{ color: getStatusColor(data.status) }}
            >
              {getStatusIcon(data.status)} {data.status.toUpperCase()}
            </span>
          </div>
          <div className="status-controls">
            <button 
              onClick={() => handleJobAction('start')}
              disabled={data.status === 'running' || actionLoading === 'start'}
              className="control-btn start-btn"
            >
              {actionLoading === 'start' ? '⏳' : '▶️'} Start
            </button>
            <button 
              onClick={() => handleJobAction('pause')}
              disabled={data.status !== 'running' || actionLoading === 'pause'}
              className="control-btn pause-btn"
            >
              {actionLoading === 'pause' ? '⏳' : '⏸️'} Pause
            </button>
            <button 
              onClick={() => handleJobAction('resume')}
              disabled={data.status !== 'paused' || actionLoading === 'resume'}
              className="control-btn resume-btn"
            >
              {actionLoading === 'resume' ? '⏳' : '▶️'} Resume
            </button>
            <button 
              onClick={() => handleJobAction('stop')}
              disabled={data.status === 'idle' || actionLoading === 'stop'}
              className="control-btn stop-btn"
            >
              {actionLoading === 'stop' ? '⏳' : '⏹️'} Stop
            </button>
          </div>
        </div>

        <div className="status-card">
          <h3>Active Workers</h3>
          <div className="metric-value">{data.active_workers}</div>
        </div>

        <div className="status-card">
          <h3>Throughput</h3>
          <div className="metric-value">{data.throughput_per_min}</div>
          <div className="metric-unit">videos/min</div>
        </div>
      </div>

      {/* Queue Progress */}
      <div className="progress-section">
        <h2>Queue Progress</h2>
        <div className="progress-stats">
          <div className="progress-item">
            <span className="progress-label">Pending</span>
            <span className="progress-value pending">{data.pending}</span>
          </div>
          <div className="progress-item">
            <span className="progress-label">Processing</span>
            <span className="progress-value processing">{data.processing}</span>
          </div>
          <div className="progress-item">
            <span className="progress-label">Completed</span>
            <span className="progress-value completed">{data.completed}</span>
          </div>
          <div className="progress-item">
            <span className="progress-label">Failed</span>
            <span className="progress-value failed">{data.failed}</span>
          </div>
        </div>
        
        <div className="progress-bar-container">
          <div className="progress-header">
            <span>Overall Progress</span>
            <span>{progressPercent}% ({data.completed}/{total})</span>
          </div>
          <div className="progress-bar">
            <div 
              className="progress-fill"
              style={{ width: `${progressPercent}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Active Workers */}
      <div className="workers-section">
        <h2>Active Workers ({data.workers.length})</h2>
        {data.workers.length === 0 ? (
          <div className="empty-state">
            <p>No active workers</p>
          </div>
        ) : (
          <div className="workers-table">
            <table>
              <thead>
                <tr>
                  <th>Worker</th>
                  <th>Video ID</th>
                  <th>Status</th>
                  <th>Elapsed Time</th>
                </tr>
              </thead>
              <tbody>
                {data.workers.map((worker, index) => (
                  <tr key={worker.name || index}>
                    <td>{worker.name}</td>
                    <td>{worker.video_id || 'N/A'}</td>
                    <td>
                      <span className={`worker-status ${worker.status}`}>
                        {worker.status}
                      </span>
                    </td>
                    <td>{getElapsedTime(worker.since)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent Errors */}
      <div className="errors-section">
        <div className="errors-header">
          <h2>Recent Errors ({data.recent_errors.length})</h2>
          <button 
            onClick={() => setShowErrors(!showErrors)}
            className="toggle-btn"
          >
            {showErrors ? '🔼' : '🔽'} {showErrors ? 'Hide' : 'Show'}
          </button>
        </div>
        
        {showErrors && (
          <div className="errors-list">
            {data.recent_errors.length === 0 ? (
              <div className="empty-state">
                <p>No recent errors</p>
              </div>
            ) : (
              data.recent_errors.map((error, index) => (
                <div key={index} className="error-item">
                  <div className="error-header">
                    <span className="error-time">{formatTime(error.timestamp)}</span>
                    {error.video_id && (
                      <span className="error-video">Video ID: {error.video_id}</span>
                    )}
                  </div>
                  <div className="error-message">{error.message}</div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      <style jsx>{`
        .monitor-container {
          max-width: 1400px;
          margin: 0 auto;
          padding: 20px;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        .monitor-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 32px;
          padding-bottom: 20px;
          border-bottom: 1px solid #e5e7eb;
        }

        .monitor-header h1 {
          margin: 0;
          font-size: 2.5rem;
          color: #111827;
          font-weight: 700;
        }

        .connection-status {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
          color: #6b7280;
        }

        .status-indicator {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #ef4444;
        }

        .status-indicator.connected {
          background: #10b981;
        }

        .loading-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 400px;
          text-align: center;
        }

        .spinner {
          width: 40px;
          height: 40px;
          border: 4px solid #f3f4f6;
          border-top: 4px solid #2563eb;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin-bottom: 16px;
        }

        .error-banner {
          background: #fee2e2;
          color: #991b1b;
          padding: 12px 16px;
          border-radius: 8px;
          margin-bottom: 24px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .error-banner button {
          background: none;
          border: none;
          color: #991b1b;
          font-size: 18px;
          cursor: pointer;
          padding: 0 4px;
        }

        .status-overview {
          display: grid;
          grid-template-columns: 2fr 1fr 1fr;
          gap: 24px;
          margin-bottom: 32px;
        }

        .status-card {
          background: white;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          padding: 24px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .status-card.main-status {
          text-align: center;
        }

        .status-card h2, .status-card h3 {
          margin: 0 0 16px 0;
          color: #374151;
          font-size: 1.25rem;
        }

        .status-display {
          margin-bottom: 24px;
        }

        .status-badge {
          font-size: 1.5rem;
          font-weight: bold;
          padding: 8px 16px;
          border-radius: 8px;
          background: #f9fafb;
          border: 2px solid currentColor;
        }

        .status-controls {
          display: flex;
          gap: 8px;
          justify-content: center;
          flex-wrap: wrap;
        }

        .control-btn {
          padding: 8px 16px;
          border: none;
          border-radius: 6px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .control-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .start-btn, .resume-btn {
          background: #10b981;
          color: white;
        }

        .start-btn:hover:not(:disabled), .resume-btn:hover:not(:disabled) {
          background: #059669;
        }

        .pause-btn {
          background: #f59e0b;
          color: white;
        }

        .pause-btn:hover:not(:disabled) {
          background: #d97706;
        }

        .stop-btn {
          background: #ef4444;
          color: white;
        }

        .stop-btn:hover:not(:disabled) {
          background: #dc2626;
        }

        .metric-value {
          font-size: 2.5rem;
          font-weight: bold;
          color: #111827;
          text-align: center;
        }

        .metric-unit {
          text-align: center;
          color: #6b7280;
          font-size: 14px;
          margin-top: 4px;
        }

        .progress-section {
          background: white;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          padding: 24px;
          margin-bottom: 32px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .progress-section h2 {
          margin: 0 0 20px 0;
          color: #374151;
        }

        .progress-stats {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
          gap: 16px;
          margin-bottom: 24px;
        }

        .progress-item {
          text-align: center;
          padding: 16px;
          border-radius: 8px;
          background: #f9fafb;
        }

        .progress-label {
          display: block;
          font-size: 12px;
          color: #6b7280;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 8px;
        }

        .progress-value {
          font-size: 1.5rem;
          font-weight: bold;
        }

        .progress-value.pending { color: #f59e0b; }
        .progress-value.processing { color: #3b82f6; }
        .progress-value.completed { color: #10b981; }
        .progress-value.failed { color: #ef4444; }

        .progress-bar-container {
          background: #f9fafb;
          border-radius: 8px;
          padding: 16px;
        }

        .progress-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
          font-weight: 600;
          color: #374151;
        }

        .progress-bar {
          width: 100%;
          height: 12px;
          background: #e5e7eb;
          border-radius: 6px;
          overflow: hidden;
        }

        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #10b981, #059669);
          border-radius: 6px;
          transition: width 0.3s ease;
        }

        .workers-section, .errors-section {
          background: white;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          padding: 24px;
          margin-bottom: 32px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .workers-section h2, .errors-section h2 {
          margin: 0 0 20px 0;
          color: #374151;
        }

        .workers-table table {
          width: 100%;
          border-collapse: collapse;
        }

        .workers-table th {
          background: #f9fafb;
          padding: 12px;
          text-align: left;
          font-weight: 600;
          color: #374151;
          border-bottom: 1px solid #e5e7eb;
          font-size: 14px;
        }

        .workers-table td {
          padding: 12px;
          border-bottom: 1px solid #f3f4f6;
          color: #6b7280;
        }

        .worker-status {
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 600;
          text-transform: uppercase;
        }

        .worker-status.processing {
          background: #dbeafe;
          color: #1e40af;
        }

        .worker-status.idle {
          background: #f3f4f6;
          color: #6b7280;
        }

        .empty-state {
          text-align: center;
          padding: 40px;
          color: #6b7280;
          font-style: italic;
        }

        .errors-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }

        .toggle-btn {
          background: #f3f4f6;
          border: none;
          padding: 8px 12px;
          border-radius: 6px;
          font-size: 14px;
          cursor: pointer;
          transition: background 0.2s ease;
        }

        .toggle-btn:hover {
          background: #e5e7eb;
        }

        .errors-list {
          max-height: 400px;
          overflow-y: auto;
        }

        .error-item {
          padding: 12px;
          border: 1px solid #fee2e2;
          border-radius: 8px;
          margin-bottom: 8px;
          background: #fef2f2;
        }

        .error-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }

        .error-time {
          font-size: 12px;
          color: #6b7280;
        }

        .error-video {
          font-size: 12px;
          color: #991b1b;
          background: #fee2e2;
          padding: 2px 6px;
          border-radius: 4px;
        }

        .error-message {
          color: #991b1b;
          font-size: 14px;
        }

        .retry-btn {
          background: #2563eb;
          color: white;
          border: none;
          padding: 8px 16px;
          border-radius: 6px;
          cursor: pointer;
          margin-top: 16px;
        }

        .retry-btn:hover {
          background: #1d4ed8;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        @media (max-width: 768px) {
          .monitor-container {
            padding: 16px;
          }
          
          .status-overview {
            grid-template-columns: 1fr;
          }
          
          .progress-stats {
            grid-template-columns: repeat(2, 1fr);
          }
          
          .status-controls {
            flex-direction: column;
          }
          
          .workers-table {
            overflow-x: auto;
          }
        }
      `}</style>
    </div>
  );
};

export default JobMonitor;
