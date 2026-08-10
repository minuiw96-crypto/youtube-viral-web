import { useState } from 'react'
import AuthedNavBar from '../components/AuthedNavBar'
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
      <AuthedNavBar />
      <div className="predict-page">
        {step === 'input' && (
          <form className="predict-card" onSubmit={handleSubmit}>
            {error && <div className="form-error">{error}</div>}
            <input
              type="url"
              placeholder="유튜브 영상 URL"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
            />
            <button type="submit" className="btn btn-primary btn-block">
              예측하기
            </button>
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
  )
}
