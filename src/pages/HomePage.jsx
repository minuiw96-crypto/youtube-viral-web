import { useEffect, useState } from 'react'
import AuthedNavBar from '../components/AuthedNavBar'
import ScoreGauge from '../components/ScoreGauge'
import { getChannelSummary } from '../api/client'

function formatNumber(n) {
  return typeof n === 'number' ? n.toLocaleString('ko-KR') : '-'
}

function formatPercent(n) {
  if (typeof n !== 'number') return '-'
  // 응답이 비율(0.12)인지 이미 퍼센트(12.3)인지 백엔드 확인 전이라 12 이하일 때만 100을 곱함
  const pct = Math.abs(n) <= 1 ? n * 100 : n
  return `${pct.toFixed(1)}%`
}

const RANK_LABELS = ['gold', 'silver', 'bronze']

export default function HomePage() {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    getChannelSummary()
      .then((data) => {
        if (!cancelled) setSummary(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || '채널 데이터를 불러오지 못했습니다.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const videos = summary?.recent_videos || []
  const top3 = videos.slice(0, 3)
  const rest = videos.slice(3)

  return (
    <div className="dashboard-shell">
      <AuthedNavBar />

      <div className="container">
        {loading && <p className="dashboard-status">채널 데이터를 불러오는 중...</p>}
        {!loading && error && <div className="form-error dashboard-status">{error}</div>}

        {!loading && !error && summary && (
          <>
            <div className="kpi-grid">
              <div className="kpi-card">
                <span className="kpi-label">구독자 수</span>
                <span className="kpi-value">{formatNumber(summary.subscriber_count)}</span>
              </div>
              <div className="kpi-card">
                <span className="kpi-label">총 조회수</span>
                <span className="kpi-value">{formatNumber(summary.view_count)}</span>
              </div>
              <div className="kpi-card">
                <span className="kpi-label">성장률</span>
                <span className="kpi-value">{formatPercent(summary.growth_rate)}</span>
              </div>
              <div className="kpi-card">
                <span className="kpi-label">참여도</span>
                <span className="kpi-value">{formatPercent(summary.engagement_rate)}</span>
              </div>
            </div>

            {top3.length > 0 && (
              <div className="rank-list">
                {top3.map((video, i) => (
                  <div className={`rank-item ${RANK_LABELS[i]}`} key={video.video_id || i}>
                    <span className="rank-number">{i + 1}</span>
                    {video.thumbnail_url && (
                      <img src={video.thumbnail_url} alt="" className="rank-thumb" />
                    )}
                    <span className="rank-title">{video.title || '제목 없음'}</span>
                    <ScoreGauge score={video.viral_score} />
                  </div>
                ))}
              </div>
            )}

            {rest.length > 0 && (
              <div className="video-grid">
                {rest.map((video, i) => (
                  <div className="video-card" key={video.video_id || i}>
                    {video.thumbnail_url && (
                      <img src={video.thumbnail_url} alt="" className="video-thumb" />
                    )}
                    <span className="video-title">{video.title || '제목 없음'}</span>
                    <ScoreGauge score={video.viral_score} />
                  </div>
                ))}
              </div>
            )}

            {videos.length === 0 && (
              <p className="dashboard-status">아직 표시할 영상 데이터가 없습니다.</p>
            )}

            <div className="predict-cta">
              <div>
                <h3>영상이 뜨기 전에 미리 확인하세요</h3>
                <p>유튜브 URL을 입력하면 바이럴 스코어를 바로 예측해드려요.</p>
              </div>
              <button type="button" className="btn btn-outline" disabled>
                곧 지원 예정
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
