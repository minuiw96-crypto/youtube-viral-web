const LEVELS = [
  { label: '매우 낮음', max: 19 },
  { label: '낮음', max: 39 },
  { label: '보통', max: 59 },
  { label: '높음', max: 79 },
  { label: '매우 높음', max: 100 },
]

const TICK_VALUES = [20, 40, 60, 80]

function arcPoint(value, radius) {
  const angle = Math.PI + (Math.PI * value) / 100
  return {
    x: 110 + Math.cos(angle) * radius,
    y: 112 + Math.sin(angle) * radius,
  }
}

function predictionLevel(score) {
  if (typeof score !== 'number' || !Number.isFinite(score)) return null
  return LEVELS.find((level) => score <= level.max) || LEVELS[LEVELS.length - 1]
}

export default function PredictionSemicircleGauge({ score }) {
  const value = typeof score === 'number' && Number.isFinite(score) ? Math.min(100, Math.max(0, score)) : 0
  const level = predictionLevel(score)

  return (
    <div className="prediction-gauge">
      <svg viewBox="0 0 220 132" role="img" aria-label={level ? `바이럴 점수 ${value.toFixed(1)}점, ${level.label}` : '바이럴 점수 없음'}>
        <path className="prediction-gauge-track" d="M 25 112 A 85 85 0 0 1 195 112" pathLength="100" />
        <path className="prediction-gauge-fill" d="M 25 112 A 85 85 0 0 1 195 112" pathLength="100" strokeDasharray={`${value} 100`} />
        {TICK_VALUES.map((tick) => {
          const inner = arcPoint(tick, 76)
          const outer = arcPoint(tick, 94)
          return <line key={tick} className="prediction-gauge-tick" x1={inner.x} y1={inner.y} x2={outer.x} y2={outer.y} />
        })}
        <g className="prediction-gauge-marker">
          <polygon points="0,7 -5,-3 5,-3" />
          <animateMotion
            begin="1.35s"
            dur="1.15s"
            path="M 16 112 A 94 94 0 0 1 204 112"
            keyPoints={`0;${value / 100}`}
            keyTimes="0;1"
            calcMode="spline"
            keySplines=".2 .8 .2 1"
            rotate="auto"
            fill="freeze"
          />
        </g>
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
