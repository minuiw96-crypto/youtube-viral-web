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
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function compact(value) {
  const parsed = number(value)
  if (parsed === null) return '-'
  return new Intl.NumberFormat('ko-KR', { notation: 'compact', maximumFractionDigits: 1 }).format(parsed)
}

function pct(value) {
  const parsed = number(value)
  return parsed === null ? '-' : `${parsed > 0 ? '+' : ''}${parsed.toFixed(1)}%`
}

export default function MyChannelPage({ view = 'benchmark' }) {
  const [summary, setSummary] = useState(null)
  const [videos, setVideos] = useState([])
  const [ranking, setRanking] = useState([])
  const [tier, setTier] = useState('tier3')
  const [selectedId, setSelectedId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([getChannelSummary(), getChannelVideos(), getVideoRanking()])
      .then(([summaryData, videoData, rankData]) => {
        if (!active) return
        setSummary(summaryData.summary || summaryData.channel || summaryData)
        setVideos(videoData.videos || videoData.video_list || [])
        setRanking(rankData.video_ranking || [])
      })
      .catch((err) => active && setError(err.message || '채널 데이터를 불러오지 못했습니다.'))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [])

  const category = videos.find((video) => video.category)?.category || summary?.category
  const categoryLabel = category ? formatCategory(category) : '전체 카테고리'

  const categoryRanking = useMemo(() => {
    const filtered = category ? ranking.filter((item) => item.category === category) : ranking
    return filtered.length ? filtered : ranking
  }, [ranking, category])

  const channels = useMemo(() => {
    const map = new Map()
    categoryRanking.forEach((item) => {
      if (!item.channel_id) return
      const existing = map.get(item.channel_id) || {
        id: item.channel_id,
        name: item.channel_title || item.channel_name || '채널명 없음',
        thumbnail: item.channel_thumbnail_url,
        subscribers: number(item.subscriber_count),
        scores: [],
      }
      const score = number(item.viral_score)
      if (score !== null) existing.scores.push(score)
      map.set(item.channel_id, existing)
    })
    return [...map.values()].map((item) => ({
      ...item,
      score: item.scores.length ? item.scores.reduce((a, b) => a + b, 0) / item.scores.length : null,
    }))
  }, [categoryRanking])

  const tierChannels = useMemo(() => {
    const current = TIERS.find((item) => item.key === tier)
    return channels.filter((item) => item.subscribers !== null && item.subscribers >= current.min && item.subscribers <= current.max)
  }, [channels, tier])

  const topVideos = useMemo(() => videos.slice().sort((a, b) => (number(b.viral_score) ?? -1) - (number(a.viral_score) ?? -1)), [videos])
  const selectedVideo = topVideos.find((video) => (video.video_id || video.id) === selectedId) || topVideos[0]
  const best = topVideos[0]

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main dashboard-page">
        <DashboardHeader
          title={view === 'performance' ? '영상 성과 분석' : '채널 벤치마크'}
          description={view === 'performance'
            ? '내 영상의 조회수와 바이럴 스코어 분포를 확인하세요.'
            : `${categoryLabel} 시장 안에서 내 채널의 위치를 확인하세요.`}
        />

        {loading && <div className="panel-state"><span className="loading-spinner" />채널 데이터를 불러오는 중입니다.</div>}
        {!loading && error && <div className="panel-state error-state">{error}</div>}

        {!loading && !error && view === 'benchmark' && (
          <>
            <section className="channel-hero-card">
              <div className="channel-identity">
                {summary?.thumbnail_url || summary?.channel_thumbnail_url ? (
                  <img src={summary.thumbnail_url || summary.channel_thumbnail_url} alt="" />
                ) : <span className="channel-avatar-fallback">P</span>}
                <div>
                  <span className="section-kicker">MY CHANNEL</span>
                  <h2>{summary?.channel_title || summary?.title || summary?.channel_name || '내 YouTube 채널'}</h2>
                  <p>{categoryLabel}</p>
                </div>
              </div>
              <div className="channel-kpis">
                <div><span>구독자</span><strong>{compact(summary?.subscriber_count)}</strong></div>
                <div><span>누적 조회수</span><strong>{compact(summary?.view_count || summary?.total_view_count)}</strong></div>
                <div><span>평균 스코어</span><strong>{best && number(best.viral_score) !== null ? number(best.viral_score).toFixed(1) : '-'}</strong></div>
              </div>
            </section>

            <section className="report-panel">
              <div className="panel-heading">
                <div><span className="section-kicker">BENCHMARK</span><h2>구독자 규모별 비교 채널</h2></div>
                <p>{categoryLabel === '전체 카테고리' ? categoryLabel : `${categoryLabel} 카테고리`}</p>
              </div>
              <div className="tier-tabs">
                {TIERS.map((item) => (
                  <button key={item.key} type="button" className={tier === item.key ? 'active' : ''} onClick={() => setTier(item.key)}>{item.label}</button>
                ))}
              </div>
              {tierChannels.length ? (
                <div className="benchmark-grid">
                  {tierChannels.slice(0, 5).map((item, index) => (
                    <article className="benchmark-card" key={item.id}>
                      <span className="benchmark-rank">{String(index + 1).padStart(2, '0')}</span>
                      {item.thumbnail ? <img src={item.thumbnail} alt="" /> : <span className="channel-avatar-fallback">{item.name.slice(0, 1)}</span>}
                      <div><h3>{item.name}</h3><p>구독자 {compact(item.subscribers)}</p></div>
                      <strong>{item.score === null ? '-' : item.score.toFixed(1)}</strong>
                    </article>
                  ))}
                </div>
              ) : <div className="compact-empty">현재 수집된 랭킹에는 이 구간의 비교 채널이 없습니다.</div>}
            </section>
          </>
        )}

        {!loading && !error && view === 'performance' && (
          <div className="performance-layout">
            <section className="report-panel performance-map-card">
              <div className="panel-heading"><div><span className="section-kicker">VIDEO MAP</span><h2>영상 성과 분포</h2></div><p>조회수 대비 바이럴 스코어</p></div>
              {topVideos.length ? (
                <div className="bubble-chart" aria-label="영상 성과 분포 차트">
                  <span className="axis-label axis-y">바이럴 스코어</span>
                  <span className="axis-label axis-x">조회수</span>
                  {topVideos.slice(0, 8).map((video, index) => {
                    const score = Math.max(8, Math.min(96, number(video.viral_score) ?? 10))
                    const views = Math.max(8, Math.min(92, Math.log10(Math.max(10, number(video.view_count) ?? 10)) * 15))
                    return <button key={video.video_id || index} type="button" className={`video-bubble ${selectedVideo === video ? 'active' : ''}`} style={{ left: `${views}%`, bottom: `${score}%`, '--bubble-size': `${34 + Math.min(score, 80) / 2}px` }} onClick={() => setSelectedId(video.video_id || video.id)} aria-label={video.title || `영상 ${index + 1}`} />
                  })}
                </div>
              ) : <div className="compact-empty">분석할 영상 데이터가 없습니다.</div>}
            </section>

            <aside className="report-panel video-insight-panel">
              <span className="section-kicker">SELECTED VIDEO</span>
              {selectedVideo ? (
                <>
                  {selectedVideo.thumbnail_url && <img className="insight-thumbnail" src={selectedVideo.thumbnail_url} alt="" />}
                  <h2>{selectedVideo.title || '제목 없음'}</h2>
                  <ScoreGauge score={number(selectedVideo.viral_score)} />
                  <dl>
                    <div><dt>조회수</dt><dd>{compact(selectedVideo.view_count)}</dd></div>
                    <div><dt>평균 대비 성과</dt><dd>{pct(selectedVideo.performance_multiplier ? (number(selectedVideo.performance_multiplier) - 1) * 100 : null)}</dd></div>
                    <div><dt>카테고리</dt><dd>{formatCategory(selectedVideo.category)}</dd></div>
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
