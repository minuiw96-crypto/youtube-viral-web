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
    <header className="app-nav">
      <div className="container app-nav-inner">
        <Logo linkTo="/home" className="app-nav-logo" />
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
