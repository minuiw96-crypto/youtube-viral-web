const RADIUS = 26
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

// 임시 등급 기준 — 실제 퀀타일 기준은 백엔드 데이터 확인 후 교체 필요
function getGrade(score) {
  if (score >= 90) return { label: '베리굿', className: 'grade-verygood' }
  if (score >= 70) return { label: '굿', className: 'grade-good' }
  if (score >= 40) return { label: '배드', className: 'grade-bad' }
  return { label: '베리배드', className: 'grade-verybad' }
}

export default function ScoreGauge({ score }) {
  const value = typeof score === 'number' ? score : 0
  const offset = CIRCUMFERENCE * (1 - Math.min(Math.max(value, 0), 100) / 100)
  const grade = getGrade(value)

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
      <span className={`grade-badge ${grade.className}`}>{grade.label}</span>
    </div>
  )
}
