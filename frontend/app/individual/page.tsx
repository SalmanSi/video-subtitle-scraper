"use client";
import SingleVideoIngestion from '../components/SingleVideoIngestion';
import Link from 'next/link';

export default function IndividualVideoPage() {
  return (
    <div className="individual-container">
      <div className="header">
        <div className="header-inner">
          <h1>Individual Video Processing</h1>
          <p className="subtitle">
            Extract subtitles from a single YouTube video without adding it to the channel queue. Perfect for quick tests or one‑off needs.
          </p>
        </div>
      </div>

      {/* Core Tool */}
      <div className="tool-wrapper">
        <SingleVideoIngestion />
      </div>

      {/* How It Works / Info Section */}
      <div className="info-section">
        <h2 className="section-title">How it works</h2>
        <div className="cards">
          <div className="card">
            <div className="card-icon">🔍</div>
            <h3>Get Info</h3>
            <p>Preview video details and available subtitle languages.</p>
          </div>
          <div className="card">
            <div className="card-icon">🎯</div>
            <h3>Extract</h3>
            <p>Fetch subtitles instantly and view a preview.</p>
          </div>
          <div className="card">
            <div className="card-icon">💾</div>
            <h3>Download</h3>
            <p>Download the extracted subtitles to your device.</p>
          </div>
          <div className="card">
            <div className="card-icon">�</div>
            <h3>Languages</h3>
            <p>Choose preferred and auto‑generated languages.</p>
          </div>
        </div>

        <div className="note">
          <div className="note-icon">📌</div>
          <div className="note-body">
            <h4>Important</h4>
            <p>
              Videos processed here are <strong>not stored</strong> or added to any channel queue. For bulk or managed processing use the
              {' '}<Link href="/" className="link">Add Channels</Link> workflow then manage them on the{' '}
              <Link href="/dashboard" className="link">Dashboard</Link> and <Link href="/monitor" className="link">Job Monitor</Link>.
            </p>
          </div>
        </div>
      </div>

      <style jsx>{`
        .individual-container {
          max-width: 1400px;
          margin: 0 auto;
          padding: 20px;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .header {
          margin-bottom: 32px;
          border-bottom: 1px solid #e5e7eb;
          padding-bottom: 20px;
        }
        .header-inner h1 {
          margin: 0;
          font-size: 2.5rem;
          color: #111827;
          font-weight: 700;
        }
        .subtitle {
          max-width: 760px;
          margin-top: 12px;
          font-size: 1.05rem;
          color: #6b7280;
          line-height: 1.5;
        }
        .tool-wrapper {
          margin-bottom: 40px;
        }
        .info-section {
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          padding: 28px;
          margin-bottom: 40px;
        }
        .section-title {
          margin: 0 0 20px 0;
          color: #374151;
          font-size: 1.5rem;
          font-weight: 600;
        }
        .cards {
          display: grid;
          grid-template-columns: repeat(auto-fit,minmax(160px,1fr));
          gap: 16px;
          margin-bottom: 28px;
        }
        .card {
          background: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 10px;
          padding: 16px 16px 18px;
          box-shadow: 0 1px 2px rgba(0,0,0,0.05);
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .card-icon { font-size: 1.5rem; }
        .card h3 {
          margin: 0;
          font-size: 0.9rem;
          letter-spacing: 0.5px;
          text-transform: uppercase;
          font-weight: 700;
          color: #1f2937;
        }
        .card p {
          margin: 0;
          font-size: 0.8rem;
          line-height: 1.3;
          color: #6b7280;
        }
        .note {
          display: flex;
          gap: 16px;
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          border-radius: 12px;
          padding: 20px 22px;
          align-items: flex-start;
        }
        .note-icon { font-size: 1.75rem; line-height: 1; }
        .note-body h4 {
          margin: 0 0 6px 0;
          font-size: 1rem;
          color: #1e3a8a;
          font-weight: 600;
        }
        .note-body p {
          margin: 0;
          font-size: 0.9rem;
          color: #1e40af;
          line-height: 1.5;
        }
        .link { color: #2563eb; text-decoration: underline; }
        .link:hover { color: #1d4ed8; }
        @media (max-width: 768px) {
          .individual-container { padding: 16px; }
          .header-inner h1 { font-size: 2rem; }
          .section-title { font-size: 1.25rem; }
          .cards { grid-template-columns: repeat(auto-fit,minmax(140px,1fr)); }
        }
      `}</style>
    </div>
  );
}
