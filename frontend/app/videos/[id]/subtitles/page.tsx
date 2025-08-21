"use client";
import React, { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import axios from 'axios';

interface SubtitleItem {
  id: number;
  language: string;
  content: string;
  content_length: number;
  downloaded_at: string;
}

interface VideoSubtitlesResponse {
  video_id: number;
  video_title: string;
  video_url: string;
  status: string;
  subtitles: SubtitleItem[];
}

function escapeHtml(str: string) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function highlight(content: string, q: string) {
  if (!q) return escapeHtml(content);
  try {
    const re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
    return escapeHtml(content).replace(re, m => `<mark>${m}</mark>`);
  } catch {
    return escapeHtml(content);
  }
}

const VideoSubtitlesPage: React.FC = () => {
  const params = useParams();
  const router = useRouter();
  const videoId = params.id as string;
  const [data, setData] = useState<VideoSubtitlesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeLang, setActiveLang] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [matchCount, setMatchCount] = useState(0);

  useEffect(() => {
    if (videoId) fetchData(videoId);
  }, [videoId]);

  const fetchData = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const url = base ? `${base}/api/subtitles/videos/${id}` : `/api/subtitles/videos/${id}`;
      const res = await axios.get(url);
      setData(res.data);
      if (res.data.subtitles?.length) setActiveLang(res.data.subtitles[0].language);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load subtitles');
    } finally {
      setLoading(false);
    }
  };

  const downloadSubtitle = (subtitleId: number) => {
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const url = base ? `${base}/api/subtitles/${subtitleId}/download` : `/api/subtitles/${subtitleId}/download`;
    window.open(url, '_blank');
  };

  const current = data ? data.subtitles.find(s=>s.language===activeLang) || data.subtitles[0] : null;

  const highlighted = useMemo(() => {
    if (!current) return '';
    return highlight(current.content, query);
  }, [current, query]);

  useEffect(() => {
    if (!query || !highlighted) {
      setMatchCount(0);
      return;
    }
    const tmp = highlighted.match(/<mark>/g);
    setMatchCount(tmp ? tmp.length : 0);
  }, [query, highlighted]);

  if (loading) return <div style={{display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',minHeight:'300px'}}><div className="spinner" />Loading subtitles...</div>;
  if (error) return <div style={{textAlign:'center',padding:'40px'}}><h2>Error</h2><p>{error}</p><button onClick={()=>fetchData(videoId)}>Retry</button></div>;
  if (!data) return null;

  return (
    <div style={{maxWidth:'1100px', margin:'0 auto', padding:'24px', fontFamily:'-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif'}}>
      <button onClick={()=>router.back()} style={{background:'#f3f4f6',border:'none',padding:'8px 16px',borderRadius:'6px',marginBottom:'16px',cursor:'pointer'}}>← Back</button>
  <h1 style={{margin:'0 0 4px',fontSize:'2rem',color:'#111827'}}>{data.video_title || `Video ${data.video_id}`}</h1>
      <p style={{margin:'0 0 16px'}}><a style={{color:'#2563eb'}} href={data.video_url} target="_blank" rel="noopener noreferrer">Open on YouTube</a></p>

      {data.subtitles.length === 0 ? (
        <div style={{padding:'60px 20px', textAlign:'center', color:'#6b7280', background:'#f9fafb', border:'1px solid #e5e7eb', borderRadius:'12px'}}>No subtitles found for this video.</div>
      ) : (
        <div style={{display:'flex', gap:'24px', flexWrap:'wrap'}}>
          <div style={{flex:'0 0 220px'}}>
            <h3 style={{margin:'0 0 12px 0', fontSize:'14px', letterSpacing:'0.5px', textTransform:'uppercase', color:'#6b7280'}}>Languages</h3>
            <div style={{display:'flex', flexDirection:'column', gap:'8px'}}>
              {data.subtitles.map(sub => (
                <button key={sub.id} onClick={()=>setActiveLang(sub.language)} style={{textAlign:'left',padding:'8px 12px',border:'1px solid #e5e7eb',borderRadius:'8px',background: sub.language===activeLang ? '#2563eb' : '#fff', color: sub.language===activeLang ? '#fff' : '#374151', cursor:'pointer', fontSize:'13px'}}>
                  {sub.language} ({Math.round(sub.content_length/1000)}k chars)
                </button>
              ))}
            </div>
          </div>
          <div style={{flex:'1 1 600px', minWidth:'360px'}}>
            <div style={{display:'flex', flexDirection:'column', gap:'12px'}}>
              <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                <h3 style={{margin:0, fontSize:'1rem', color:'#374151'}}>Transcript ({current.language})</h3>
                <div style={{display:'flex', gap:'8px'}}>
                  <input
                    placeholder='Search text'
                    value={query}
                    onChange={e=>setQuery(e.target.value)}
                    style={{padding:'6px 10px', border:'1px solid #d1d5db', borderRadius:'6px', fontSize:'12px'}}
                  />
                  <button onClick={()=>downloadSubtitle(current.id)} style={{background:'#10b981', color:'#fff', border:'none', padding:'8px 14px', borderRadius:'6px', fontSize:'12px', fontWeight:600, cursor:'pointer'}}>Download .txt</button>
                </div>
              </div>
              {query && (
                <div style={{fontSize:'11px', color:'#6b7280'}}>Matches: {matchCount}</div>
              )}
              <div style={{border:'1px solid #e5e7eb', borderRadius:'12px', padding:'16px', background:'#fff', maxHeight:'600px', overflowY:'auto', whiteSpace:'pre-wrap', fontFamily:'monospace', fontSize:'13px', lineHeight:1.5}}>
                <div dangerouslySetInnerHTML={{__html: highlighted}} />
              </div>
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
  .spinner {width:40px;height:40px;border:4px solid #f3f4f6;border-top:4px solid #2563eb;border-radius:50%;animation:spin 1s linear infinite;margin-bottom:16px;}
  mark { background:#fde68a; padding:0 2px; border-radius:2px; }
        @keyframes spin {0%{transform:rotate(0deg);}100%{transform:rotate(360deg);}}
      `}</style>
    </div>
  );
};

export default VideoSubtitlesPage;
