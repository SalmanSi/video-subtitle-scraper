'use client';

import React, { useEffect, useState } from 'react';
import axios from 'axios';

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

const Dashboard: React.FC = () => {
    const [channels, setChannels] = useState<Channel[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchChannels = async () => {
            try {
                const response = await axios.get('/api/channels'); // Adjust the API endpoint as necessary
                setChannels(response.data);
            } catch (err) {
                setError('Failed to fetch channels');
            } finally {
                setLoading(false);
            }
        };

        fetchChannels();
    }, []);

    if (loading) {
        return <div>Loading...</div>;
    }

    if (error) {
        return <div>{error}</div>;
    }

    return (
        <div>
            <h1>Dashboard</h1>
            <table>
                <thead>
                    <tr>
                        <th>Channel Name</th>
                        <th>Total Videos</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {channels.map(channel => (
                        <tr key={channel.id}>
                            <td>{channel.name}</td>
                            <td>{channel.total_videos}</td>
                            <td>{channel.completed}/{channel.total_videos}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default Dashboard;