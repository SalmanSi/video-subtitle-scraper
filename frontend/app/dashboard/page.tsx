'use client';

import React, { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

interface Channel {
    id: number;
    name: string;
    url: string;
    total_videos: number;
    pending: number;
    completed: number;
    failed: number;
    processing: number;
    created_at: string;
}

interface GlobalStats {
    totalChannels: number;
    totalVideos: number;
    overallCompleted: number;
    overallPending: number;
    overallProcessing: number;
    overallFailed: number;
    overallCompletionPercent: number;
}

const Dashboard: React.FC = () => {
    const [channels, setChannels] = useState<Channel[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [refreshing, setRefreshing] = useState<boolean>(false);
    const router = useRouter();

    const fetchChannels = useCallback(async () => {
        try {
            setRefreshing(true);
            const response = await axios.get(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004'}/api/channels/`);
            setChannels(response.data);
            setError(null);
        } catch (err) {
            setError('Failed to fetch channels');
            console.error('Error fetching channels:', err);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        fetchChannels();
        
        // Auto-refresh every 30 seconds
        const interval = setInterval(fetchChannels, 30000);
        return () => clearInterval(interval);
    }, [fetchChannels]);

    const calculateGlobalStats = (): GlobalStats => {
        const totalChannels = channels.length;
        const totalVideos = channels.reduce((sum, ch) => sum + ch.total_videos, 0);
        const overallCompleted = channels.reduce((sum, ch) => sum + ch.completed, 0);
        const overallPending = channels.reduce((sum, ch) => sum + ch.pending, 0);
        const overallProcessing = channels.reduce((sum, ch) => sum + ch.processing, 0);
        const overallFailed = channels.reduce((sum, ch) => sum + ch.failed, 0);
        const overallCompletionPercent = totalVideos > 0 ? Math.round((overallCompleted / totalVideos) * 100) : 0;

        return {
            totalChannels,
            totalVideos,
            overallCompleted,
            overallPending,
            overallProcessing,
            overallFailed,
            overallCompletionPercent
        };
    };

    const getProgressPercentage = (completed: number, total: number): number => {
        return total > 0 ? Math.round((completed / total) * 100) : 0;
    };

    const formatDate = (dateString: string): string => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

    const handleDeleteChannel = async (channelId: number, channelName: string) => {
        if (!confirm(`Are you sure you want to delete channel "${channelName}"? This will remove all associated videos and subtitles.`)) {
            return;
        }

        try {
            await axios.delete(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004'}/api/channels/${channelId}`);
            setChannels(prev => prev.filter(ch => ch.id !== channelId));
        } catch (err) {
            alert('Failed to delete channel. Please try again.');
            console.error('Error deleting channel:', err);
        }
    };

    if (loading) {
        return (
            <div className="loading-container">
                <div className="spinner-large"></div>
                <p>Loading dashboard...</p>
            </div>
        );
    }

    if (error && channels.length === 0) {
        return (
            <div className="error-container">
                <h2>Error</h2>
                <p>{error}</p>
                <button onClick={fetchChannels} className="retry-btn">
                    Retry
                </button>
            </div>
        );
    }

    const globalStats = calculateGlobalStats();

    return (
        <div className="dashboard">
            <div className="dashboard-header">
                <div className="header-content">
                    <h1>Dashboard</h1>
                    <div className="header-actions">
                        <button 
                            onClick={fetchChannels} 
                            className={`refresh-btn ${refreshing ? 'refreshing' : ''}`}
                            disabled={refreshing}
                        >
                            {refreshing ? '⟳' : '↻'} Refresh
                        </button>
                        <Link href="/" className="add-channel-btn">
                            + Add Channel
                        </Link>
                    </div>
                </div>
            </div>

            {/* Global Summary */}
            <div className="global-stats">
                <h2>Global Summary</h2>
                <div className="stats-grid">
                    <div className="stat-card global">
                        <h3>Total Channels</h3>
                        <span className="stat-number">{globalStats.totalChannels}</span>
                    </div>
                    <div className="stat-card global">
                        <h3>Total Videos</h3>
                        <span className="stat-number">{globalStats.totalVideos}</span>
                    </div>
                    <div className="stat-card global">
                        <h3>Overall Completed</h3>
                        <span className="stat-number completed">{globalStats.overallCompleted}</span>
                        <div className="stat-subtitle">{globalStats.overallCompletionPercent}% complete</div>
                    </div>
                    <div className="stat-card global">
                        <h3>In Progress</h3>
                        <span className="stat-number processing">{globalStats.overallProcessing}</span>
                    </div>
                    <div className="stat-card global">
                        <h3>Pending</h3>
                        <span className="stat-number pending">{globalStats.overallPending}</span>
                    </div>
                    <div className="stat-card global">
                        <h3>Failed</h3>
                        <span className="stat-number failed">{globalStats.overallFailed}</span>
                    </div>
                </div>

                {/* Global Progress Bar */}
                <div className="global-progress">
                    <div className="progress-header">
                        <span>Overall Progress</span>
                        <span>{globalStats.overallCompletionPercent}%</span>
                    </div>
                    <div className="progress-bar">
                        <div 
                            className="progress-fill" 
                            style={{ width: `${globalStats.overallCompletionPercent}%` }}
                        ></div>
                    </div>
                </div>
            </div>

            {/* Channels List */}
            <div className="channels-section">
                <h2>Channels ({channels.length})</h2>
                
                {channels.length === 0 ? (
                    <div className="empty-state">
                        <h3>No channels added yet</h3>
                        <p>Start by adding a YouTube channel to begin scraping subtitles.</p>
                        <Link href="/" className="cta-btn">
                            Add Your First Channel
                        </Link>
                    </div>
                ) : (
                    <div className="channels-table-container">
                        <table className="channels-table">
                            <thead>
                                <tr>
                                    <th>Channel Name</th>
                                    <th>Progress</th>
                                    <th>Status Breakdown</th>
                                    <th>Added</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {channels.map(channel => {
                                    const progressPercent = getProgressPercentage(channel.completed, channel.total_videos);
                                    
                                    return (
                                        <tr key={channel.id}>
                                            <td className="channel-info">
                                                <div className="channel-name">
                                                    {channel.name || '(Loading...)'}
                                                </div>
                                                <div className="channel-url">
                                                    <a 
                                                        href={channel.url} 
                                                        target="_blank" 
                                                        rel="noopener noreferrer"
                                                        onClick={(e) => e.stopPropagation()}
                                                    >
                                                        {channel.url}
                                                    </a>
                                                </div>
                                            </td>
                                            <td className="progress-cell">
                                                <div className="progress-info">
                                                    <span className="progress-text">
                                                        {progressPercent}% ({channel.completed}/{channel.total_videos})
                                                    </span>
                                                    <div className="mini-progress-bar">
                                                        <div 
                                                            className="mini-progress-fill" 
                                                            style={{ width: `${progressPercent}%` }}
                                                        ></div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="status-badges">
                                                {channel.pending > 0 && (
                                                    <span className="status-badge pending">
                                                        P: {channel.pending}
                                                    </span>
                                                )}
                                                {channel.processing > 0 && (
                                                    <span className="status-badge processing">
                                                        Pr: {channel.processing}
                                                    </span>
                                                )}
                                                {channel.completed > 0 && (
                                                    <span className="status-badge completed">
                                                        C: {channel.completed}
                                                    </span>
                                                )}
                                                {channel.failed > 0 && (
                                                    <span className="status-badge failed">
                                                        F: {channel.failed}
                                                    </span>
                                                )}
                                            </td>
                                            <td className="date-cell">
                                                {formatDate(channel.created_at)}
                                            </td>
                                            <td className="actions-cell">
                                                <div className="action-buttons">
                                                    <Link 
                                                        href={`/channels/${channel.id}`} 
                                                        className="action-btn view-btn"
                                                    >
                                                        View Queue
                                                    </Link>
                                                    <button 
                                                        onClick={() => handleDeleteChannel(channel.id, channel.name)}
                                                        className="action-btn delete-btn"
                                                    >
                                                        Delete
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <style jsx>{`
                .dashboard {
                    max-width: 1400px;
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

                .dashboard-header {
                    margin-bottom: 32px;
                    border-bottom: 1px solid #e5e7eb;
                    padding-bottom: 20px;
                }

                .header-content {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    flex-wrap: wrap;
                    gap: 16px;
                }

                .dashboard-header h1 {
                    margin: 0;
                    font-size: 2.5rem;
                    color: #111827;
                    font-weight: 700;
                }

                .header-actions {
                    display: flex;
                    gap: 12px;
                    align-items: center;
                }

                .refresh-btn, .add-channel-btn, .retry-btn, .cta-btn {
                    padding: 10px 20px;
                    border-radius: 8px;
                    font-weight: 600;
                    text-decoration: none;
                    border: none;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    font-size: 14px;
                }

                .refresh-btn {
                    background: #f3f4f6;
                    color: #374151;
                }

                .refresh-btn:hover:not(:disabled) {
                    background: #e5e7eb;
                }

                .refresh-btn.refreshing {
                    opacity: 0.7;
                    animation: spin 1s linear infinite;
                }

                .add-channel-btn, .cta-btn {
                    background: #2563eb;
                    color: white;
                }

                .add-channel-btn:hover, .cta-btn:hover {
                    background: #1d4ed8;
                }

                .retry-btn {
                    background: #ef4444;
                    color: white;
                }

                .retry-btn:hover {
                    background: #dc2626;
                }

                .global-stats {
                    margin-bottom: 40px;
                    padding: 24px;
                    background: #f9fafb;
                    border-radius: 12px;
                    border: 1px solid #e5e7eb;
                }

                .global-stats h2 {
                    margin: 0 0 20px 0;
                    color: #111827;
                    font-size: 1.5rem;
                }

                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 16px;
                    margin-bottom: 24px;
                }

                .stat-card {
                    background: white;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    padding: 20px;
                    text-align: center;
                }

                .stat-card.global {
                    border-left: 4px solid #2563eb;
                }

                .stat-card h3 {
                    margin: 0 0 8px 0;
                    font-size: 12px;
                    color: #6b7280;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    font-weight: 600;
                }

                .stat-number {
                    font-size: 2rem;
                    font-weight: bold;
                    color: #111827;
                    display: block;
                }

                .stat-number.pending { color: #f59e0b; }
                .stat-number.processing { color: #3b82f6; }
                .stat-number.completed { color: #10b981; }
                .stat-number.failed { color: #ef4444; }

                .stat-subtitle {
                    font-size: 12px;
                    color: #6b7280;
                    margin-top: 4px;
                }

                .global-progress {
                    background: white;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    padding: 20px;
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
                    background: #f3f4f6;
                    border-radius: 6px;
                    overflow: hidden;
                }

                .progress-fill {
                    height: 100%;
                    background: linear-gradient(90deg, #10b981, #059669);
                    border-radius: 6px;
                    transition: width 0.3s ease;
                }

                .channels-section h2 {
                    margin-bottom: 20px;
                    color: #111827;
                    font-size: 1.5rem;
                }

                .empty-state {
                    text-align: center;
                    padding: 60px 20px;
                    background: white;
                    border: 2px dashed #d1d5db;
                    border-radius: 12px;
                }

                .empty-state h3 {
                    margin: 0 0 8px 0;
                    color: #374151;
                    font-size: 1.25rem;
                }

                .empty-state p {
                    margin: 0 0 24px 0;
                    color: #6b7280;
                }

                .channels-table-container {
                    background: white;
                    border-radius: 12px;
                    border: 1px solid #e5e7eb;
                    overflow: hidden;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                }

                .channels-table {
                    width: 100%;
                    border-collapse: collapse;
                }

                .channels-table th {
                    background: #f9fafb;
                    padding: 16px;
                    text-align: left;
                    font-weight: 600;
                    color: #374151;
                    border-bottom: 1px solid #e5e7eb;
                    font-size: 14px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }

                .channels-table td {
                    padding: 16px;
                    border-bottom: 1px solid #f3f4f6;
                    vertical-align: top;
                }

                .channels-table tr:hover {
                    background: #f9fafb;
                }

                .channel-info {
                    min-width: 300px;
                }

                .channel-name {
                    font-weight: 600;
                    color: #111827;
                    margin-bottom: 4px;
                    font-size: 14px;
                }

                .channel-url {
                    font-size: 12px;
                }

                .channel-url a {
                    color: #6b7280;
                    text-decoration: none;
                    word-break: break-all;
                }

                .channel-url a:hover {
                    color: #2563eb;
                    text-decoration: underline;
                }

                .progress-cell {
                    min-width: 150px;
                }

                .progress-info {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }

                .progress-text {
                    font-size: 14px;
                    font-weight: 600;
                    color: #374151;
                }

                .mini-progress-bar {
                    width: 100%;
                    height: 6px;
                    background: #f3f4f6;
                    border-radius: 3px;
                    overflow: hidden;
                }

                .mini-progress-fill {
                    height: 100%;
                    background: linear-gradient(90deg, #10b981, #059669);
                    border-radius: 3px;
                    transition: width 0.3s ease;
                }

                .status-badges {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 6px;
                    min-width: 120px;
                }

                .status-badge {
                    font-size: 11px;
                    font-weight: 600;
                    padding: 4px 8px;
                    border-radius: 12px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }

                .status-badge.pending {
                    background: #fef3c7;
                    color: #92400e;
                }

                .status-badge.processing {
                    background: #dbeafe;
                    color: #1e40af;
                }

                .status-badge.completed {
                    background: #d1fae5;
                    color: #065f46;
                }

                .status-badge.failed {
                    background: #fee2e2;
                    color: #991b1b;
                }

                .date-cell {
                    font-size: 12px;
                    color: #6b7280;
                    min-width: 100px;
                }

                .actions-cell {
                    min-width: 180px;
                }

                .action-buttons {
                    display: flex;
                    gap: 8px;
                    flex-wrap: wrap;
                }

                .action-btn {
                    padding: 6px 12px;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 600;
                    text-decoration: none;
                    border: none;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }

                .view-btn {
                    background: #2563eb;
                    color: white;
                }

                .view-btn:hover {
                    background: #1d4ed8;
                }

                .delete-btn {
                    background: #ef4444;
                    color: white;
                }

                .delete-btn:hover {
                    background: #dc2626;
                }

                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }

                @media (max-width: 768px) {
                    .dashboard {
                        padding: 16px;
                    }
                    
                    .header-content {
                        flex-direction: column;
                        align-items: stretch;
                    }
                    
                    .stats-grid {
                        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    }
                    
                    .channels-table-container {
                        overflow-x: auto;
                    }
                    
                    .action-buttons {
                        flex-direction: column;
                    }
                }
            `}</style>
        </div>
    );
};

export default Dashboard;