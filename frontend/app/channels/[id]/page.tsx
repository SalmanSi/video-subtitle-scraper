'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import axios from 'axios';
import VideoQueue from '../../components/VideoQueue';

interface Channel {
    id: number;
    name: string;
    url: string;
    total_videos: number;
    pending: number;
    processing: number;
    completed: number;
    failed: number;
}

const ChannelDetails = () => {
    const params = useParams();
    const id = params.id;
    const [channel, setChannel] = useState<Channel | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (id) {
            fetchChannelDetails(id as string);
        }
    }, [id]);

    const fetchChannelDetails = async (channelId: string) => {
        try {
            const base = process.env.NEXT_PUBLIC_API_URL;
            const url = base ? `${base}/api/channels/${channelId}` : `/api/channels/${channelId}`;
            const response = await axios.get(url);
            setChannel(response.data);
        } catch (err) {
            setError('Failed to fetch channel details.');
        } finally {
            setLoading(false);
        }
    };

    if (loading) return (
        <div className="loading-container">
            <div className="spinner-large"></div>
            <p>Loading channel details...</p>
        </div>
    );
    
    if (error) return (
        <div className="error-container">
            <h2>Error</h2>
            <p>{error}</p>
            <Link href="/dashboard" className="back-btn">Go Back</Link>
        </div>
    );

    return (
        <div className="channel-details">
            <div className="header">
                <Link href="/dashboard" className="back-btn">
                    ← Back to Dashboard
                </Link>
                <h1>{channel?.name}</h1>
                <p className="channel-url">
                    <a href={channel?.url} target="_blank" rel="noopener noreferrer">
                        {channel?.url}
                    </a>
                </p>
            </div>

            <div className="stats-section">
                <div className="stat-card">
                    <h3>Total Videos</h3>
                    <span className="stat-number">{channel?.total_videos || 0}</span>
                </div>
                <div className="stat-card">
                    <h3>Pending</h3>
                    <span className="stat-number pending">{channel?.pending || 0}</span>
                </div>
                <div className="stat-card">
                    <h3>Processing</h3>
                    <span className="stat-number processing">{channel?.processing || 0}</span>
                </div>
                <div className="stat-card">
                    <h3>Completed</h3>
                    <span className="stat-number completed">{channel?.completed || 0}</span>
                </div>
                <div className="stat-card">
                    <h3>Failed</h3>
                    <span className="stat-number failed">{channel?.failed || 0}</span>
                </div>
            </div>

            {/* Video Queue Component */}
            {channel && (
                <VideoQueue
                    channelId={channel.id}
                    channelName={channel.name}
                />
            )}

            <style jsx>{`
                .channel-details {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }

                .loading-container, .error-container {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    min-height: 400px;
                    text-align: center;
                }

                .spinner-large {
                    width: 40px;
                    height: 40px;
                    border: 4px solid #f3f4f6;
                    border-top: 4px solid #2563eb;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin-bottom: 16px;
                }

                .header {
                    margin-bottom: 32px;
                }

                .back-btn {
                    background: #f3f4f6;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 6px;
                    cursor: pointer;
                    margin-bottom: 16px;
                    text-decoration: none;
                    color: #374151;
                    display: inline-block;
                }

                .back-btn:hover {
                    background: #e5e7eb;
                }

                .header h1 {
                    margin: 0 0 8px 0;
                    font-size: 2rem;
                    color: #111827;
                }

                .channel-url a {
                    color: #2563eb;
                    text-decoration: none;
                    font-size: 14px;
                }

                .channel-url a:hover {
                    text-decoration: underline;
                }

                .stats-section {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                    gap: 16px;
                    margin-bottom: 32px;
                }

                .stat-card {
                    background: white;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    padding: 20px;
                    text-align: center;
                }

                .stat-card h3 {
                    margin: 0 0 8px 0;
                    font-size: 12px;
                    color: #6b7280;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    font-weight: 500;
                }

                .stat-number {
                    font-size: 1.75rem;
                    font-weight: bold;
                    color: #111827;
                }

                .stat-number.pending { color: #f59e0b; }
                .stat-number.processing { color: #f59e0b; }
                .stat-number.completed { color: #10b981; }
                .stat-number.failed { color: #ef4444; }

                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
};

export default ChannelDetails;

