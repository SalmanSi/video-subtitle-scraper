import React, { useState } from 'react';

const ChannelForm: React.FC = () => {
    const [channelUrl, setChannelUrl] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (!channelUrl) {
            setError('Channel URL is required');
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
                throw new Error('Failed to add channel');
            }

            // Clear the input field after successful submission
            setChannelUrl('');
            alert('Channel added successfully!');
        } catch (err) {
            setError(err.message);
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
                />
                <button type="submit">Add Channel</button>
            </form>
            {error && <p style={{ color: 'red' }}>{error}</p>}
        </div>
    );
};

export default ChannelForm;