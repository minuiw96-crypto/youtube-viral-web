import { useState } from 'react'
import Sidebar from '../components/Sidebar'
import DashboardHeader from '../components/DashboardHeader'
import ScoreGauge from '../components/ScoreGauge'
import { predictFromUrl } from '../api/client'

const PREDICTION_CATEGORIES = [
  { value: 'KR_MUKBANG', label: '먹방' },
  { value: 'KR_GAMING', label: '게임' },
]

function valueOf(result, ...keys) {
  for (const key of keys) if (result?.[key] !== undefined && result?.[key] !== null) return result[key]
  return null
}

export default function PredictPage() {
  const [url, setUrl] = useState('')
  const [category, setCategory] = useState(PREDICTION_CATEGORIES[0].value)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    if (!url.trim()) return
    setLoading(true)
    setError('')
    try {
      setResult(await predictFromUrl(url.trim(), category))
    }
    catch (err) { setError(err.message || '예측에 실패했습니다.') }
    finally { setLoading(false) }
  }

  const rawScore = valueOf(result, 'predicted_score', 'viral_score', 'score', 'prediction_score')
  const score = rawScore === null ? null : Number(rawScore)
  const validScore = Number.isFinite(score) ? score : null

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main dashboard-page predict-dashboard">
        <DashboardHeader title="바이럴 가능성 예측" description="YouTube 영상 URL 하나로 확산 가능성과 핵심 신호를 분석합니다." />

        <section className="predict-studio">
          <div className="predict-workbench">
            <form className="predict-form-new" onSubmit={handleSubmit}>
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
                <button type="submit" disabled={loading}>{loading ? '분석 중' : '예측하기'}<span>→</span></button>
              </div>
              {error && <p className="predict-error">{error}</p>}
              <p className="input-note">공개 상태인 YouTube 영상 주소를 입력해 주세요.</p>
            </form>

            {!result && !loading && (
              <div className="predict-empty-visual"><div className="signal-orbit"><span /><span /><span /><b>P</b></div><p>URL을 입력하면 분석 결과가 여기에 표시됩니다.</p></div>
            )}
            {loading && <div className="predict-empty-visual"><span className="loading-spinner large" /><p>영상 신호를 분석하고 있습니다.</p></div>}
            {result && !loading && (
              <div className="prediction-result-new">
                <div className="result-media">
                  {valueOf(result, 'thumbnail_url', 'thumbnail') ? <img src={valueOf(result, 'thumbnail_url', 'thumbnail')} alt="" /> : <span className="result-media-fallback">RESULT</span>}
                  <div><span>분석 완료</span><h3>{valueOf(result, 'title', 'video_title') || 'YouTube 영상'}</h3></div>
                </div>
                <div className="result-score-area"><ScoreGauge score={validScore} /><div><span>바이럴 스코어</span><strong>{validScore === null ? '-' : validScore.toFixed(1)}<small>/100</small></strong><p>{valueOf(result, 'grade', 'label', 'prediction_label') || '예측 모델 분석 결과'}</p></div></div>
                <button type="button" className="analyze-again" onClick={() => { setResult(null); setUrl(''); setError('') }}>다른 영상 분석하기</button>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  )
}
