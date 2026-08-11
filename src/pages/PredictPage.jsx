import { useState } from 'react'
import Sidebar from '../components/Sidebar'
import ScoreGauge from '../components/ScoreGauge'
import { predictFromUrl } from '../api/client'

export default function PredictPage() {
  const [step, setStep] = useState('input')
  const [url, setUrl] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    if (!url.trim()) return
    setStep('loading')
    setError('')
    try {
      const data = await predictFromUrl(url.trim())
      setResult(data)
      setStep('result')
    } catch (err) {
      setError(err.message || '예측에 실패했습니다.')
      setStep('input')
    }
  }

  function reset() {
    setUrl('')
    setResult(null)
    setError('')
    setStep('input')
  }

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <div className="dashboard-main">
      <div className="predict-page">
        <div className="predict-card-wrap">
          <h1 className="predict-title">영상 URL로 바이럴 스코어 확인하기</h1>

          {step === 'input' && (
            <form className="predict-card" onSubmit={handleSubmit}>
              {error && <div className="form-error">{error}</div>}
              <label className="predict-label" htmlFor="predict-url">
                예측할 YouTube 영상 주소를 입력하세요
              </label>
              <div className="predict-input-row">
                <div className="predict-url-input">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8 5v14l11-7Z" />
                  </svg>
                  <input
                    id="predict-url"
                    type="url"
                    placeholder="https://youtube.com/watch?v=..."
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    required
                  />
                </div>
                <button type="submit" className="predict-submit-btn">
                  예측 실행
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M5 12h14M13 6l6 6-6 6" />
                  </svg>
                </button>
              </div>
            </form>
          )}

          {step === 'loading' && <p className="dashboard-status">예측 중입니다...</p>}

          {step === 'result' && result && (
            <div className="predict-result-card">
              {result.thumbnail_url && (
                <img src={result.thumbnail_url} alt="" className="video-detail-thumb" />
              )}
              <h2>{result.title || '예측 결과'}</h2>
              <ScoreGauge score={result.viral_score} />
              <button type="button" className="btn btn-outline" onClick={reset}>
                처음으로
              </button>
            </div>
          )}
        </div>
      </div>
      </div>
    </div>
  )
}
