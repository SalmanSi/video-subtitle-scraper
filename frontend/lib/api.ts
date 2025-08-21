// API Configuration
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004';

export const API_ENDPOINTS = {
  channels: `${API_BASE_URL}/api/channels`,
  videos: (channelId: number) => `${API_BASE_URL}/api/channels/${channelId}/videos`,
  channel: (channelId: number) => `${API_BASE_URL}/api/channels/${channelId}`,
  subtitles: {
    video: (videoId: number) => `${API_BASE_URL}/api/videos/${videoId}/subtitles`,
    download: (videoId: number) => `${API_BASE_URL}/api/subtitles/videos/${videoId}/download`,
    batchDownload: (channelId: number) => `${API_BASE_URL}/api/channels/${channelId}/subtitles/download`
  },
  jobs: `${API_BASE_URL}/api/jobs`,
  settings: `${API_BASE_URL}/api/settings`
};
