const RADIUS = 26
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

export default function ScoreGauge({ score }) {
  const value = typeof score === 'number' ? score : 0
  const offset = CIRCUMFERENCE * (1 - Math.min(Math.max(value, 0), 100) / 100)

  return (
    <div className="score-gauge">
      <svg width="64" height="64" viewBox="0 0 64 64">
        <circle cx="32" cy="32" r={RADIUS} className="score-gauge-track" />
        <circle
          cx="32"
          cy="32"
          r={RADIUS}
          className="score-gauge-fill"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          transform="rotate(-90 32 32)"
        />
        <text x="32" y="36" textAnchor="middle" className="score-gauge-text">
          {typeof score === 'number' ? score.toFixed(1) : '-'}
        </text>
      </svg>
    </div>
  )
}
