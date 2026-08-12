import { useEffect, useMemo, useState } from 'react'
import Sidebar from '../components/Sidebar'
import ScoreGauge from '../components/ScoreGauge'
import { getVideoRanking } from '../api/client'
import { formatCategory } from '../utils/categoryLabels'
import { formatSubscriberCount } from '../utils/numberFormat'

const RANK_LABELS = ['gold', 'silver', 'bronze']

function getSubscriberCount(video) {
  return video.subscriber_count
    ?? video.channel_subscriber_count
    ?? video.subscribers
    ?? video.channel?.subscriber_count
    ?? video.channel_data?.subscriber_count
}

function getCategoryTone(value) {
  const category = String(value || '').trim().toUpperCase()
  if (category.includes('MUKBANG')) return 'mukbang'
  if (category.includes('GAMING')) return 'gaming'
  return 'default'
}

function RankBadge({ index }) {
  if (index > 2) return <span className="rank-number">{index + 1}</span>
  return (
    <span className={`rank-badge rank-badge-medal ${RANK_LABELS[index]}`} aria-label={`${index + 1}위`}>
      <i />
      <b>{index + 1}</b>
    </span>
  )
}

export default function HomePage() {
  const [videos, setVideos] = useState(null)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

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
  }, [])

  function runSearch() {
    setSearch(searchInput)
  }

  const filteredVideos = useMemo(() => {
    if (!videos) return []
    let filtered = videos.slice()
    const q = search.trim().toLowerCase()
    if (q) {
      filtered = filtered.filter((v) => {
        const categoryLabel = formatCategory(v.category).toLowerCase()
        const channelName = (v.channel_title || v.channel_name || '').toLowerCase()
        const title = (v.title || '').toLowerCase()
        return categoryLabel.includes(q) || channelName.includes(q) || title.includes(q)
      })
    }
    return filtered.sort((a, b) => (Number(b.viral_score) || -Infinity) - (Number(a.viral_score) || -Infinity))
  }, [videos, search])
  const top10 = useMemo(() => filteredVideos.slice(0, 10), [filteredVideos])

  return (
    <div className="dashboard-shell">
      <Sidebar />

      <div className="dashboard-main">
      <div className="container">
        {loading && <p className="dashboard-status">영상 데이터를 불러오는 중...</p>}
        {!loading && error && <div className="form-error dashboard-status">{error}</div>}
        {!loading && !error && videos && videos.length === 0 && (
          <p className="dashboard-status">아직 표시할 영상 데이터가 없습니다.</p>
        )}

        {!loading && !error && videos && videos.length > 0 && (
          <>
            <div className="rank-page-heading">
              <h1>영상 랭킹</h1>
              <p>최근 7일 기준 바이럴 스코어 순위</p>
            </div>
            <div className="rank-search-bar">
              <div className="rank-search-input">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="7" />
                  <path d="M21 21l-4.35-4.35" />
                </svg>
                <input
                  type="text"
                  placeholder="채널명, 카테고리로 검색해보세요"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') runSearch()
                  }}
                />
              </div>
              <button type="button" className="rank-search-btn" onClick={runSearch}>
                검색
              </button>
            </div>

            <div className="rank-table-card">
              <div className="rank-table-head">
                <div className="rank-table-title">
                  <h2>영상 TOP10</h2>
                </div>
              </div>
              {top10.length === 0 ? (
                <p className="dashboard-status">검색 결과가 없습니다.</p>
              ) : (
                <div className="rank-table-scroll">
                  <table className="rank-table">
                    <colgroup>
                      <col className="col-rank" />
                      <col className="col-video" />
                      <col className="col-category" />
                      <col className="col-channel" />
                      <col className="col-subs" />
                      <col className="col-score" />
                    </colgroup>
                    <thead>
                      <tr>
                        <th>순위</th>
                        <th>영상</th>
                        <th>카테고리</th>
                        <th>유튜브 채널</th>
                        <th>구독자</th>
                        <th>스코어</th>
                      </tr>
                    </thead>
                    <tbody>
                      {top10.map((video, i) => (
                        <tr key={video.video_id || i}>
                          <td>
                            <RankBadge index={i} />
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
                            <span className={`category-pill category-pill-${getCategoryTone(video.category || video.project_category)}`}>
                              {formatCategory(video.category || video.project_category)}
                            </span>
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
                          <td>{formatSubscriberCount(getSubscriberCount(video))}</td>
                          <td>
                            <ScoreGauge score={video.viral_score} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}
      </div>
      </div>
    </div>
  )
}
