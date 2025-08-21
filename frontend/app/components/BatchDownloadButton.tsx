import React, { useState } from 'react';

interface BatchDownloadButtonProps {
  channelId: number;
  channelName: string;
  completedVideoCount: number;
  disabled?: boolean;
}

const BatchDownloadButton: React.FC<BatchDownloadButtonProps> = ({
  channelId,
  channelName,
  completedVideoCount,
  disabled = false,
}) => {
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState('');

  const handleDownload = async () => {
    if (completedVideoCount === 0) {
      setError('No completed subtitles available for download');
      return;
    }

    setIsDownloading(true);
    setError('');

    try {
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004'}/api/channels/${channelId}/subtitles/download`, {
        method: 'GET',
        headers: {
          'Accept': 'application/zip',
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('No completed subtitles found for this channel');
        }
        throw new Error(`Download failed: ${response.statusText}`);
      }

      // Get the blob data
      const blob = await response.blob();
      
      // Create download link
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Use the filename from Content-Disposition header if available
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `channel-${channelId}-subtitles.zip`;
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      URL.revokeObjectURL(url);
      document.body.removeChild(link);
      
    } catch (err) {
      console.error('Download error:', err);
      setError(err instanceof Error ? err.message : 'Download failed');
    } finally {
      setIsDownloading(false);
    }
  };

  const isDisabled = disabled || completedVideoCount === 0 || isDownloading;

  return (
    <div className="batch-download-container">
      <button
        onClick={handleDownload}
        disabled={isDisabled}
        className={`batch-download-btn ${isDisabled ? 'disabled' : ''} ${isDownloading ? 'loading' : ''}`}
        title={
          completedVideoCount === 0 
            ? 'No completed subtitles available' 
            : `Download ${completedVideoCount} completed subtitle files as ZIP`
        }
      >
        {isDownloading ? (
          <>
            <span className="spinner"></span>
            Downloading...
          </>
        ) : (
          <>
            📦 Download All Subtitles ({completedVideoCount})
          </>
        )}
      </button>
      
      {error && (
        <div className="error-message">
          ❌ {error}
        </div>
      )}
      
      <style jsx>{`
        .batch-download-container {
          margin: 16px 0;
        }
        
        .batch-download-btn {
          background: #2563eb;
          color: white;
          border: none;
          padding: 12px 24px;
          border-radius: 8px;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 8px;
          transition: all 0.2s ease;
        }
        
        .batch-download-btn:hover:not(.disabled) {
          background: #1d4ed8;
          transform: translateY(-2px);
          box-shadow: 0 4px 8px rgba(37, 99, 235, 0.3);
        }
        
        .batch-download-btn.disabled {
          background: #9ca3af;
          cursor: not-allowed;
          transform: none;
          box-shadow: none;
        }
        
        .batch-download-btn.loading {
          background: #1d4ed8;
          cursor: wait;
        }
        
        .spinner {
          width: 16px;
          height: 16px;
          border: 2px solid #ffffff40;
          border-top: 2px solid white;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        
        .error-message {
          color: #dc2626;
          background: #fee2e2;
          border: 1px solid #fecaca;
          padding: 8px 12px;
          border-radius: 4px;
          margin-top: 8px;
          font-size: 14px;
        }
        
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default BatchDownloadButton;
