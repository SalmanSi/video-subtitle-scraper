import React, { useEffect, useState } from 'react';
import axios from 'axios';
import Link from 'next/link';
import BatchDownloadButton from './BatchDownloadButton';

interface Video {
    id: number;
    title: string;
    status: string;
    attempts: number;
    last_error?: string;
    url: string;
    channel_id: number;
    completed_at?: string;
    created_at: string;
}

interface VideoQueueProps {
    channelId: number;
    channelName?: string;
}

const VideoQueue: React.FC<VideoQueueProps> = ({ channelId, channelName = '' }) => {
    const [videos, setVideos] = useState<Video[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [bulkRetrying, setBulkRetrying] = useState(false);

    useEffect(() => {
        fetchVideos();
    }, [channelId]);

    const fetchVideos = async () => {
        try {
            const response = await axios.get(`/api/channels/${channelId}/videos`);
            setVideos(response.data.videos || response.data);
        } catch (error) {
            console.error('Error fetching videos:', error);
            setError('Failed to load videos');
        } finally {
            setLoading(false);
        }
    };

    const handleRetry = async (videoId: number) => {
        try {
            await axios.post(`/api/videos/${videoId}/retry`);
            // Refresh the video list after retry
            await fetchVideos();
        } catch (error) {
            console.error('Error retrying video:', error);
        }
    };

    const handleBulkRetry = async () => {
        setBulkRetrying(true);
        try {
            const failedVideos = videos.filter(v => v.status === 'failed');
            // Retry all failed videos
            const retryPromises = failedVideos.map(video => 
                axios.post(`/api/videos/${video.id}/retry`)
            );
            await Promise.all(retryPromises);
            // Refresh the video list after bulk retry
            await fetchVideos();
        } catch (error) {
            console.error('Error in bulk retry:', error);
        } finally {
            setBulkRetrying(false);
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

    // Filter videos based on status filter
    const filteredVideos = statusFilter === 'all' 
        ? videos 
        : videos.filter(video => video.status === statusFilter);

    const completedCount = videos.filter(video => video.status === 'completed').length;
    const failedCount = videos.filter(video => video.status === 'failed').length;

    if (loading) {
        return (
            <div className="loading-container">
                <div className="spinner"></div>
                <span>Loading videos...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="error-container">
                <p>Error: {error}</p>
                <button onClick={fetchVideos}>Retry</button>
            </div>
        );
    }

    return (
        <div className="video-queue">
            <div className="queue-header">
                <h2>Video Queue ({filteredVideos.length} of {videos.length} videos)</h2>
                
                {/* Controls */}
                <div className="queue-controls">
                    {/* Status Filter */}
                    <select 
                        value={statusFilter} 
                        onChange={(e) => setStatusFilter(e.target.value)}
                        className="status-filter"
                    >
                        <option value="all">All Statuses</option>
                        <option value="pending">Pending</option>
                        <option value="processing">Processing</option>
                        <option value="completed">Completed</option>
                        <option value="failed">Failed</option>
                    </select>

                    {/* Bulk Retry Button */}
                    {failedCount > 0 && (
                        <button 
                            onClick={handleBulkRetry}
                            disabled={bulkRetrying}
                            className="bulk-retry-btn"
                        >
                            {bulkRetrying ? '🔄 Retrying...' : `🔄 Retry All Failed (${failedCount})`}
                        </button>
                    )}

                    {/* Batch Download Button */}
                    <BatchDownloadButton
                        channelId={channelId}
                        channelName={channelName}
                        completedVideoCount={completedCount}
                    />
                </div>
            </div>

            {filteredVideos.length === 0 ? (
                <div className="no-videos">
                    <p>
                        {statusFilter === 'all' 
                            ? 'No videos found for this channel.' 
                            : `No ${statusFilter} videos found.`
                        }
                    </p>
                </div>
            ) : (
                <div className="queue-table-container">
                    <table className="queue-table">
                        <thead>
                            <tr>
                                <th>Title</th>
                                <th>Status</th>
                                <th>Attempts</th>
                                <th>Last Error</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredVideos.map(video => (
                                <tr key={video.id}>
                                    <td className="title-cell">
                                        <div className="video-title" title={video.title}>
                                            {video.title}
                                        </div>
                                    </td>
                                    <td>
                                        <span 
                                            className="status-badge"
                                            style={{ color: getStatusColor(video.status) }}
                                        >
                                            {video.status}
                                        </span>
                                    </td>
                                    <td className="attempts-cell">
                                        {video.attempts}
                                    </td>
                                    <td className="error-cell">
                                        {video.last_error ? (
                                            <span className="error-text" title={video.last_error}>
                                                {video.last_error.length > 30 
                                                    ? `${video.last_error.substring(0, 30)}...` 
                                                    : video.last_error
                                                }
                                            </span>
                                        ) : (
                                            <span className="no-error">—</span>
                                        )}
                                    </td>
                                    <td className="actions-cell">
                                        <div className="action-buttons">
                                            {video.status === 'failed' && (
                                                <button 
                                                    onClick={() => handleRetry(video.id)}
                                                    className="retry-btn"
                                                >
                                                    🔄 Retry
                                                </button>
                                            )}
                                            {video.status === 'completed' && (
                                                <>
                                                    <Link 
                                                        href={`/videos/${video.id}/subtitles`}
                                                        className="view-subtitles-btn"
                                                    >
                                                        👁️ View Subtitles
                                                    </Link>
                                                    <button 
                                                        onClick={() => {
                                                            window.open(`/api/subtitles/videos/${video.id}/download`, '_blank');
                                                        }}
                                                        className="download-btn"
                                                    >
                                                        📥 Download
                                                    </button>
                                                </>
                                            )}
                                            <a 
                                                href={video.url} 
                                                target="_blank" 
                                                rel="noopener noreferrer"
                                                className="view-video-btn"
                                            >
                                                🔗 Video
                                            </a>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            <style jsx>{`
                .video-queue {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }

                .queue-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 24px;
                    flex-wrap: wrap;
                    gap: 16px;
                }

                .queue-header h2 {
                    margin: 0;
                    color: #111827;
                }

                .queue-controls {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    flex-wrap: wrap;
                }

                .status-filter {
                    padding: 8px 12px;
                    border: 1px solid #d1d5db;
                    border-radius: 6px;
                    background: white;
                    font-size: 14px;
                    min-width: 120px;
                }

                .status-filter:focus {
                    outline: none;
                    border-color: #2563eb;
                    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
                }

                .bulk-retry-btn {
                    padding: 8px 16px;
                    border: none;
                    border-radius: 6px;
                    background: #f59e0b;
                    color: white;
                    font-size: 14px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                }

                .bulk-retry-btn:hover:not(:disabled) {
                    background: #d97706;
                }

                .bulk-retry-btn:disabled {
                    opacity: 0.6;
                    cursor: not-allowed;
                }

                .loading-container, .error-container {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 40px;
                    text-align: center;
                    gap: 12px;
                }

                .spinner {
                    width: 20px;
                    height: 20px;
                    border: 2px solid #f3f4f6;
                    border-top: 2px solid #2563eb;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }

                .no-videos {
                    text-align: center;
                    padding: 40px;
                    color: #6b7280;
                    font-style: italic;
                }

                .queue-table-container {
                    background: white;
                    border-radius: 8px;
                    border: 1px solid #e5e7eb;
                    overflow: hidden;
                }

                .queue-table {
                    width: 100%;
                    border-collapse: collapse;
                }

                .queue-table th {
                    background: #f9fafb;
                    padding: 12px 16px;
                    text-align: left;
                    font-weight: 600;
                    color: #374151;
                    border-bottom: 1px solid #e5e7eb;
                }

                .queue-table td {
                    padding: 12px 16px;
                    border-bottom: 1px solid #f3f4f6;
                }

                .queue-table tr:hover {
                    background: #f9fafb;
                }

                .title-cell {
                    max-width: 300px;
                }

                .video-title {
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                    font-weight: 500;
                    color: #111827;
                }

                .status-badge {
                    font-weight: 600;
                    text-transform: uppercase;
                    font-size: 12px;
                    letter-spacing: 0.5px;
                }

                .attempts-cell {
                    text-align: center;
                    font-weight: 500;
                    color: #374151;
                    width: 80px;
                }

                .error-cell {
                    max-width: 200px;
                }

                .error-text {
                    color: #dc2626;
                    font-size: 12px;
                    cursor: help;
                }

                .no-error {
                    color: #9ca3af;
                }

                .actions-cell {
                    width: 250px;
                }

                .action-buttons {
                    display: flex;
                    gap: 6px;
                    flex-wrap: wrap;
                }

                .retry-btn, .download-btn, .view-subtitles-btn, .view-video-btn {
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 11px;
                    text-decoration: none;
                    cursor: pointer;
                    border: none;
                    transition: all 0.2s ease;
                    display: inline-flex;
                    align-items: center;
                    gap: 4px;
                    white-space: nowrap;
                }

                .retry-btn {
                    background: #f59e0b;
                    color: white;
                }

                .retry-btn:hover {
                    background: #d97706;
                }

                .download-btn {
                    background: #10b981;
                    color: white;
                }

                .download-btn:hover {
                    background: #059669;
                }

                .view-subtitles-btn {
                    background: #3b82f6;
                    color: white;
                }

                .view-subtitles-btn:hover {
                    background: #2563eb;
                }

                .view-video-btn {
                    background: #f3f4f6;
                    color: #374151;
                }

                .view-video-btn:hover {
                    background: #e5e7eb;
                }

                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
};

export default VideoQueue;