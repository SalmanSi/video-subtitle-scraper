'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';
import Link from 'next/link';

interface Channel {
    id: number;
    name: string;
    url: string;
    total_videos: number;
    pending: number;
    completed: number;
    failed: number;
    processing: number;
}

export default function HomePage() {
    const [channels, setChannels] = useState<Channel[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchChannels();
    }, []);

    const fetchChannels = async () => {
        try {
            const response = await axios.get(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004'}/api/channels/`);
            setChannels(response.data);
        } catch (err) {
            setError('Failed to fetch channels.');
        } finally {
            setLoading(false);
        }
    };

    if (loading) return (
        <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            justifyContent: 'center', 
            minHeight: '400px', 
            textAlign: 'center' 
        }}>
            <div style={{
                width: '40px',
                height: '40px',
                border: '4px solid #f3f4f6',
                borderTop: '4px solid #2563eb',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
                marginBottom: '16px'
            }}></div>
            <p>Loading channels...</p>
        </div>
    );

    if (error) return (
        <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            justifyContent: 'center', 
            minHeight: '400px', 
            textAlign: 'center' 
        }}>
            <h2>Error</h2>
            <p>{error}</p>
            <button onClick={fetchChannels}>Retry</button>
        </div>
    );

    return (
        <div style={{ 
            maxWidth: '1200px', 
            margin: '0 auto', 
            padding: '20px',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
        }}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-end', flexWrap:'wrap', gap:'16px', marginBottom: '40px' }}>
                <div style={{textAlign:'left'}}>
                    <h1 style={{ margin: '0 0 8px 0', fontSize: '2.5rem', color: '#111827' }}>
                        Channels
                    </h1>
                    <p style={{ color: '#6b7280', fontSize: '1.1rem', margin: '0' }}>
                        Manage ingested YouTube channels & progress
                    </p>
                </div>
                <div style={{display:'flex', gap:'12px'}}>
                    <Link href="/onboarding" style={{background:'#2563eb', color:'#fff', textDecoration:'none', padding:'12px 20px', borderRadius:'10px', fontWeight:600, fontSize:'14px'}}>
                        + Add Channels
                    </Link>
                    <Link href="/settings" style={{background:'#10b981', color:'#fff', textDecoration:'none', padding:'12px 20px', borderRadius:'10px', fontWeight:600, fontSize:'14px'}}>
                        Settings
                    </Link>
                </div>
            </div>

            <div>
                <h2 style={{ marginBottom: '24px', color: '#111827' }}>
                    Channels ({channels.length})
                </h2>
                
                {channels.length === 0 ? (
                    <div style={{ 
                        textAlign: 'center', 
                        padding: '60px 20px', 
                        color: '#6b7280', 
                        fontStyle: 'italic' 
                    }}>
                        <p>No channels found. Add a channel to get started!</p>
                    </div>
                ) : (
                    <div style={{ 
                        display: 'grid', 
                        gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', 
                        gap: '24px' 
                    }}>
                        {channels.map(channel => (
                            <Link 
                                key={channel.id} 
                                href={`/channels/${channel.id}`} 
                                style={{
                                    display: 'block',
                                    background: 'white',
                                    border: '1px solid #e5e7eb',
                                    borderRadius: '12px',
                                    padding: '24px',
                                    textDecoration: 'none',
                                    color: 'inherit',
                                    transition: 'all 0.2s ease',
                                    cursor: 'pointer'
                                }}
                            >
                                <div style={{ 
                                    display: 'flex', 
                                    justifyContent: 'space-between', 
                                    alignItems: 'flex-start', 
                                    marginBottom: '12px' 
                                }}>
                                    <h3 style={{ 
                                        margin: '0', 
                                        fontSize: '1.25rem', 
                                        color: '#111827', 
                                        fontWeight: '600' 
                                    }}>
                                        {channel.name}
                                    </h3>
                                    <span style={{
                                        background: '#f3f4f6',
                                        color: '#374151',
                                        padding: '4px 8px',
                                        borderRadius: '4px',
                                        fontSize: '12px',
                                        fontWeight: '500'
                                    }}>
                                        {channel.total_videos} total
                                    </span>
                                </div>
                                
                                <div style={{ marginBottom: '16px' }}>
                                    <span
                                        role="link"
                                        tabIndex={0}
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            window.open(channel.url, '_blank', 'noopener');
                                        }}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter' || e.key === ' ') {
                                                e.preventDefault();
                                                e.stopPropagation();
                                                window.open(channel.url, '_blank', 'noopener');
                                            }
                                        }}
                                        style={{
                                            color: '#2563eb',
                                            textDecoration: 'underline',
                                            fontSize: '14px',
                                            wordBreak: 'break-all',
                                            cursor: 'pointer'
                                        }}
                                    >
                                        {channel.url}
                                    </span>
                                </div>

                                <div style={{ 
                                    display: 'grid', 
                                    gridTemplateColumns: 'repeat(4, 1fr)', 
                                    gap: '12px', 
                                    marginBottom: '16px' 
                                }}>
                                    <div style={{ 
                                        textAlign: 'center', 
                                        padding: '8px', 
                                        borderRadius: '6px', 
                                        background: '#f9fafb' 
                                    }}>
                                        <span style={{ 
                                            display: 'block', 
                                            fontSize: '1.25rem', 
                                            fontWeight: '600', 
                                            marginBottom: '2px',
                                            color: '#f59e0b'
                                        }}>
                                            {channel.pending}
                                        </span>
                                        <span style={{ 
                                            fontSize: '10px', 
                                            textTransform: 'uppercase', 
                                            letterSpacing: '0.5px', 
                                            color: '#6b7280' 
                                        }}>
                                            Pending
                                        </span>
                                    </div>
                                    <div style={{ 
                                        textAlign: 'center', 
                                        padding: '8px', 
                                        borderRadius: '6px', 
                                        background: '#f9fafb' 
                                    }}>
                                        <span style={{ 
                                            display: 'block', 
                                            fontSize: '1.25rem', 
                                            fontWeight: '600', 
                                            marginBottom: '2px',
                                            color: '#3b82f6'
                                        }}>
                                            {channel.processing}
                                        </span>
                                        <span style={{ 
                                            fontSize: '10px', 
                                            textTransform: 'uppercase', 
                                            letterSpacing: '0.5px', 
                                            color: '#6b7280' 
                                        }}>
                                            Processing
                                        </span>
                                    </div>
                                    <div style={{ 
                                        textAlign: 'center', 
                                        padding: '8px', 
                                        borderRadius: '6px', 
                                        background: '#f9fafb' 
                                    }}>
                                        <span style={{ 
                                            display: 'block', 
                                            fontSize: '1.25rem', 
                                            fontWeight: '600', 
                                            marginBottom: '2px',
                                            color: '#10b981'
                                        }}>
                                            {channel.completed}
                                        </span>
                                        <span style={{ 
                                            fontSize: '10px', 
                                            textTransform: 'uppercase', 
                                            letterSpacing: '0.5px', 
                                            color: '#6b7280' 
                                        }}>
                                            Completed
                                        </span>
                                    </div>
                                    <div style={{ 
                                        textAlign: 'center', 
                                        padding: '8px', 
                                        borderRadius: '6px', 
                                        background: '#f9fafb' 
                                    }}>
                                        <span style={{ 
                                            display: 'block', 
                                            fontSize: '1.25rem', 
                                            fontWeight: '600', 
                                            marginBottom: '2px',
                                            color: '#ef4444'
                                        }}>
                                            {channel.failed}
                                        </span>
                                        <span style={{ 
                                            fontSize: '10px', 
                                            textTransform: 'uppercase', 
                                            letterSpacing: '0.5px', 
                                            color: '#6b7280' 
                                        }}>
                                            Failed
                                        </span>
                                    </div>
                                </div>

                                {channel.completed > 0 && (
                                    <div style={{
                                        background: '#ecfdf5',
                                        color: '#065f46',
                                        padding: '8px 12px',
                                        borderRadius: '6px',
                                        fontSize: '14px',
                                        fontWeight: '500',
                                        textAlign: 'center',
                                        border: '1px solid #a7f3d0'
                                    }}>
                                        📦 {channel.completed} downloads available
                                    </div>
                                )}
                            </Link>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}