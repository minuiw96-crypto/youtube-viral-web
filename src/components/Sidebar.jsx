import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import Logo from './Logo'
import ThemeToggle from './ThemeToggle'
import { clearAccessToken, getCurrentUser } from '../api/client'

const COLLAPSE_KEY = 'predictube_sidebar_collapsed'

const NAV_ITEMS = [
  {
    to: '/home',
    label: '홈',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M3 10.5 12 3l9 7.5" />
        <path d="M5 9.5V21h5v-6h4v6h5V9.5" />
      </svg>
    ),
  },
  {
    to: '/my-channel',
    label: '내 채널',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="8" r="4" />
        <path d="M4 20c1.5-4 5-6 8-6s6.5 2 8 6" />
      </svg>
    ),
  },
  {
    to: '/predict',
    label: '바이럴 예측',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M3 17 9 11l4 4 8-8" />
        <path d="M15 7h6v6" />
      </svg>
    ),
  },
  {
    to: '/settings',
    label: '설정',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M4 6h16M4 12h16M4 18h16" />
        <circle cx="8" cy="6" r="2" fill="var(--surface)" />
        <circle cx="16" cy="12" r="2" fill="var(--surface)" />
        <circle cx="10" cy="18" r="2" fill="var(--surface)" />
      </svg>
    ),
  },
]

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE_KEY) === '1')
  const [user, setUser] = useState(null)
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    let active = true
    getCurrentUser().then((data) => {
      if (active) setUser(data.user || data)
    }).catch(() => {})
    return () => { active = false }
  }, [])

  function toggleCollapsed() {
    setCollapsed((v) => {
      const next = !v
      localStorage.setItem(COLLAPSE_KEY, next ? '1' : '0')
      return next
    })
  }

  function handleLogout() {
    clearAccessToken()
    navigate('/login')
  }

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-top">
        <Logo className="sidebar-logo" linkTo="/home" />
        <button
          type="button"
          className="sidebar-collapse-btn"
          onClick={toggleCollapsed}
          aria-label={collapsed ? '사이드바 펼치기' : '사이드바 접기'}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            {collapsed ? <path d="m9 6 6 6-6 6" /> : <path d="m15 6-6 6 6 6" />}
          </svg>
        </button>
      </div>

      <div className="sidebar-workspace">
        <span className="workspace-mark">P</span>
        <div className="sidebar-link-label">
          <strong>PredicTube</strong>
          <small>Creator analytics</small>
        </div>
      </div>

      <nav className="sidebar-nav">
        <span className="sidebar-section-label sidebar-link-label">WORKSPACE</span>
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className={`sidebar-link ${location.pathname === item.to ? 'active' : ''}`}
          >
            {item.icon}
            <span className="sidebar-link-label">{item.label}</span>
          </Link>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="sidebar-profile">
          <span className="sidebar-avatar">{(user?.name || user?.email || 'P').slice(0, 1).toUpperCase()}</span>
          <div className="sidebar-profile-copy sidebar-link-label">
            <strong>{user?.name || '내 계정'}</strong>
            <small>{user?.email || 'PredicTube member'}</small>
          </div>
        </div>
        <div className="sidebar-utility-row">
          <ThemeToggle />
          <button type="button" className="sidebar-logout" onClick={handleLogout}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <path d="M16 17l5-5-5-5" />
              <path d="M21 12H9" />
            </svg>
            <span className="sidebar-link-label">로그아웃</span>
          </button>
        </div>
      </div>
    </aside>
  )
}
