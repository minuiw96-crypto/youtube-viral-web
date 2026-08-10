import { useEffect, useState } from 'react'
import AuthedNavBar from '../components/AuthedNavBar'
import ScoreGauge from '../components/ScoreGauge'
import { getChannelVideos } from '../api/client'

const RANK_LABELS = ['gold', 'silver', 'bronze']

function formatMultiplier(n) {
  return typeof n === 'number' ? `×${n.toFixed(1)}` : '-'
}

export default function HomePage() {
  const [videos, setVideos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    getChannelVideos()
      .then((data) => {
        if (cancelled) return
        const top10 = (data.videos || [])
          .slice()
          .sort((a, b) => (a.rank ?? Infinity) - (b.rank ?? Infinity))
          .slice(0, 10)
        setVideos(top10)
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
  }, [])

  return (
    <div className="dashboard-shell">
      <AuthedNavBar />

      <div className="container">
        {loading && <p className="dashboard-status">영상 데이터를 불러오는 중...</p>}
        {!loading && error && <div className="form-error dashboard-status">{error}</div>}
        {!loading && !error && videos.length === 0 && (
          <p className="dashboard-status">아직 표시할 영상 데이터가 없습니다.</p>
        )}

        {!loading && !error && videos.length > 0 && (
          <div className="rank-table-card">
            <div className="rank-table-head">
              <h2>TOP 10 영상 스코어</h2>
            </div>
            <div className="rank-table-scroll">
              <table className="rank-table">
                <thead>
                  <tr>
                    <th>순위</th>
                    <th>영상</th>
                    <th>성과 배수</th>
                    <th>스코어</th>
                  </tr>
                </thead>
                <tbody>
                  {videos.map((video, i) => (
                    <tr key={video.video_id || i}>
                      <td>
                        <span className={`rank-medal ${RANK_LABELS[i] || ''}`}>{i + 1}</span>
                      </td>
                      <td>
                        <div className="rank-video-cell">
                          {video.thumbnail_url && (
                            <img src={video.thumbnail_url} alt="" className="rank-thumb" />
                          )}
                          <span className="rank-title">{video.title || '제목 없음'}</span>
                        </div>
                      </td>
                      <td>{formatMultiplier(video.performance_multiplier)}</td>
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
