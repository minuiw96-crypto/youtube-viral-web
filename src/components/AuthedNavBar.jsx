import { Link, useNavigate } from 'react-router-dom'
import Logo from './Logo'
import ThemeToggle from './ThemeToggle'
import { clearAccessToken } from '../api/client'

export default function AuthedNavBar() {
  const navigate = useNavigate()

  function handleLogout() {
    clearAccessToken()
    navigate('/login')
  }

  return (
    <header className="site-nav">
      <div className="container">
        <Logo linkTo="/" />
        <ul className="nav-links">
          <li><Link to="/home">홈</Link></li>
          <li><Link to="/video-detail">영상 상세</Link></li>
          <li><Link to="/predict">예측</Link></li>
          <li><Link to="/settings">설정</Link></li>
        </ul>
        <div className="nav-actions">
          <ThemeToggle />
          <button type="button" className="btn btn-outline btn-sm" onClick={handleLogout}>
            로그아웃
          </button>
        </div>
      </div>
    </header>
  )
}
