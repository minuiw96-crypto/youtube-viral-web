import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import Logo from './Logo'
import ThemeToggle from './ThemeToggle'
import { clearAccessToken } from '../api/client'

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
    to: '/video-detail',
    label: '영상 상세',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="9" />
        <path d="M10 8.5 15.5 12 10 15.5V8.5Z" fill="currentColor" stroke="none" />
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
  const location = useLocation()
  const navigate = useNavigate()

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
        <Logo className="sidebar-logo" linkTo="/" />
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

      <nav className="sidebar-nav">
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
    </aside>
  )
}
