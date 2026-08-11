import { useEffect, useMemo, useState } from 'react'
import Sidebar from '../components/Sidebar'
import DashboardHeader from '../components/DashboardHeader'
import ScoreGauge from '../components/ScoreGauge'
import { getChannelSummary, getChannelVideos, getVideoRanking } from '../api/client'
import { formatCategory } from '../utils/categoryLabels'

const TIERS = [
  { key: 'tier1', label: '1천~1만', min: 1000, max: 9999 },
  { key: 'tier2', label: '1만~10만', min: 10000, max: 99999 },
  { key: 'tier3', label: '10만~50만', min: 100000, max: 499999 },
  { key: 'tier4', label: '50만~100만', min: 500000, max: 999999 },
  { key: 'tier5', label: '100만+', min: 1000000, max: Infinity },
]

function number(value) {
  if (value === null || value === undefined || value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function compact(value) {
  const parsed = number(value)
  if (parsed === null) return '-'
  return new Intl.NumberFormat('ko-KR', { notation: 'compact', maximumFractionDigits: 1 }).format(parsed)
}

function percent(value) {
  const parsed = number(value)
  return parsed === null ? '-' : `${parsed.toFixed(2)}%`
}

function categoryKey(value) {
  return String(value || '').trim().toUpperCase().replace(/^[A-Z]{2}_/, '')
}

function videoEngagement(video) {
  const provided = number(video.engagement_rate)
  if (provided !== null) return provided
  const views = number(video.view_count)
  const likes = number(video.like_count)
  const comments = number(video.comment_count)
  if (!views || likes === null || comments === null) return null
  return ((likes + comments) / views) * 100
}

function ChannelAvatar({ channel, className = '' }) {
  if (channel?.thumbnail) return <img className={className} src={channel.thumbnail} alt="" />
  return <span className={`channel-avatar-fallback ${className}`.trim()}>{channel?.name?.slice(0, 1) || 'P'}</span>
}

export default function MyChannelPage({ view = 'benchmark' }) {
  const [summary, setSummary] = useState(null)
  const [videos, setVideos] = useState([])
  const [ranking, setRanking] = useState([])
  const [tier, setTier] = useState('tier3')
  const [selectedChannelId, setSelectedChannelId] = useState(null)
  const [selectedVideoId, setSelectedVideoId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([getChannelSummary(), getChannelVideos(), getVideoRanking()])
      .then(([summaryData, videoData, rankData]) => {
        if (!active) return
        const nextSummary = summaryData.summary || summaryData.channel || summaryData
        const subscribers = number(nextSummary?.subscriber_count)
        const currentTier = TIERS.find((item) => subscribers !== null && subscribers >= item.min && subscribers <= item.max)
        setSummary(nextSummary)
        if (currentTier) setTier(currentTier.key)
        setVideos(videoData.videos || videoData.video_list || [])
        setRanking(rankData.video_ranking || [])
      })
      .catch((err) => active && setError(err.message || '채널 데이터를 불러오지 못했습니다.'))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [])

  const projectCategory = summary?.project_category
    || videos.find((video) => video.project_category || video.content_domain)?.project_category
    || videos.find((video) => video.content_domain)?.content_domain
  const categoryLabel = formatCategory(projectCategory)

  const categoryRanking = useMemo(() => {
    if (!projectCategory) return []
    return ranking.filter((item) => categoryKey(item.category || item.project_category) === categoryKey(projectCategory))
  }, [ranking, projectCategory])

  const channels = useMemo(() => {
    const map = new Map()
    categoryRanking.forEach((item) => {
      if (!item.channel_id) return
      const score = number(item.viral_score)
      const existing = map.get(item.channel_id) || {
        id: item.channel_id,
        name: item.channel_title || item.channel_name || '채널명 없음',
        thumbnail: item.channel_thumbnail_url,
        subscribers: number(item.subscriber_count),
        scores: [],
        topVideo: null,
      }
      if (score !== null) {
        existing.scores.push(score)
        if (!existing.topVideo || score > number(existing.topVideo.viral_score)) existing.topVideo = item
      }
      if (existing.subscribers === null) existing.subscribers = number(item.subscriber_count)
      map.set(item.channel_id, existing)
    })
    return [...map.values()].map((item) => ({
      ...item,
      averageScore: item.scores.length ? item.scores.reduce((sum, score) => sum + score, 0) / item.scores.length : null,
    }))
  }, [categoryRanking])

  const tierChannels = useMemo(() => {
    const current = TIERS.find((item) => item.key === tier) || TIERS[0]
    return channels
      .filter((item) => item.id !== summary?.channel_id && item.subscribers !== null && item.subscribers >= current.min && item.subscribers <= current.max)
      .sort((a, b) => (b.averageScore ?? -1) - (a.averageScore ?? -1) || (b.subscribers ?? 0) - (a.subscribers ?? 0))
      .slice(0, 5)
  }, [channels, summary?.channel_id, tier])

  const topChannels = useMemo(() => channels
    .filter((item) => item.averageScore !== null)
    .sort((a, b) => b.averageScore - a.averageScore)
    .slice(0, 3), [channels])
  const selectedChannel = topChannels.find((item) => item.id === selectedChannelId) || topChannels[0]

  const performanceVideos = useMemo(() => videos
    .map((video) => ({ ...video, engagement: videoEngagement(video) }))
    .filter((video) => number(video.view_count) !== null && video.engagement !== null)
    .sort((a, b) => (number(b.view_count) ?? 0) - (number(a.view_count) ?? 0))
    .slice(0, 20), [videos])
  const selectedVideo = performanceVideos.find((video) => (video.video_id || video.id) === selectedVideoId) || performanceVideos[0]

  const chartPoints = useMemo(() => {
    if (!performanceVideos.length) return []
    const logs = performanceVideos.map((video) => Math.log10(Math.max(1, number(video.view_count))))
    const minLog = Math.min(...logs)
    const maxLog = Math.max(...logs)
    const maxEngagement = Math.max(1, ...performanceVideos.map((video) => video.engagement))
    return performanceVideos.map((video, index) => {
      const x = 8 + ((logs[index] - minLog) / (maxLog - minLog || 1)) * 84
      const y = 8 + (video.engagement / maxEngagement) * 84
      const score = number(video.viral_score)
      return { video, x, y, size: 24 + Math.min(18, (score ?? 30) / 5) }
    })
  }, [performanceVideos])

  const ownScores = videos.map((video) => number(video.viral_score)).filter((score) => score !== null)
  const ownAverageScore = ownScores.length ? ownScores.reduce((sum, score) => sum + score, 0) / ownScores.length : null

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main dashboard-page">
        <DashboardHeader
          title={view === 'performance' ? '영상 성과 분석' : `${categoryLabel === '-' ? '내 카테고리' : categoryLabel} 유튜브`}
          description={view === 'performance'
            ? '조회수와 참여율을 기준으로 내 영상의 성과 위치를 확인하세요.'
            : `${categoryLabel === '-' ? '연결 채널' : categoryLabel} 카테고리의 추천 채널과 평균 점수를 비교합니다.`}
        />

        {loading && <div className="panel-state"><span className="loading-spinner" />채널 데이터를 불러오는 중입니다.</div>}
        {!loading && error && <div className="panel-state error-state">{error}</div>}

        {!loading && !error && view === 'benchmark' && (
          <>
            <section className="channel-hero-card">
              <div className="channel-identity">
                {summary?.channel_thumbnail_url ? <img src={summary.channel_thumbnail_url} alt="" /> : <span className="channel-avatar-fallback">P</span>}
                <div>
                  <h2>{summary?.channel_title || summary?.channel_name || '내 YouTube 채널'}</h2>
                  <p>{categoryLabel} 카테고리</p>
                </div>
              </div>
              <div className="channel-kpis">
                <div><span>구독자</span><strong>{compact(summary?.subscriber_count)}</strong></div>
                <div><span>누적 조회수</span><strong>{compact(summary?.total_view_count)}</strong></div>
                <div><span>평균 점수</span><strong>{ownAverageScore === null ? '-' : ownAverageScore.toFixed(1)}</strong></div>
              </div>
            </section>

            <section className="report-panel benchmark-section">
              <div className="panel-heading">
                <div><h2>구독자 수 분류별 모니터링 채널 추천</h2><p>내 채널과 비슷한 규모의 {categoryLabel} 채널을 확인해 보세요.</p></div>
              </div>
              <div className="tier-tabs" role="tablist" aria-label="구독자 수 구간">
                {TIERS.map((item) => (
                  <button key={item.key} type="button" role="tab" aria-selected={tier === item.key} className={tier === item.key ? 'active' : ''} onClick={() => setTier(item.key)}>{item.label}</button>
                ))}
              </div>
              {tierChannels.length ? (
                <div className="benchmark-grid">
                  {tierChannels.map((item) => (
                    <article className="benchmark-card" key={item.id}>
                      <ChannelAvatar channel={item} />
                      <div><h3>{item.name}</h3><p>구독자 {compact(item.subscribers)}</p></div>
                      <strong>평균 {item.averageScore === null ? '-' : item.averageScore.toFixed(1)}점</strong>
                    </article>
                  ))}
                </div>
              ) : <div className="compact-empty">이 구독자 구간에 추천할 {categoryLabel} 채널이 없습니다.</div>}
            </section>

            <section className="report-panel top-channel-section">
              <div className="panel-heading">
                <div><h2>평균 점수 높은 채널</h2><p>{categoryLabel} 카테고리에서 평균 바이럴 점수가 높은 TOP 3입니다.</p></div>
              </div>
              {topChannels.length ? (
                <div className="top-channel-showcase">
                  <div className="top-channel-list">
                    {topChannels.map((item, index) => (
                      <button key={item.id} type="button" className={selectedChannel === item ? 'active' : ''} onClick={() => setSelectedChannelId(item.id)}>
                        <span className="top-channel-rank">{index + 1}</span>
                        <ChannelAvatar channel={item} />
                        <span className="top-channel-copy"><strong>{item.name}</strong><small>구독자 {compact(item.subscribers)}</small></span>
                        <b>{item.averageScore.toFixed(1)}</b>
                      </button>
                    ))}
                  </div>
                  <article className="top-video-card">
                    {selectedChannel?.topVideo?.thumbnail_url ? <img src={selectedChannel.topVideo.thumbnail_url} alt="" /> : <div className="top-video-fallback">영상 미리보기</div>}
                    <div className="top-video-content">
                      <div className="top-video-channel"><ChannelAvatar channel={selectedChannel} /><span><strong>{selectedChannel?.name}</strong><small>채널 최고 점수 영상</small></span></div>
                      <h3>{selectedChannel?.topVideo?.title || '영상 제목 정보가 없습니다.'}</h3>
                      <dl>
                        <div><dt>바이럴 점수</dt><dd>{number(selectedChannel?.topVideo?.viral_score)?.toFixed(1) || '-'}</dd></div>
                        <div><dt>채널 평균 점수</dt><dd>{selectedChannel?.averageScore?.toFixed(1) || '-'}</dd></div>
                        <div><dt>평균 조회수</dt><dd>{compact(selectedChannel?.topVideo?.avg_view_count)}</dd></div>
                      </dl>
                    </div>
                  </article>
                </div>
              ) : <div className="compact-empty">평균 점수를 계산할 {categoryLabel} 채널 데이터가 없습니다.</div>}
            </section>
          </>
        )}

        {!loading && !error && view === 'performance' && (
          <div className="performance-layout">
            <section className="report-panel performance-map-card">
              <div className="panel-heading"><div><h2>영상 성과 분포</h2><p>조회수 대비 좋아요와 댓글의 참여율을 비교합니다.</p></div></div>
              {chartPoints.length ? (
                <div className="bubble-chart" aria-label="조회수와 참여율 기준 영상 성과 분포 차트">
                  <span className="axis-label axis-y">참여율</span>
                  <span className="axis-label axis-x">조회수</span>
                  <span className="chart-zone-label">반응과 확장성이 높은 영역</span>
                  {chartPoints.map(({ video, x, y, size }, index) => (
                    <button
                      key={video.video_id || index}
                      type="button"
                      className={`video-bubble ${selectedVideo === video ? 'active' : ''}`}
                      style={{ left: `${x}%`, bottom: `${y}%`, '--bubble-size': `${size}px` }}
                      onClick={() => setSelectedVideoId(video.video_id || video.id)}
                      title={`${video.title || `영상 ${index + 1}`} · 조회수 ${compact(video.view_count)} · 참여율 ${percent(video.engagement)}`}
                      aria-label={video.title || `영상 ${index + 1}`}
                    />
                  ))}
                </div>
              ) : <div className="compact-empty">조회수와 참여율을 계산할 영상 데이터가 없습니다.</div>}
            </section>

            <aside className="report-panel video-insight-panel">
              <h2>선택 영상 정보</h2>
              {selectedVideo ? (
                <>
                  {selectedVideo.thumbnail_url && <img className="insight-thumbnail" src={selectedVideo.thumbnail_url} alt="" />}
                  <h3>{selectedVideo.title || '제목 없음'}</h3>
                  <ScoreGauge score={number(selectedVideo.viral_score)} />
                  <dl>
                    <div><dt>조회수</dt><dd>{compact(selectedVideo.view_count)}</dd></div>
                    <div><dt>좋아요</dt><dd>{compact(selectedVideo.like_count)}</dd></div>
                    <div><dt>댓글</dt><dd>{compact(selectedVideo.comment_count)}</dd></div>
                    <div><dt>참여율</dt><dd>{percent(selectedVideo.engagement)}</dd></div>
                    <div><dt>카테고리</dt><dd>{formatCategory(selectedVideo.content_domain || selectedVideo.project_category || projectCategory)}</dd></div>
                  </dl>
                </>
              ) : <div className="compact-empty">선택할 영상이 없습니다.</div>}
            </aside>
          </div>
        )}
      </main>
    </div>
  )
}
