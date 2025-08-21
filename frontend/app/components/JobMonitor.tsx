// /video-subtitle-scraper/video-subtitle-scraper/frontend/app/components/JobMonitor.tsx

import React, { useEffect, useState } from 'react';

const JobMonitor = () => {
    const [jobs, setJobs] = useState([]);
    const [connectionStatus, setConnectionStatus] = useState('Connecting...');

    useEffect(() => {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const wsUrl = apiUrl.replace('http:', 'ws:').replace('https:', 'wss:');
        const socket = new WebSocket(`${wsUrl}/jobs/status`);

        socket.onopen = () => {
            setConnectionStatus('Connected');
        };

        socket.onmessage = (event) => {
            const updatedJobs = JSON.parse(event.data);
            setJobs(updatedJobs);
        };

        socket.onerror = () => {
            setConnectionStatus('Connection Error');
        };

        socket.onclose = () => {
            setConnectionStatus('Disconnected');
        };

        return () => {
            socket.close();
        };
    }, []);

    return (
        <div>
            <h2>Job Monitor</h2>
            <p>Status: {connectionStatus}</p>
            <ul>
                {jobs.map((job, index) => (
                    <li key={index}>
                        Job ID: {job.id}, Status: {job.status}, Active Workers: {job.active_workers}
                    </li>
                ))}
            </ul>
        </div>
    );
};

export default JobMonitor;