'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname();

  return (
    <html lang="en">
      <head>
        <title>Video Subtitle Scraper</title>
        <meta name="description" content="YouTube video subtitle extraction and management tool" />
      </head>
      <body style={{ margin: 0, padding: 0, backgroundColor: '#f9fafb' }}>
        {/* Navigation Bar */}
        <nav style={{
          background: 'white',
          borderBottom: '1px solid #e5e7eb',
          padding: '0 20px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
        }}>
          <div style={{
            maxWidth: '1400px',
            margin: '0 auto',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: '64px'
          }}>
            <Link 
              href="/"
              style={{
                fontSize: '1.25rem',
                fontWeight: 'bold',
                color: '#111827',
                textDecoration: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              🎬 Video Subtitle Scraper
            </Link>
            
            <div style={{ display: 'flex', gap: '8px' }}>
              <Link 
                href="/"
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  fontSize: '14px',
                  fontWeight: '600',
                  textDecoration: 'none',
                  transition: 'all 0.2s ease',
                  background: pathname === '/' ? '#2563eb' : 'transparent',
                  color: pathname === '/' ? 'white' : '#374151'
                }}
              >
                Add Channels
              </Link>
              <Link 
                href="/dashboard"
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  fontSize: '14px',
                  fontWeight: '600',
                  textDecoration: 'none',
                  transition: 'all 0.2s ease',
                  background: pathname === '/dashboard' ? '#2563eb' : 'transparent',
                  color: pathname === '/dashboard' ? 'white' : '#374151'
                }}
              >
                📊 Dashboard
              </Link>
              <Link 
                href="/monitor"
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  fontSize: '14px',
                  fontWeight: '600',
                  textDecoration: 'none',
                  transition: 'all 0.2s ease',
                  background: pathname === '/monitor' ? '#2563eb' : 'transparent',
                  color: pathname === '/monitor' ? 'white' : '#374151'
                }}
              >
                🔍 Job Monitor
              </Link>
              <Link 
                href="/individual"
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  fontSize: '14px',
                  fontWeight: '600',
                  textDecoration: 'none',
                  transition: 'all 0.2s ease',
                  background: pathname === '/individual' ? '#2563eb' : 'transparent',
                  color: pathname === '/individual' ? 'white' : '#374151'
                }}
              >
                🎯 Individual Video
              </Link>
            </div>
          </div>
        </nav>
        
        {/* Main Content */}
        <main style={{ minHeight: 'calc(100vh - 64px)' }}>
          {children}
        </main>
      </body>
    </html>
  )
}
