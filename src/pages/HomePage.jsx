import { useEffect, useState } from 'react'
import AuthedNavBar from '../components/AuthedNavBar'
import ScoreGauge from '../components/ScoreGauge'
import { getChannelVideos } from '../api/client'

const RANK_LABELS = ['gold', 'silver', 'bronze']

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
          <div className="rank-list">
            {videos.map((video, i) => (
              <div className={`rank-item ${RANK_LABELS[i] || ''}`} key={video.video_id || i}>
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
      </div>
    </div>
  )
}
