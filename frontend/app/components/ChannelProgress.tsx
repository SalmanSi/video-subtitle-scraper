'use client';

import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface ChannelIngestionStatus {
  channel_id: number;
  url: string;
  name: string;
  status: 'loading' | 'completed' | 'failed';
  videos_found: number;
  videos_ingested: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
}

interface ChannelProgressProps {
  channelId: number;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

const ChannelProgress: React.FC<ChannelProgressProps> = ({ 
  channelId, 
  onComplete, 
  onError 
}) => {
  const [status, setStatus] = useState<ChannelIngestionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const resolveBackendOrigin = () => {
    if (typeof window === 'undefined') return 'http://localhost:8004';
    if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, '');
    const { protocol, hostname, port } = window.location;
    if (port === '3000' || port === '') {
      return `${protocol}//${hostname}:8004`;
    }
    return `${protocol}//${window.location.host}`;
  };

  const fetchStatus = async () => {
    try {
      const backendOrigin = resolveBackendOrigin();
      const response = await axios.get(
        `${backendOrigin}/api/channels/${channelId}/ingestion-status`
      );
      
      const newStatus = response.data;
      setStatus(newStatus);
      
      // Handle status changes
      if (newStatus.status === 'completed' && onComplete) {
        onComplete();
      } else if (newStatus.status === 'failed' && onError) {
        onError(newStatus.error_message || 'Channel ingestion failed');
      }
      
      setLoading(false);
    } catch (err: any) {
      console.error('Failed to fetch channel status:', err);
      setError(err.response?.data?.detail || 'Failed to fetch status');
      setLoading(false);
      
      if (onError) {
        onError(err.response?.data?.detail || 'Failed to fetch status');
      }
    }
  };

  useEffect(() => {
    // Initial fetch
    fetchStatus();

    // Poll for updates every 2 seconds if still loading
    const interval = setInterval(() => {
      if (status?.status === 'loading') {
        fetchStatus();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [channelId, status?.status]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'loading': return '⏳';
      case 'completed': return '✅';
      case 'failed': return '❌';
      default: return '❓';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'loading': return '#f59e0b';
      case 'completed': return '#10b981';
      case 'failed': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const formatTime = (timeString?: string) => {
    if (!timeString) return 'N/A';
    const date = new Date(timeString);
    return date.toLocaleTimeString();
  };

  const getElapsedTime = (startTime?: string) => {
    if (!startTime) return 'N/A';
    const start = new Date(startTime);
    const now = new Date();
    const elapsed = Math.floor((now.getTime() - start.getTime()) / 1000);
    
    if (elapsed < 60) return `${elapsed}s`;
    if (elapsed < 3600) return `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`;
    return `${Math.floor(elapsed / 3600)}h ${Math.floor((elapsed % 3600) / 60)}m`;
  };

  if (loading && !status) {
    return (
      <div className="channel-progress loading">
        <div className="spinner"></div>
        <span>Loading channel status...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="channel-progress error">
        <span className="error-icon">❌</span>
        <span>Error: {error}</span>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="channel-progress error">
        <span className="error-icon">❌</span>
        <span>No status available</span>
      </div>
    );
  }

  return (
    <div className="channel-progress">
      <div className="progress-header">
        <div className="channel-info">
          <span 
            className="status-icon"
            style={{ color: getStatusColor(status.status) }}
          >
            {getStatusIcon(status.status)}
          </span>
          <div className="channel-details">
            <h4 className="channel-name">{status.name}</h4>
            <p className="channel-url">{status.url}</p>
          </div>
        </div>
        
        <div className="status-badge" style={{ color: getStatusColor(status.status) }}>
          {status.status.toUpperCase()}
        </div>
      </div>

      <div className="progress-stats">
        <div className="stat-item">
          <span className="stat-label">Videos Found:</span>
          <span className="stat-value">{status.videos_found}</span>
        </div>
        
        <div className="stat-item">
          <span className="stat-label">Videos Ingested:</span>
          <span className="stat-value">{status.videos_ingested}</span>
        </div>
        
        <div className="stat-item">
          <span className="stat-label">Started:</span>
          <span className="stat-value">{formatTime(status.started_at)}</span>
        </div>
        
        {status.status === 'loading' && (
          <div className="stat-item">
            <span className="stat-label">Elapsed:</span>
            <span className="stat-value">{getElapsedTime(status.started_at)}</span>
          </div>
        )}
        
        {status.completed_at && (
          <div className="stat-item">
            <span className="stat-label">Completed:</span>
            <span className="stat-value">{formatTime(status.completed_at)}</span>
          </div>
        )}
      </div>

      {status.status === 'loading' && (
        <div className="progress-bar-container">
          <div className="progress-bar">
            <div className="progress-fill loading-animation"></div>
          </div>
          <p className="progress-text">Discovering videos...</p>
        </div>
      )}

      {status.error_message && (
        <div className="error-message">
          <span className="error-icon">⚠️</span>
          {status.error_message}
        </div>
      )}

      <style jsx>{`
        .channel-progress {
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          padding: 16px;
          margin: 12px 0;
          background: white;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .progress-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }

        .channel-info {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .status-icon {
          font-size: 20px;
        }

        .channel-details h4 {
          margin: 0;
          font-size: 16px;
          font-weight: 600;
          color: #1f2937;
        }

        .channel-details p {
          margin: 4px 0 0 0;
          font-size: 12px;
          color: #6b7280;
          word-break: break-all;
        }

        .status-badge {
          font-size: 12px;
          font-weight: 600;
          padding: 4px 8px;
          border-radius: 4px;
          background: rgba(0, 0, 0, 0.05);
        }

        .progress-stats {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
          gap: 12px;
          margin-bottom: 16px;
        }

        .stat-item {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .stat-label {
          font-size: 12px;
          color: #6b7280;
          font-weight: 500;
        }

        .stat-value {
          font-size: 14px;
          color: #1f2937;
          font-weight: 600;
        }

        .progress-bar-container {
          margin-top: 16px;
        }

        .progress-bar {
          width: 100%;
          height: 8px;
          background: #f3f4f6;
          border-radius: 4px;
          overflow: hidden;
        }

        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #3b82f6, #1d4ed8);
        }

        .loading-animation {
          width: 30%;
          animation: loading 2s ease-in-out infinite;
        }

        @keyframes loading {
          0% { transform: translateX(-100%); }
          50% { transform: translateX(250%); }
          100% { transform: translateX(-100%); }
        }

        .progress-text {
          margin: 8px 0 0 0;
          font-size: 12px;
          color: #6b7280;
          text-align: center;
        }

        .error-message {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          background: #fef2f2;
          border: 1px solid #fecaca;
          border-radius: 4px;
          color: #dc2626;
          font-size: 12px;
          margin-top: 12px;
        }

        .loading {
          display: flex;
          align-items: center;
          gap: 8px;
          justify-content: center;
          padding: 20px;
        }

        .error {
          display: flex;
          align-items: center;
          gap: 8px;
          justify-content: center;
          padding: 20px;
          color: #dc2626;
        }

        .spinner {
          width: 16px;
          height: 16px;
          border: 2px solid #f3f4f6;
          border-top: 2px solid #3b82f6;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default ChannelProgress;
