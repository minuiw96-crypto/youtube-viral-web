import AuthedNavBar from '../components/AuthedNavBar'

const ROWS = [
  { label: '이메일 변경' },
  { label: '비밀번호 변경' },
  { label: '채널 정보 확인' },
]

export default function SettingsPage() {
  return (
    <div className="dashboard-shell">
      <AuthedNavBar />
      <div className="container">
        <div className="settings-list">
          {ROWS.map((row) => (
            <div className="settings-row" key={row.label}>
              <span>{row.label}</span>
              <button type="button" className="btn btn-outline btn-sm" disabled>
                곧 지원 예정
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
