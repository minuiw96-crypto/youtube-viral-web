import { useState } from 'react'
import Sidebar from '../components/Sidebar'
import DashboardHeader from '../components/DashboardHeader'
import PredictionSemicircleGauge from '../components/PredictionSemicircleGauge'
import { getVideoMetadata, predictFromUrl } from '../api/client'
import predictVideoIcon from '../assets/predict-video-icon.png'

const PREDICTION_CATEGORIES = [
  { value: 'KR_MUKBANG', label: '먹방' },
  { value: 'KR_GAMING', label: '게임' },
]

function valueOf(result, ...keys) {
  for (const key of keys) if (result?.[key] !== undefined && result?.[key] !== null) return result[key]
  return null
}

function titleFromResult(result) {
  return valueOf(result, 'title', 'video_title')
    || valueOf(result?.video, 'title', 'video_title')
    || valueOf(result?.video_data, 'title', 'video_title')
    || valueOf(result?.metadata, 'title', 'video_title')
}

function thumbnailFromResult(result) {
  return valueOf(result, 'thumbnail_url', 'video_thumbnail_url')
    || valueOf(result?.video, 'thumbnail_url', 'video_thumbnail_url')
    || valueOf(result?.video_data, 'thumbnail_url', 'video_thumbnail_url')
    || valueOf(result?.metadata, 'thumbnail_url', 'video_thumbnail_url')
}

function videoIdFromUrl(value) {
  try {
    const parsed = new URL(value)
    const hostname = parsed.hostname.toLowerCase().replace(/^www\./, '')
    if (hostname === 'youtu.be') return parsed.pathname.split('/').filter(Boolean)[0] || ''
    if (hostname === 'youtube.com' || hostname.endsWith('.youtube.com')) {
      if (parsed.pathname === '/watch') return parsed.searchParams.get('v') || ''
      const [route, videoId] = parsed.pathname.split('/').filter(Boolean)
      if (['shorts', 'embed', 'live'].includes(route)) return videoId || ''
    }
  }
  catch {
    return ''
  }
  return ''
}

function directThumbnailUrl(videoId) {
  return videoId ? `https://i.ytimg.com/vi/${encodeURIComponent(videoId)}/hqdefault.jpg` : ''
}

async function fetchYouTubeMetadata(videoUrl) {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), 5000)
  try {
    const endpoint = `https://www.youtube.com/oembed?url=${encodeURIComponent(videoUrl)}&format=json`
    const response = await fetch(endpoint, { signal: controller.signal })
    if (!response.ok) return null
    const metadata = await response.json()
    return {
      title: typeof metadata.title === 'string' ? metadata.title.trim() : '',
      thumbnailUrl: typeof metadata.thumbnail_url === 'string' ? metadata.thumbnail_url : '',
    }
  }
  catch {
    return null
  }
  finally {
    window.clearTimeout(timeoutId)
  }
}

function OrbitVisual({ loading = false }) {
  return (
    <div className={`signal-orbit ${loading ? 'loading' : ''}`} aria-hidden="true">
      <span className="orbit-ring orbit-ring-outer"><i /></span>
      <span className="orbit-ring orbit-ring-middle"><i /></span>
      <span className="orbit-ring orbit-ring-inner"><i /></span>
      <b>P</b>
    </div>
  )
}

export default function PredictPage() {
  const [url, setUrl] = useState('')
  const [category, setCategory] = useState(PREDICTION_CATEGORIES[0].value)
  const [result, setResult] = useState(null)
  const [videoTitle, setVideoTitle] = useState('')
  const [videoThumbnail, setVideoThumbnail] = useState('')
  const [fallbackThumbnail, setFallbackThumbnail] = useState('')
  const [thumbnailFailed, setThumbnailFailed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    if (!url.trim()) return
    setLoading(true)
    setError('')
    setVideoTitle('')
    setVideoThumbnail('')
    setFallbackThumbnail('')
    setThumbnailFailed(false)
    try {
      const videoUrl = url.trim()
      const videoId = videoIdFromUrl(videoUrl)
      const [prediction, databaseMetadata] = await Promise.all([
        predictFromUrl(videoUrl, category),
        videoId ? getVideoMetadata(videoId).catch(() => null) : Promise.resolve(null),
      ])
      const databaseTitle = databaseMetadata?.found ? databaseMetadata.title : ''
      const databaseThumbnail = databaseMetadata?.found ? databaseMetadata.thumbnail_url : ''
      const needsYouTubeTitle = !databaseTitle && !titleFromResult(prediction)
      const metadata = needsYouTubeTitle ? await fetchYouTubeMetadata(videoUrl) : null
      const directThumbnail = directThumbnailUrl(videoId)
      setVideoTitle(databaseTitle || titleFromResult(prediction) || metadata?.title || '')
      setVideoThumbnail(databaseThumbnail || thumbnailFromResult(prediction) || directThumbnail)
      setFallbackThumbnail(directThumbnail)
      setResult(prediction)
    }
    catch (err) { setError(err.message || '예측에 실패했습니다.') }
    finally { setLoading(false) }
  }

  const rawScore = valueOf(result, 'predicted_score', 'viral_score', 'score', 'prediction_score')
  const score = rawScore === null ? null : Number(rawScore)
  const validScore = Number.isFinite(score) ? score : null
  const categoryLabel = PREDICTION_CATEGORIES.find((item) => item.value === category)?.label || '기타'
  const resultTitle = titleFromResult(result) || videoTitle || 'YouTube 영상'
  const resultThumbnail = thumbnailFromResult(result) || videoThumbnail

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main dashboard-page predict-dashboard">
        <DashboardHeader title="바이럴 스코어" />

        <section className="predict-studio">
          <div className={`predict-workbench ${result ? 'has-result' : ''} ${loading ? 'is-loading' : ''}`}>
            {!result && !loading && (
              <div className="predict-entry-layout">
                <form className="predict-form-new" onSubmit={handleSubmit}>
                  <div className="predict-form-heading">
                    <img src={predictVideoIcon} alt="" />
                    <h2>분석할 영상을 입력하세요</h2>
                  </div>
                  <div className="predict-category-field">
                    <label htmlFor="prediction-category">영상 카테고리</label>
                    <select id="prediction-category" value={category} onChange={(event) => setCategory(event.target.value)}>
                      {PREDICTION_CATEGORIES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                    </select>
                  </div>
                  <label htmlFor="predict-url">YouTube 영상 URL</label>
                  <div className="predict-input-new">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10 13a5 5 0 0 0 7.1.1l2-2a5 5 0 0 0-7.1-7.1l-1.1 1.1"/><path d="M14 11a5 5 0 0 0-7.1-.1l-2 2A5 5 0 0 0 12 20l1.1-1.1"/></svg>
                    <input id="predict-url" type="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://www.youtube.com/watch?v=..." required />
                    <button type="submit">예측하기<span>→</span></button>
                  </div>
                  {error && <p className="predict-error">{error}</p>}
                  <p className="input-note">공개 상태인 YouTube 영상 주소를 입력해 주세요.</p>
                </form>
              </div>
            )}

            {loading && <div className="predict-empty-visual predict-loading-visual"><OrbitVisual loading /><p>영상 신호를 분석하고 있습니다.</p></div>}

            {result && !loading && (
              <div className="prediction-result-new">
                <span className="prediction-complete-status">분석 완료</span>
                <div className="prediction-result-summary">
                  {resultThumbnail && !thumbnailFailed ? (
                    <img
                      src={resultThumbnail}
                      alt=""
                      className="prediction-result-thumbnail"
                      onError={(event) => {
                        if (fallbackThumbnail && event.currentTarget.src !== fallbackThumbnail) {
                          event.currentTarget.src = fallbackThumbnail
                          return
                        }
                        setThumbnailFailed(true)
                      }}
                    />
                  ) : <div className="prediction-result-thumbnail thumbnail-fallback">영상 썸네일</div>}
                  <div className="prediction-result-heading">
                    <h2>{resultTitle}</h2>
                    <p className="prediction-category-chip">{categoryLabel}</p>
                  </div>
                </div>
                <PredictionSemicircleGauge score={validScore} />
                <button type="button" className="analyze-again" onClick={() => { setResult(null); setVideoTitle(''); setVideoThumbnail(''); setFallbackThumbnail(''); setThumbnailFailed(false); setUrl(''); setError('') }}>다른 영상 분석하기</button>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  )
}
