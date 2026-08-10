import { Link } from 'react-router-dom'
import Logo from './Logo'
import ThemeToggle from './ThemeToggle'

export default function NavBar() {
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
          <Link to="/login" className="btn btn-ghost btn-sm nav-mobile-hide">로그인</Link>
          <Link to="/register" className="btn btn-primary btn-sm">무료로 시작하기</Link>
        </div>
      </div>
    </header>
  )
}
