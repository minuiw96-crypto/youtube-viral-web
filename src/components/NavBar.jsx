import { Link, useNavigate } from 'react-router-dom'
import Logo from './Logo'
import ThemeToggle from './ThemeToggle'
import { getAccessToken, clearAccessToken } from '../api/client'

export default function NavBar() {
  const navigate = useNavigate()
  const isLoggedIn = Boolean(getAccessToken())

  function handleLogout() {
    clearAccessToken()
    navigate('/')
  }

  return (
    <header className="site-nav">
      <div className="container">
        <Logo />
        <ul className="nav-links">
          <li><a href="#features">기능 소개</a></li>
          <li><a href="#pricing">요금제</a></li>
        </ul>
        <div className="nav-actions">
          <ThemeToggle />
          {isLoggedIn ? (
            <>
              <button type="button" className="btn btn-ghost btn-sm nav-mobile-hide" onClick={handleLogout}>
                로그아웃
              </button>
              <Link to="/home" className="btn btn-primary btn-sm">대시보드로 가기</Link>
            </>
          ) : (
            <>
              <Link to="/login" className="btn btn-ghost btn-sm nav-mobile-hide">로그인</Link>
              <Link to="/register" className="btn btn-primary btn-sm">무료로 시작하기</Link>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
