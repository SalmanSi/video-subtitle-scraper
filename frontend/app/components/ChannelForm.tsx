import React, { useState, useEffect } from 'react';

interface ChannelProgress {
    channelId: number;
    url: string;
    name: string;
    status: 'loading' | 'completed' | 'failed';
    videosFound: number;
    videosIngested: number;
    errorMessage?: string;
}

const ChannelForm: React.FC = () => {
    const [channelUrl, setChannelUrl] = useState('');
    const [error, setError] = useState('');
    const [addedChannels, setAddedChannels] = useState<ChannelProgress[]>([]);
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Poll for channel progress updates
    const pollChannelProgress = async (channelId: number) => {
        const maxAttempts = 60; // Poll for up to 5 minutes (60 * 5s intervals)
        let attempts = 0;
        
        const poll = async () => {
            try {
                const response = await fetch(`/api/channels/${channelId}/ingestion-status`);
                if (response.ok) {
                    const progress: ChannelProgress = await response.json();
                    
                    // Update the specific channel in our list
                    setAddedChannels(prev => 
                        prev.map(ch => ch.channelId === channelId ? progress : ch)
                    );
                    
                    // Continue polling if still loading and haven't exceeded max attempts
                    if (progress.status === 'loading' && attempts < maxAttempts) {
                        attempts++;
                        setTimeout(poll, 5000); // Poll every 5 seconds
                    }
                }
            } catch (err) {
                console.error('Failed to fetch channel progress:', err);
            }
        };
        
        poll();
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsSubmitting(true);

        if (!channelUrl) {
            setError('Channel URL is required');
            setIsSubmitting(false);
            return;
        }

        try {
            const response = await fetch('/api/channels', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: channelUrl }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to add channel');
            }

            const result = await response.json();
            
            // If we have channel IDs, start polling for each
            if (result.channel_ids && result.channel_ids.length > 0) {
                result.channel_ids.forEach((channelId: number) => {
                    // Add initial progress entry
                    const initialProgress: ChannelProgress = {
                        channelId: channelId,
                        url: channelUrl,
                        name: 'Loading...',
                        status: 'loading',
                        videosFound: 0,
                        videosIngested: 0
                    };
                    
                    setAddedChannels(prev => [...prev, initialProgress]);
                    
                    // Start polling for this channel's progress
                    pollChannelProgress(channelId);
                });
            } else {
                // Fallback for older API response format
                const initialProgress: ChannelProgress = {
                    channelId: Date.now(),
                    url: channelUrl,
                    name: 'Loading...',
                    status: 'loading',
                    videosFound: 0,
                    videosIngested: 0
                };
                
                setAddedChannels(prev => [...prev, initialProgress]);
            }
            
            // Clear the input field after successful submission
            setChannelUrl('');
        } catch (err) {
            setError(err.message);
        } finally {
            setIsSubmitting(false);
        }
    };

    const formatStatus = (progress: ChannelProgress) => {
        switch (progress.status) {
            case 'loading':
                return `Loading... (${progress.videosFound} videos found)`;
            case 'completed':
                return `✅ Completed (${progress.videosFound} videos)`;
            case 'failed':
                return `❌ Failed: ${progress.errorMessage || 'Unknown error'}`;
            default:
                return progress.status;
        }
    };

    return (
        <div>
            <h2>Add Channel</h2>
            <form onSubmit={handleSubmit}>
                <input
                    type="text"
                    value={channelUrl}
                    onChange={(e) => setChannelUrl(e.target.value)}
                    placeholder="Enter Channel URL"
                    disabled={isSubmitting}
                />
                <button type="submit" disabled={isSubmitting}>
                    {isSubmitting ? 'Adding...' : 'Add Channel'}
                </button>
            </form>
            {error && <p style={{ color: 'red' }}>{error}</p>}
            
            {/* Real-time progress display */}
            {addedChannels.length > 0 && (
                <div style={{ marginTop: '20px' }}>
                    <h3>Channel Progress</h3>
                    {addedChannels.map((progress, index) => (
                        <div key={progress.channelId || index} style={{ 
                            padding: '10px', 
                            margin: '5px 0', 
                            border: '1px solid #ccc', 
                            borderRadius: '4px',
                            backgroundColor: progress.status === 'loading' ? '#f0f8ff' : 
                                           progress.status === 'completed' ? '#f0fff0' : '#fff0f0'
                        }}>
                            <div><strong>{progress.name}</strong></div>
                            <div style={{ fontSize: '0.9em', color: '#666' }}>{progress.url}</div>
                            <div style={{ fontWeight: 'bold', marginTop: '5px' }}>
                                {formatStatus(progress)}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default ChannelForm;