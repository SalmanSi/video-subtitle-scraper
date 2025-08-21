/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
  destination: 'http://localhost:8004/api/:path*', // Backend server
      },
    ]
  },
}

module.exports = nextConfig
