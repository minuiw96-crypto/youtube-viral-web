import { useEffect, useMemo, useState } from 'react'
import Sidebar from '../components/Sidebar'
import ScoreGauge from '../components/ScoreGauge'
import { getVideoRanking } from '../api/client'
import { formatCategory } from '../utils/categoryLabels'
import { formatSubscriberCount } from '../utils/numberFormat'

const RANK_LABELS = ['gold', 'silver', 'bronze']
const RANK_IMAGE_URLS = [
  'https://res-static.noxinfluencer.com/kol20/2026/08/public/img/rank1.f0c1a4fb79352929b918f2921e8ba058.png',
  'https://res-static.noxinfluencer.com/kol20/2026/08/public/img/rank2.5ebf5808f26db7ca00ca24c859109d81.png',
  'https://res-static.noxinfluencer.com/kol20/2026/08/public/img/rank3.2c9a17ec5beede48a64a72b6c3b00e75.png',
]
const RANK_STYLES = [
  { key: 'crown', label: '왕관' },
  { key: 'medal', label: '메달' },
  { key: 'image', label: '랭크 이미지' },
  { key: 'chip', label: '번호 칩' },
  { key: 'flag', label: '리본' },
  { key: 'minimal', label: '미니멀' },
]

function getSubscriberCount(video) {
  return video.subscriber_count
    ?? video.channel_subscriber_count
    ?? video.subscribers
    ?? video.channel?.subscriber_count
    ?? video.channel_data?.subscriber_count
}

function RankBadge({ index, style = 'medal' }) {
  if (index > 2) return <span className="rank-number">{index + 1}</span>
  if (style === 'image') {
    return (
      <img
        className="rank-image-badge"
        src={RANK_IMAGE_URLS[index]}
        alt={`${index + 1}위`}
        referrerPolicy="no-referrer"
      />
    )
  }
  if (style === 'crown') {
    return (
      <svg className={`rank-crown ${RANK_LABELS[index]}`} viewBox="0 0 24 20" fill="currentColor" aria-label={`${index + 1}위`}>
        <path d="M2 18 L1 7 L7 11 L12 3 L17 11 L23 7 L22 18 Z" />
      </svg>
    )
  }
  return (
    <span className={`rank-badge rank-badge-${style} ${RANK_LABELS[index]}`} aria-label={`${index + 1}위`}>
      <i />
      <b>{index + 1}</b>
    </span>
  )
}

export default function HomePage() {
  const [videos, setVideos] = useState(null)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [rankStyle, setRankStyle] = useState('medal')
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
                  <p>전체 {videos.length.toLocaleString('ko-KR')}개 중 검색 결과 {filteredVideos.length.toLocaleString('ko-KR')}개 · 상위 {top10.length}개 표시</p>
                </div>
                <div className="rank-style-picker" aria-label="상위 순위 디자인 선택">
                  {RANK_STYLES.map((item) => (
                    <button key={item.key} type="button" className={rankStyle === item.key ? 'active' : ''} onClick={() => setRankStyle(item.key)}>
                      <RankBadge index={0} style={item.key} />
                      <span>{item.label}</span>
                    </button>
                  ))}
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
                            <RankBadge index={i} style={rankStyle} />
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
