import { useState } from 'react'
import AuthedNavBar from '../components/AuthedNavBar'
import ScoreGauge from '../components/ScoreGauge'

const EXAMPLE_VIDEO = {
  title: '콩 몰래 먹기 걸리면 황천길',
  category: '먹방',
  thumbnail_url: 'https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg',
  viral_score: 91.2,
}

const CHANNEL_GROUPS = [
  { label: '1일 1개 이상', channels: ['예시채널 A', '예시채널 B', '예시채널 C'] },
  { label: '1일 5개 이상', channels: ['예시채널 D', '예시채널 E', '예시채널 F'] },
  { label: '5일 50개 미만', channels: ['예시채널 G', '예시채널 H', '예시채널 I'] },
  { label: '500~1000개', channels: ['예시채널 J', '예시채널 K', '예시채널 L'] },
  { label: '1000개 이상', channels: ['예시채널 M', '예시채널 N', '예시채널 O'] },
]

const SCATTER_POINTS = [
  { x: 60, y: 40, category: '먹방' },
  { x: 130, y: 90, category: '먹방' },
  { x: 210, y: 60, category: '게임' },
  { x: 260, y: 130, category: '게임' },
  { x: 320, y: 45, category: '요리' },
  { x: 380, y: 100, category: '뷰티' },
]

export default function VideoDetailPage() {
  const [tab, setTab] = useState('similar')

  return (
    <div className="dashboard-shell">
      <AuthedNavBar />
      <div className="container">
        <div className="video-detail-head">
          <img src={EXAMPLE_VIDEO.thumbnail_url} alt="" className="video-detail-thumb" />
          <div className="video-detail-meta">
            <span className="category-pill">{EXAMPLE_VIDEO.category}</span>
            <h2>{EXAMPLE_VIDEO.title}</h2>
            <ScoreGauge score={EXAMPLE_VIDEO.viral_score} />
          </div>
        </div>

        <div className="tab-bar">
          <button
            type="button"
            className={`tab-btn ${tab === 'similar' ? 'active' : ''}`}
            onClick={() => setTab('similar')}
          >
            비슷한 채널
          </button>
          <button
            type="button"
            className={`tab-btn ${tab === 'positioning' ? 'active' : ''}`}
            onClick={() => setTab('positioning')}
          >
            카테고리 포지셔닝
          </button>
        </div>

        {tab === 'similar' && (
          <div className="similar-groups">
            {CHANNEL_GROUPS.map((group) => (
              <div className="similar-group" key={group.label}>
                <span className="similar-group-label">{group.label}</span>
                <div className="similar-channels">
                  {group.channels.map((name) => (
                    <div className="similar-channel" key={name}>
                      <span className="channel-avatar-placeholder" />
                      <span>{name}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === 'positioning' && (
          <div className="positioning-card">
            <svg viewBox="0 0 420 160" className="positioning-chart">
              <line x1="20" y1="140" x2="410" y2="140" stroke="var(--border)" strokeWidth="1" />
              <line x1="20" y1="10" x2="20" y2="140" stroke="var(--border)" strokeWidth="1" />
              {SCATTER_POINTS.map((p, i) => (
                <circle key={i} cx={p.x} cy={160 - p.y} r="7" fill="var(--accent)" opacity="0.75" />
              ))}
              <text x="20" y="155" className="chart-axis-label">카테고리</text>
              <text x="4" y="14" className="chart-axis-label">조회수</text>
            </svg>
            <p className="chart-note">예시 데이터입니다.</p>
          </div>
        )}
      </div>
    </div>
  )
}
