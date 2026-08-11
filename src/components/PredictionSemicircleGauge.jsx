const LEVELS = [
  { label: '매우 낮음', max: 19, tone: 'very-low' },
  { label: '낮음', max: 39, tone: 'low' },
  { label: '보통', max: 59, tone: 'medium' },
  { label: '높음', max: 79, tone: 'high' },
  { label: '매우 높음', max: 100, tone: 'very-high' },
]

function predictionLevel(score) {
  if (typeof score !== 'number' || !Number.isFinite(score)) return null
  return LEVELS.find((level) => score <= level.max) || LEVELS[LEVELS.length - 1]
}

export default function PredictionSemicircleGauge({ score }) {
  const value = typeof score === 'number' && Number.isFinite(score) ? Math.min(100, Math.max(0, score)) : 0
  const level = predictionLevel(score)
  const activeLevelIndex = level ? LEVELS.indexOf(level) : -1

  return (
    <div className={`prediction-gauge ${level?.tone || 'unavailable'}`}>
      <svg viewBox="0 0 220 132" role="img" aria-label={level ? `바이럴 점수 ${value.toFixed(1)}점, ${level.label}` : '바이럴 점수 없음'}>
        {LEVELS.map((item, index) => (
          <path
            key={item.label}
            className={`prediction-gauge-segment ${item.tone} ${index <= activeLevelIndex ? 'is-reached' : ''} ${index === activeLevelIndex ? 'is-current' : ''}`}
            d="M 25 112 A 85 85 0 0 1 195 112"
            pathLength="100"
            strokeDasharray="18.4 81.6"
            strokeDashoffset={index * -20.4}
          />
        ))}
      </svg>
      <div className="prediction-gauge-value">
        <strong>{level ? value.toFixed(1) : '-'}</strong>
        <span>/ 100</span>
      </div>
      <div className="prediction-levels" aria-label="바이럴 점수 단계">
        {LEVELS.map((item) => <span key={item.label} className={level?.label === item.label ? 'active' : ''}>{item.label}</span>)}
      </div>
    </div>
  )
}
