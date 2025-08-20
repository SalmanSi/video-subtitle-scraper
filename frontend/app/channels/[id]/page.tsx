'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import axios from 'axios';
import BatchDownloadButton from '../../components/BatchDownloadButton';

interface Video {
    id: number;
    title: string;
    status: string;
    url: string;
    duration?: number;
    published_at?: string;
}

interface Channel {
    id: number;
    name: string;
    url: string;
    total_videos: number;
    pending: number;
    completed: number;
    failed: number;
}

const ChannelDetails = () => {
    const params = useParams();
    const router = useRouter();
    const id = params.id;
    const [channel, setChannel] = useState<Channel | null>(null);
    const [videos, setVideos] = useState<Video[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (id) {
            fetchChannelDetails(id as string);
        }
    }, [id]);

    const fetchChannelDetails = async (channelId: string) => {
        try {
            const response = await axios.get(`/api/channels/${channelId}`);
            setChannel(response.data);
            fetchVideos(channelId);
        } catch (err) {
            setError('Failed to fetch channel details.');
            setLoading(false);
        }
    };

    const fetchVideos = async (channelId: string) => {
        try {
            const response = await axios.get(`/api/channels/${channelId}/videos`);
            setVideos(response.data.videos || response.data);
        } catch (err) {
            setError('Failed to fetch videos.');
        } finally {
            setLoading(false);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed':
                return '#10b981';
            case 'failed':
                return '#ef4444';
            case 'processing':
                return '#f59e0b';
            default:
                return '#6b7280';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'completed':
                return '✅';
            case 'failed':
                return '❌';
            case 'processing':
                return '⏳';
            default:
                return '⏸️';
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
            <button onClick={() => router.back()}>Go Back</button>
        </div>
    );

    const completedCount = videos.filter(video => video.status === 'completed').length;

    return (
        <div className="channel-details">
            <div className="header">
                <button onClick={() => router.back()} className="back-btn">
                    ← Back
                </button>
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
                    <h3>Completed</h3>
                    <span className="stat-number completed">{channel?.completed || 0}</span>
                </div>
                <div className="stat-card">
                    <h3>Failed</h3>
                    <span className="stat-number failed">{channel?.failed || 0}</span>
                </div>
            </div>

            {/* Batch Download Section */}
            {channel && (
                <BatchDownloadButton
                    channelId={channel.id}
                    channelName={channel.name}
                    completedVideoCount={completedCount}
                />
            )}

            <div className="videos-section">
                <h2>Videos ({videos.length})</h2>
                {videos.length === 0 ? (
                    <p className="no-videos">No videos found for this channel.</p>
                ) : (
                    <div className="videos-grid">
                        {videos.map(video => (
                            <div key={video.id} className="video-card">
                                <div className="video-header">
                                    <h3 className="video-title">{video.title}</h3>
                                    <div 
                                        className="status-badge"
                                        style={{ color: getStatusColor(video.status) }}
                                    >
                                        {getStatusIcon(video.status)} {video.status}
                                    </div>
                                </div>
                                <div className="video-meta">
                                    <span>ID: {video.id}</span>
                                    {video.duration && <span>Duration: {Math.floor(video.duration / 60)}m</span>}
                                </div>
                                <div className="video-actions">
                                    <a 
                                        href={video.url} 
                                        target="_blank" 
                                        rel="noopener noreferrer"
                                        className="view-btn"
                                    >
                                        View Video
                                    </a>
                                    {video.status === 'completed' && (
                                        <button 
                                            onClick={() => {
                                                // Individual video subtitle download
                                                window.open(`/api/subtitles/videos/${video.id}/download`, '_blank');
                                            }}
                                            className="download-btn"
                                        >
                                            Download Subtitles
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

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
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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
                    font-size: 14px;
                    color: #6b7280;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }

                .stat-number {
                    font-size: 2rem;
                    font-weight: bold;
                    color: #111827;
                }

                .stat-number.pending { color: #f59e0b; }
                .stat-number.completed { color: #10b981; }
                .stat-number.failed { color: #ef4444; }

                .videos-section h2 {
                    margin-bottom: 20px;
                    color: #111827;
                }

                .no-videos {
                    text-align: center;
                    color: #6b7280;
                    font-style: italic;
                    padding: 40px;
                }

                .videos-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
                    gap: 20px;
                }

                .video-card {
                    background: white;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    padding: 20px;
                    transition: box-shadow 0.2s ease;
                }

                .video-card:hover {
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }

                .video-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 12px;
                    gap: 12px;
                }

                .video-title {
                    margin: 0;
                    font-size: 16px;
                    line-height: 1.4;
                    color: #111827;
                    flex: 1;
                }

                .status-badge {
                    font-size: 12px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    white-space: nowrap;
                }

                .video-meta {
                    display: flex;
                    gap: 16px;
                    margin-bottom: 16px;
                    font-size: 12px;
                    color: #6b7280;
                }

                .video-actions {
                    display: flex;
                    gap: 8px;
                }

                .view-btn, .download-btn {
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 12px;
                    text-decoration: none;
                    cursor: pointer;
                    border: none;
                    transition: all 0.2s ease;
                }

                .view-btn {
                    background: #f3f4f6;
                    color: #374151;
                }

                .view-btn:hover {
                    background: #e5e7eb;
                }

                .download-btn {
                    background: #10b981;
                    color: white;
                }

                .download-btn:hover {
                    background: #059669;
                }

                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
};

export default ChannelDetails;

