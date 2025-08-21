"use client";

import React, { useState, useCallback } from 'react';
import axios from 'axios';
import Link from 'next/link';
import ChannelProgress from '../components/ChannelProgress';

interface Row {
  url: string;
  status: 'pending' | 'validating' | 'adding' | 'added' | 'exists' | 'error';
  info?: any;
  error?: string;
  channelId?: number;  // Track channel ID for progress monitoring
}

// Base patterns for different accepted YouTube URL forms (channel handle, channel id, custom, user, video, playlist, short).
const YT_PATTERNS: RegExp[] = [
  /^(https?:\/\/)?(www\.)?youtube\.com\/@[A-Za-z0-9._-]+\/?$/i,                // Handle URLs e.g. youtube.com/@SomeHandle
  /^(https?:\/\/)?(www\.)?youtube\.com\/(channel|c|user)\/[^\s\/]+\/?$/i,      // channel/c/user forms
  /^(https?:\/\/)?(www\.)?youtube\.com\/watch\?v=[^\s&]+/i,                     // individual video
  /^(https?:\/\/)?(www\.)?youtu\.be\/[A-Za-z0-9_-]+/i,                           // short video link
  /^(https?:\/\/)?(www\.)?youtube\.com\/playlist\?list=[^\s&]+/i                // playlist
];

function parseInput(raw: string): string[] {
  return Array.from(new Set(
    raw
      .split(/[\n,]/)
      .map(s => s.trim())
      .filter(s => s.length > 0)
  ));
}

const MAX_BATCH_WARN = 100;
const CONCURRENCY = 3;

const OnboardingPage: React.FC = () => {
  const [input, setInput] = useState('');
  const [rows, setRows] = useState<Row[]>([]);
  const [inProgress, setInProgress] = useState(false);
  const [showOnlyErrors, setShowOnlyErrors] = useState(false);
  const [confirmLarge, setConfirmLarge] = useState(false);
  const [summary, setSummary] = useState<{added:number; exists:number; errors:number}>({added:0, exists:0, errors:0});
  const [addedChannelIds, setAddedChannelIds] = useState<number[]>([]);

  const backendBase = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004').replace(/\/$/, '');

  const validateUrl = (url: string) => {
    const trimmed = url.trim();
    return YT_PATTERNS.some(r => r.test(trimmed));
  };

  const startIngestion = useCallback(async () => {
    const urls = parseInput(input);
    if (urls.length === 0) return;

    if (urls.length > MAX_BATCH_WARN && !confirmLarge) {
      setConfirmLarge(true);
      return;
    }

    // Prepare rows
    const initial: Row[] = urls.map(url => ({ url, status: validateUrl(url) ? 'pending' : 'error', error: validateUrl(url) ? undefined : 'Invalid format'}));
    setRows(initial);
    setSummary({added:0, exists:0, errors: initial.filter(r=>r.status==='error').length});

    const queue = [...initial.filter(r=>r.status==='pending')];
    let active = 0;
    let added = 0, exists = 0, errors = initial.filter(r=>r.status==='error').length;
    setInProgress(true);

    const processNext = async () => {
      if (queue.length === 0) {
        if (active === 0) setInProgress(false);
        return;
      }
      const row = queue.shift();
      if (!row) return;
      row.status = 'adding';
      setRows(r => [...r]);
      active++;
      try {
        const res = await axios.post(`${backendBase}/api/channels/`, { url: row.url });
        // Decide if already exists vs added (backend might return a message or same channel) - naive check by response
        row.status = 'added';
        row.info = res.data;
        
        // Track newly added channels for progress monitoring
        if (res.data && res.data.channels_created > 0) {
          // We need to get the channel ID - let's fetch it
          try {
            const channelsRes = await axios.get(`${backendBase}/api/channels/`);
            const latestChannel = channelsRes.data.find((ch: any) => ch.url === row.url);
            if (latestChannel) {
              row.channelId = latestChannel.id;
              setAddedChannelIds(prev => [...prev, latestChannel.id]);
            }
          } catch (e) {
            console.warn('Could not fetch channel ID for progress tracking');
          }
        }
        
        added++;
      } catch (e: any) {
        if (e?.response?.status === 400 || e?.response?.status === 409) {
          row.status = 'exists';
          row.error = e?.response?.data?.detail || 'Already exists';
          exists++;
        } else {
          row.status = 'error';
          row.error = e?.response?.data?.detail || e.message || 'Error';
          errors++;
        }
      } finally {
        active--;
        setRows(r => [...r]);
        setSummary({added, exists, errors});
        processNext();
      }
    };

    // Launch limited concurrency
    for (let i=0; i<CONCURRENCY; i++) {
      processNext();
    }
  }, [input, confirmLarge, backendBase]);

  const retryRow = async (row: Row) => {
    if (inProgress) return;
    if (!validateUrl(row.url)) {
      row.status = 'error';
      row.error = 'Invalid format';
      setRows(r=>[...r]);
      return;
    }
    row.status = 'adding';
    setRows(r=>[...r]);
    try {
      const res = await axios.post(`${backendBase}/api/channels/`, { url: row.url });
      row.status = 'added';
      row.info = res.data;
      setSummary(s=>({ ...s, added: s.added+1 }));
    } catch (e:any) {
      if (e?.response?.status === 400 || e?.response?.status === 409) {
        row.status = 'exists';
        row.error = e?.response?.data?.detail || 'Already exists';
        setSummary(s=>({ ...s, exists: s.exists+1 }));
      } else {
        row.status = 'error';
        row.error = e?.response?.data?.detail || e.message || 'Error';
        setSummary(s=>({ ...s, errors: s.errors+1 }));
      }
    } finally {
      setRows(r=>[...r]);
    }
  };

  const filteredRows = showOnlyErrors ? rows.filter(r=>['error','exists'].includes(r.status)) : rows;

  return (
    <div className="onboarding-container">
      <div className="header-section">
        <h1>Add Channels</h1>
        <p>Paste one or multiple YouTube channel URLs (comma or newline separated)</p>
      </div>

      <div className="main-content">
        <div className="input-section">
          <textarea
            value={input}
            onChange={e=>setInput(e.target.value)}
            placeholder={'https://www.youtube.com/@veritasium\nhttps://www.youtube.com/@Kurzgesagt'}
            rows={12}
            className="url-textarea"
            disabled={inProgress}
          />
          <div className="input-controls">
            <div className="url-counter">
              {parseInput(input).length} unique URL(s)
            </div>
            <div className="controls-right">
              <label className="error-filter">
                <input 
                  type="checkbox" 
                  checked={showOnlyErrors} 
                  onChange={e=>setShowOnlyErrors(e.target.checked)}
                  className="filter-checkbox"
                />
                Show only errors
              </label>
              <button
                onClick={startIngestion}
                disabled={inProgress || parseInput(input).length===0}
                className={`ingest-btn ${inProgress ? 'loading' : ''}`}
              >
                {inProgress ? 'Ingesting...' : 'Ingest'}
              </button>
            </div>
          </div>
          {confirmLarge && !inProgress && (
            <div className="large-batch-warning">
              Large batch ({parseInput(input).length} URLs). Click Ingest again to confirm.
            </div>
          )}

          {summary.added+summary.exists+summary.errors>0 && (
            <div className="summary-stats">
              <span className="stat-added">Added: {summary.added}</span>
              <span className="stat-exists">Exists: {summary.exists}</span>
              <span className="stat-errors">Errors: {summary.errors}</span>
            </div>
          )}

          <div className="dashboard-link">
            <Link href="/dashboard" className="nav-link">Go to Dashboard →</Link>
          </div>
        </div>

        <div className="progress-section">
          <h2 className="progress-title">Progress</h2>
          <div className="progress-table-container">
            <table className="progress-table">
              <thead>
                <tr>
                  <th className="url-header">URL</th>
                  <th className="status-header">Status</th>
                  <th className="action-header">Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredRows.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="empty-row">No rows</td>
                  </tr>
                ) : filteredRows.map(r => (
                  <tr key={r.url} className="progress-row">
                    <td className="url-cell">{r.url}</td>
                    <td className="status-cell">
                      <StatusPill row={r} />
                      {r.error && <div className="error-details">{r.error}</div>}
                    </td>
                    <td className="action-cell">
                      {['error','exists'].includes(r.status) && (
                        <button
                          onClick={()=>retryRow(r)}
                          className="retry-btn"
                        >Retry</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Channel Progress Monitoring */}
      {addedChannelIds.length > 0 && (
        <div className="channel-progress-section">
          <h3 className="progress-section-title">
            🚀 Channel Ingestion Progress
          </h3>
          <p className="progress-section-description">
            Your channels are being processed in the background. Video metadata is being discovered and queued for subtitle extraction.
          </p>
          <div className="progress-list">
            {addedChannelIds.map(channelId => (
              <ChannelProgress 
                key={channelId}
                channelId={channelId}
                onComplete={() => {
                  console.log(`Channel ${channelId} ingestion completed`);
                }}
                onError={(error) => {
                  console.error(`Channel ${channelId} ingestion failed:`, error);
                }}
              />
            ))}
          </div>
          <div className="next-steps">
            💡 <strong>Next Step:</strong> Once ingestion completes, go to the <Link href="/monitor" className="inline-link">Job Monitor</Link> to start processing subtitles, or visit the <Link href="/dashboard" className="inline-link">Dashboard</Link> to see your channels.
          </div>
        </div>
      )}

      <style jsx>{`
        .onboarding-container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 24px;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        .header-section {
          text-align: center;
          margin-bottom: 32px;
        }

        .header-section h1 {
          margin: 0;
          font-size: 2.5rem;
          color: #111827;
          font-weight: 700;
        }

        .header-section p {
          color: #6b7280;
          font-size: 1.05rem;
          margin: 8px 0 0;
        }

        .main-content {
          display: flex;
          gap: 24px;
          flex-wrap: wrap;
        }

        .input-section {
          flex: 1 1 480px;
          min-width: 360px;
        }

        .url-textarea {
          width: 100%;
          padding: 16px;
          border: 2px solid #e5e7eb;
          border-radius: 12px;
          font-size: 14px;
          font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
          resize: vertical;
          background: white;
          transition: all 0.2s ease;
          line-height: 1.5;
        }

        .url-textarea:focus {
          outline: none;
          border-color: #2563eb;
          box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }

        .url-textarea:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          background: #f9fafb;
        }

        .url-textarea::placeholder {
          color: #9ca3af;
        }

        .input-controls {
          display: flex;
          justify-content: space-between;
          margin-top: 12px;
          align-items: center;
          flex-wrap: wrap;
          gap: 12px;
        }

        .url-counter {
          font-size: 12px;
          color: #6b7280;
          font-weight: 500;
        }

        .controls-right {
          display: flex;
          gap: 12px;
          align-items: center;
        }

        .error-filter {
          font-size: 12px;
          display: flex;
          align-items: center;
          gap: 6px;
          cursor: pointer;
          color: #374151;
          font-weight: 500;
        }

        .filter-checkbox {
          width: 14px;
          height: 14px;
          accent-color: #2563eb;
        }

        .ingest-btn {
          background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
          color: white;
          border: none;
          padding: 10px 18px;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
        }

        .ingest-btn:hover:not(:disabled) {
          background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
          box-shadow: 0 4px 8px rgba(37, 99, 235, 0.3);
          transform: translateY(-1px);
        }

        .ingest-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          transform: none;
        }

        .ingest-btn.loading {
          position: relative;
          color: transparent;
        }

        .ingest-btn.loading::after {
          content: '';
          position: absolute;
          top: 50%;
          left: 50%;
          width: 16px;
          height: 16px;
          border: 2px solid transparent;
          border-top: 2px solid currentColor;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          transform: translate(-50%, -50%);
          color: white;
        }

        .large-batch-warning {
          margin-top: 12px;
          background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
          border: 1px solid #fbbf24;
          padding: 12px 16px;
          border-radius: 8px;
          font-size: 12px;
          color: #92400e;
          font-weight: 500;
        }

        .summary-stats {
          margin-top: 16px;
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
          font-size: 12px;
        }

        .stat-added {
          background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
          color: #065f46;
          padding: 6px 12px;
          border-radius: 6px;
          border: 1px solid #a7f3d0;
          font-weight: 600;
        }

        .stat-exists {
          background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
          color: #1e40af;
          padding: 6px 12px;
          border-radius: 6px;
          border: 1px solid #93c5fd;
          font-weight: 600;
        }

        .stat-errors {
          background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
          color: #991b1b;
          padding: 6px 12px;
          border-radius: 6px;
          border: 1px solid #fecaca;
          font-weight: 600;
        }

        .dashboard-link {
          margin-top: 24px;
        }

        .nav-link {
          color: #2563eb;
          text-decoration: none;
          font-size: 14px;
          font-weight: 600;
          transition: color 0.2s ease;
        }

        .nav-link:hover {
          color: #1d4ed8;
          text-decoration: underline;
        }

        .progress-section {
          flex: 1 1 600px;
          min-width: 420px;
        }

        .progress-title {
          margin: 0 0 16px 0;
          font-size: 1.25rem;
          color: #111827;
          font-weight: 600;
        }

        .progress-table-container {
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          overflow: hidden;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .progress-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 13px;
          background: white;
        }

        .progress-table thead {
          background: #f9fafb;
        }

        .url-header, .status-header, .action-header {
          text-align: left;
          padding: 12px;
          font-weight: 600;
          color: #374151;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          font-size: 11px;
        }

        .status-header {
          width: 120px;
        }

        .action-header {
          width: 160px;
        }

        .empty-row {
          padding: 24px;
          text-align: center;
          color: #6b7280;
          font-style: italic;
        }

        .progress-row {
          border-top: 1px solid #f3f4f6;
          transition: background-color 0.15s ease;
        }

        .progress-row:hover {
          background: #f9fafb;
        }

        .url-cell, .status-cell, .action-cell {
          padding: 12px;
          vertical-align: top;
        }

        .url-cell {
          word-break: break-all;
          font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
          font-size: 12px;
        }

        .error-details {
          color: #991b1b;
          font-size: 11px;
          margin-top: 4px;
          font-weight: 500;
        }

        .retry-btn {
          background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
          color: white;
          border: none;
          padding: 6px 12px;
          border-radius: 6px;
          font-size: 12px;
          cursor: pointer;
          font-weight: 600;
          transition: all 0.2s ease;
          box-shadow: 0 1px 3px rgba(37, 99, 235, 0.2);
        }

        .retry-btn:hover {
          background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
          box-shadow: 0 2px 4px rgba(37, 99, 235, 0.3);
          transform: translateY(-1px);
        }

        .channel-progress-section {
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          padding: 24px;
          margin-top: 24px;
        }

        .progress-section-title {
          margin: 0 0 20px 0;
          color: #1e293b;
          font-size: 18px;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .progress-section-description {
          margin: 0 0 16px 0;
          color: #64748b;
          font-size: 14px;
          line-height: 1.5;
        }

        .progress-list {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .next-steps {
          margin-top: 16px;
          padding: 12px;
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          border-radius: 8px;
          font-size: 14px;
          color: #1e40af;
          line-height: 1.5;
        }

        .inline-link {
          color: #1d4ed8;
          text-decoration: underline;
          font-weight: 600;
        }

        .inline-link:hover {
          color: #1e40af;
        }

        @keyframes spin {
          0% { transform: translate(-50%, -50%) rotate(0deg); }
          100% { transform: translate(-50%, -50%) rotate(360deg); }
        }

        @media (max-width: 900px) {
          .onboarding-container {
            padding: 16px;
          }

          .header-section h1 {
            font-size: 2rem;
          }

          .main-content {
            flex-direction: column;
          }

          .input-section, .progress-section {
            min-width: auto;
          }

          .input-controls {
            flex-direction: column;
            align-items: stretch;
          }

          .controls-right {
            justify-content: space-between;
          }

          .progress-table thead {
            display: none;
          }

          .progress-row {
            display: block;
            border-bottom: 1px solid #f3f4f6;
            padding: 12px;
          }

          .url-cell, .status-cell, .action-cell {
            display: block;
            width: 100%;
            padding: 4px 0;
          }

          .url-cell {
            font-weight: 600;
            margin-bottom: 8px;
          }

          .status-cell {
            margin-bottom: 8px;
          }
        }
      `}</style>
    </div>
  );
};

const StatusPill: React.FC<{row: Row}> = ({row}) => {
  const colorMap: Record<Row['status'], {bg:string; fg:string; label:string}> = {
    pending: {bg:'#f3f4f6', fg:'#374151', label:'Pending'},
    validating: {bg:'#eff6ff', fg:'#1e3a8a', label:'Validating'},
    adding: {bg:'#dbeafe', fg:'#1e40af', label:'Adding...'},
    added: {bg:'#ecfdf5', fg:'#065f46', label:'Added'},
    exists: {bg:'#eef2ff', fg:'#3730a3', label:'Already Added'},
    error: {bg:'#fef2f2', fg:'#991b1b', label:'Error'}
  };
  const c = colorMap[row.status];
  return <span style={{display:'inline-block', padding:'4px 8px', borderRadius:'999px', background:c.bg, color:c.fg, fontSize:'11px', fontWeight:600}}>{c.label}</span>;
};

export default OnboardingPage;
