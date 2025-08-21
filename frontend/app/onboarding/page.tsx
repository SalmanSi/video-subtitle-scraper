"use client";

import React, { useState, useCallback } from 'react';
import axios from 'axios';
import Link from 'next/link';

interface Row {
  url: string;
  status: 'pending' | 'validating' | 'adding' | 'added' | 'exists' | 'error';
  info?: any;
  error?: string;
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
    <div style={{maxWidth:'1200px', margin:'0 auto', padding:'24px', fontFamily:'-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif'}}>
      <div style={{textAlign:'center', marginBottom:'32px'}}>
        <h1 style={{margin:0, fontSize:'2.5rem', color:'#111827'}}>Add Channels</h1>
        <p style={{color:'#6b7280', fontSize:'1.05rem', margin:'8px 0 0'}}>Paste one or multiple YouTube channel URLs (comma or newline separated)</p>
      </div>

      <div style={{display:'flex', gap:'24px', flexWrap:'wrap'}}>
        <div style={{flex:'1 1 480px', minWidth:'360px'}}>
          <textarea
            value={input}
            onChange={e=>setInput(e.target.value)}
            placeholder={'https://www.youtube.com/@veritasium\nhttps://www.youtube.com/@Kurzgesagt'}
            rows={12}
            style={{width:'100%', padding:'16px', border:'1px solid #e5e7eb', borderRadius:'12px', fontSize:'14px', fontFamily:'monospace', resize:'vertical'}}
            disabled={inProgress}
          />
          <div style={{display:'flex', justifyContent:'space-between', marginTop:'12px', alignItems:'center', flexWrap:'wrap', gap:'12px'}}>
            <div style={{fontSize:'12px', color:'#6b7280'}}>
              {parseInput(input).length} unique URL(s)
            </div>
            <div style={{display:'flex', gap:'12px'}}>
              <label style={{fontSize:'12px', display:'flex', alignItems:'center', gap:'4px', cursor:'pointer'}}>
                <input type="checkbox" checked={showOnlyErrors} onChange={e=>setShowOnlyErrors(e.target.checked)} />
                Show only errors
              </label>
              <button
                onClick={startIngestion}
                disabled={inProgress || parseInput(input).length===0}
                style={{background:'#2563eb', color:'white', border:'none', padding:'10px 18px', borderRadius:'8px', fontWeight:600, cursor: inProgress?'not-allowed':'pointer'}}
              >
                {inProgress ? 'Ingesting...' : 'Ingest'}
              </button>
            </div>
          </div>
          {confirmLarge && !inProgress && (
            <div style={{marginTop:'12px', background:'#fef3c7', border:'1px solid #fcd34d', padding:'12px 16px', borderRadius:'8px', fontSize:'12px', color:'#92400e'}}>
              Large batch ({parseInput(input).length} URLs). Click Ingest again to confirm.
            </div>
          )}

          {summary.added+summary.exists+summary.errors>0 && (
            <div style={{marginTop:'16px', display:'flex', gap:'12px', flexWrap:'wrap', fontSize:'12px'}}>
              <span style={{background:'#ecfdf5', color:'#065f46', padding:'4px 8px', borderRadius:'6px'}}>Added: {summary.added}</span>
              <span style={{background:'#eff6ff', color:'#1e3a8a', padding:'4px 8px', borderRadius:'6px'}}>Exists: {summary.exists}</span>
              <span style={{background:'#fef2f2', color:'#991b1b', padding:'4px 8px', borderRadius:'6px'}}>Errors: {summary.errors}</span>
            </div>
          )}

          <div style={{marginTop:'24px'}}>
            <Link href="/dashboard" style={{color:'#2563eb', textDecoration:'underline', fontSize:'14px'}}>Go to Dashboard →</Link>
          </div>
        </div>

        <div style={{flex:'1 1 600px', minWidth:'420px'}}>
          <h2 style={{margin:'0 0 16px 0', fontSize:'1.25rem', color:'#111827'}}>Progress</h2>
          <div style={{border:'1px solid #e5e7eb', borderRadius:'12px', overflow:'hidden'}}>
            <table style={{width:'100%', borderCollapse:'collapse', fontSize:'13px'}}>
              <thead style={{background:'#f9fafb'}}>
                <tr>
                  <th style={{textAlign:'left', padding:'10px 12px', fontWeight:600, color:'#374151'}}>URL</th>
                  <th style={{textAlign:'left', padding:'10px 12px', fontWeight:600, color:'#374151', width:'120px'}}>Status</th>
                  <th style={{textAlign:'left', padding:'10px 12px', fontWeight:600, color:'#374151', width:'160px'}}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredRows.length === 0 ? (
                  <tr>
                    <td colSpan={3} style={{padding:'24px', textAlign:'center', color:'#6b7280', fontStyle:'italic'}}>No rows</td>
                  </tr>
                ) : filteredRows.map(r => (
                  <tr key={r.url} style={{borderTop:'1px solid #f3f4f6'}}>
                    <td style={{padding:'8px 12px', wordBreak:'break-all'}}>{r.url}</td>
                    <td style={{padding:'8px 12px'}}>
                      <StatusPill row={r} />
                      {r.error && <div style={{color:'#991b1b', fontSize:'11px', marginTop:'4px'}}>{r.error}</div>}
                    </td>
                    <td style={{padding:'8px 12px'}}>
                      {['error','exists'].includes(r.status) && (
                        <button
                          onClick={()=>retryRow(r)}
                          style={{background:'#2563eb', color:'white', border:'none', padding:'6px 12px', borderRadius:'6px', fontSize:'12px', cursor:'pointer'}}
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

      <style jsx>{`
        @media (max-width: 900px) {
          table thead { display:none; }
          table tr { display:block; border-bottom:1px solid #f3f4f6; }
          table td { display:block; width:100%; }
          table td:first-child { font-weight:600; }
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
