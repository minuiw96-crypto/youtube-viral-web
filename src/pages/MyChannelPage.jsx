import { useEffect, useMemo, useState } from 'react'
import Sidebar from '../components/Sidebar'
import ScoreGauge from '../components/ScoreGauge'
import { getChannelVideos } from '../api/client'
import { formatCategory } from '../utils/categoryLabels'

const SUBSCRIBER_TIERS = [
  {
    label: '1천 ~ 1만',
    channels: [
      { name: '예시채널 A', subscribers: '5천' },
      { name: '예시채널 B', subscribers: '8천' },
    ],
  },
  {
    label: '1만 ~ 10만',
    channels: [
      { name: '예시채널 C', subscribers: '4만' },
      { name: '예시채널 D', subscribers: '7만' },
    ],
  },
  {
    label: '10만 ~ 50만',
    channels: [
      { name: '예시채널 E', subscribers: '20만' },
      { name: '예시채널 F', subscribers: '35만' },
    ],
  },
  {
    label: '50만 ~ 100만',
    channels: [
      { name: '예시채널 G', subscribers: '60만' },
      { name: '예시채널 H', subscribers: '90만' },
    ],
  },
  {
    label: '100만+',
    channels: [
      { name: '예시채널 I', subscribers: '150만' },
      { name: '예시채널 J', subscribers: '300만' },
    ],
  },
]

function formatNumber(n) {
  const num = typeof n === 'string' ? Number(n) : n
  return typeof num === 'number' && Number.isFinite(num) ? num.toLocaleString('ko-KR') : '-'
}

export default function MyChannelPage() {
  const [videos, setVideos] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState(null)

  useEffect(() => {
    let cancelled = false
    getChannelVideos()
      .then((data) => {
        if (!cancelled) setVideos(data.videos || data.video_list || [])
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || '채널 영상을 불러오지 못했습니다.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const sorted = useMemo(() => {
    if (!videos) return []
    return videos.slice().sort((a, b) => (b.viral_score ?? -Infinity) - (a.viral_score ?? -Infinity))
  }, [videos])

  const selected = useMemo(() => {
    if (sorted.length === 0) return null
    return sorted.find((v) => (v.video_id || v.id) === selectedId) || sorted[0]
  }, [sorted, selectedId])

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <div className="dashboard-main">
        <div className="container">
          <div className="channel-tier-card">
            <div className="channel-tier-head">
              <h2>구독자 수 분류별 모니터링 채널 추천</h2>
              <span className="channel-tier-caption">예시 데이터입니다.</span>
            </div>
            <div className="channel-tier-grid">
              {SUBSCRIBER_TIERS.map((tier) => (
                <div className="channel-tier-col" key={tier.label}>
                  <span className="channel-tier-label">{tier.label}</span>
                  {tier.channels.map((ch) => (
                    <div className="similar-channel" key={ch.name}>
                      <span className="channel-avatar-placeholder" />
                      <div className="channel-tier-info">
                        <span>{ch.name}</span>
                        <span className="channel-tier-subs">구독자 {ch.subscribers}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>

          <div className="my-video-card">
            <div className="my-video-head">
              <h2>내 영상 목록</h2>
              <span className="channel-tier-caption">스코어가 높은 순으로 정렬됩니다.</span>
            </div>

            {loading && <p className="dashboard-status">영상을 불러오는 중...</p>}
            {!loading && error && <div className="form-error dashboard-status">{error}</div>}
            {!loading && !error && sorted.length === 0 && (
              <p className="dashboard-status">아직 표시할 영상이 없습니다.</p>
            )}

            {!loading && !error && sorted.length > 0 && (
              <div className="my-video-layout">
                <div className="my-video-list">
                  {sorted.map((v, i) => {
                    const id = v.video_id || v.id || i
                    const active = selected && (selected.video_id || selected.id || sorted.indexOf(selected)) === id
                    return (
                      <button
                        type="button"
                        key={id}
                        className={`my-video-row ${active ? 'active' : ''}`}
                        onClick={() => setSelectedId(id)}
                      >
                        {v.thumbnail_url && <img src={v.thumbnail_url} alt="" className="rank-thumb" />}
                        <span className="my-video-row-title">{v.title || '제목 없음'}</span>
                        <span className="my-video-row-score">
                          {typeof v.viral_score === 'number' ? v.viral_score.toFixed(1) : '-'}
                        </span>
                      </button>
                    )
                  })}
                </div>

                {selected && (
                  <div className="video-detail-head my-video-detail">
                    {selected.thumbnail_url && (
                      <img src={selected.thumbnail_url} alt="" className="video-detail-thumb" />
                    )}
                    <div className="video-detail-meta">
                      {selected.category && (
                        <span className="category-pill">{formatCategory(selected.category)}</span>
                      )}
                      <h2>{selected.title || '제목 없음'}</h2>
                      <ScoreGauge score={selected.viral_score} />
                      {typeof selected.view_count === 'number' && (
                        <span className="dashboard-status">조회수 {formatNumber(selected.view_count)}회</span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
