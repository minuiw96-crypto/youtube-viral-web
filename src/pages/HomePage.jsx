import { useEffect, useMemo, useState } from 'react'
import AuthedNavBar from '../components/AuthedNavBar'
import ScoreGauge from '../components/ScoreGauge'
import { getVideoRanking } from '../api/client'
import { formatCategory } from '../utils/categoryLabels'

const RANK_LABELS = ['gold', 'silver', 'bronze']

function formatNumber(n) {
  return typeof n === 'number' ? n.toLocaleString('ko-KR') : '-'
}

export default function HomePage() {
  const [videos, setVideos] = useState(null)
  const [category, setCategory] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    getVideoRanking()
      .then((data) => {
        if (!cancelled) setVideos(data.video_ranking || [])
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || '영상 데이터를 불러오지 못했습니다.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [refreshKey])

  function handleRefresh() {
    setLoading(true)
    setError('')
    setRefreshKey((k) => k + 1)
  }

  const categories = useMemo(() => {
    if (!videos) return []
    return [...new Set(videos.map((v) => v.category).filter(Boolean))]
  }, [videos])

  const top10 = useMemo(() => {
    if (!videos) return []
    const filtered = category === 'all' ? videos : videos.filter((v) => v.category === category)
    return filtered
      .slice()
      .sort((a, b) => (b.viral_score ?? -Infinity) - (a.viral_score ?? -Infinity))
      .slice(0, 10)
  }, [videos, category])

  return (
    <div className="dashboard-shell">
      <AuthedNavBar />

      <div className="container">
        {loading && <p className="dashboard-status">영상 데이터를 불러오는 중...</p>}
        {!loading && error && <div className="form-error dashboard-status">{error}</div>}
        {!loading && !error && videos && videos.length === 0 && (
          <p className="dashboard-status">아직 표시할 영상 데이터가 없습니다.</p>
        )}

        {!loading && !error && videos && videos.length > 0 && (
          <div className="rank-table-card">
            <div className="rank-table-head">
              <div className="rank-table-title">
                <h2>TOP 10 영상 스코어</h2>
                <span className="rank-table-caption">전체 채널 기준 바이럴 스코어 순위</span>
              </div>
              <div className="rank-table-controls">
                {categories.length > 0 && (
                  <select
                    className="category-select"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                  >
                    <option value="all">전체 카테고리</option>
                    {categories.map((c) => (
                      <option key={c} value={c}>
                        {formatCategory(c)}
                      </option>
                    ))}
                  </select>
                )}
                <button
                  type="button"
                  className="icon-btn"
                  onClick={handleRefresh}
                  aria-label="새로고침"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 12a9 9 0 1 1-2.64-6.36M21 4v6h-6" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="rank-table-scroll">
              <table className="rank-table">
                <thead>
                  <tr>
                    <th>순위</th>
                    <th>영상</th>
                    <th>카테고리</th>
                    <th>유튜브 채널</th>
                    <th>구독자</th>
                    <th>평균 조회수</th>
                    <th>스코어</th>
                  </tr>
                </thead>
                <tbody>
                  {top10.map((video, i) => (
                    <tr key={video.video_id || i}>
                      <td>
                        <span className={`rank-medal ${RANK_LABELS[i] || ''}`}>
                          {i === 0 ? '👑' : i + 1}
                        </span>
                      </td>
                      <td>
                        <div className="rank-video-cell">
                          {video.thumbnail_url && (
                            <img src={video.thumbnail_url} alt="" className="rank-thumb" />
                          )}
                          <span className="rank-title">{video.title || '제목 없음'}</span>
                        </div>
                      </td>
                      <td>
                        <span className="category-pill">{formatCategory(video.category)}</span>
                      </td>
                      <td>
                        <div className="channel-cell">
                          {video.channel_thumbnail_url && (
                            <img
                              src={video.channel_thumbnail_url}
                              alt=""
                              className="channel-avatar"
                            />
                          )}
                          <span>{video.channel_title || video.channel_name || '-'}</span>
                        </div>
                      </td>
                      <td>{formatNumber(video.subscriber_count)}</td>
                      <td>{formatNumber(video.avg_view_count ?? video.average_view_count)}</td>
                      <td>
                        <ScoreGauge score={video.viral_score} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
