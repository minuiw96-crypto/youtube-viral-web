import { useNavigate } from 'react-router-dom'
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
