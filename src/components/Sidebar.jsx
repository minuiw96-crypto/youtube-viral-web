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
    children: [
      { to: '/my-channel', label: '채널 벤치마크' },
      { to: '/my-channel/performance', label: '영상 성과 분석' },
    ],
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
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.6v-.2h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z" />
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
        <span className="sidebar-section-label sidebar-link-label">WORKSPACE</span>
        {NAV_ITEMS.map((item) => {
          const active = item.children
            ? location.pathname.startsWith(item.to)
            : location.pathname === item.to
          return (
            <div className={`sidebar-nav-group ${active ? 'active' : ''}`} key={item.to}>
              <Link to={item.to} className={`sidebar-link ${active ? 'active' : ''}`} aria-expanded={item.children ? active : undefined}>
                {item.icon}
                <span className="sidebar-link-label">{item.label}</span>
                {item.children && (
                  <svg className="sidebar-link-label sidebar-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="m6 9 6 6 6-6" />
                  </svg>
                )}
              </Link>
              {item.children && active && !collapsed && (
                <div className="sidebar-subnav">
                  {item.children.map((child) => (
                    <Link key={child.to} to={child.to} className={location.pathname === child.to ? 'active' : ''}>
                      {child.label}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          )
        })}
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
