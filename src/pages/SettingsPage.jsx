import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import DashboardHeader from '../components/DashboardHeader'
import ThemeToggle from '../components/ThemeToggle'
import { clearAccessToken, getCurrentUser } from '../api/client'

export default function SettingsPage() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    let active = true
    getCurrentUser().then((data) => active && setUser(data.user || data)).catch(() => {}).finally(() => active && setLoading(false))
    return () => { active = false }
  }, [])

  function logout() {
    clearAccessToken()
    navigate('/login')
  }

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main dashboard-page settings-dashboard">
        <DashboardHeader title="설정" description="계정 정보와 화면 환경을 관리합니다." />
        <div className="settings-layout-new">
          <nav className="settings-nav" aria-label="설정 메뉴"><a href="#account" className="active">계정</a><a href="#appearance">화면 설정</a><a href="#session">로그인 세션</a></nav>
          <div className="settings-content">
            <section className="settings-section" id="account">
              <div className="settings-section-heading"><div><h2>계정 정보</h2><p>가입된 계정과 연결 채널을 확인합니다.</p></div></div>
              <div className="account-summary">
                <span className="settings-avatar">{(user?.name || user?.email || 'P').slice(0, 1).toUpperCase()}</span>
                <div><strong>{loading ? '계정 확인 중' : user?.name || 'PredicTube 회원'}</strong><span>{user?.email || '-'}</span></div>
                <span className="account-status"><i />활성</span>
              </div>
              <dl className="settings-data-list">
                <div><dt>이메일</dt><dd>{user?.email || '-'}</dd></div>
                <div><dt>연결 채널</dt><dd>{user?.channel_name || user?.channel_title || '연결 정보 없음'}</dd></div>
                <div><dt>권한</dt><dd>{user?.role === 'admin' ? '관리자' : '일반 사용자'}</dd></div>
              </dl>
            </section>

            <section className="settings-section" id="appearance">
              <div className="settings-section-heading"><div><h2>화면 설정</h2><p>분석 화면에 사용할 색상 모드를 선택합니다.</p></div></div>
              <div className="settings-action-row"><div><strong>라이트 / 다크 모드</strong><span>현재 모드에서 반대 모드로 전환합니다.</span></div><ThemeToggle /></div>
            </section>

            <section className="settings-section danger-section" id="session">
              <div className="settings-section-heading"><div><h2>로그인 세션</h2><p>이 브라우저에 저장된 로그인 정보를 삭제합니다.</p></div></div>
              <div className="settings-action-row"><div><strong>현재 기기에서 로그아웃</strong><span>다시 이용하려면 이메일과 비밀번호로 로그인해야 합니다.</span></div><button type="button" className="danger-button" onClick={logout}>로그아웃</button></div>
            </section>
          </div>
        </div>
      </main>
    </div>
  )
}
