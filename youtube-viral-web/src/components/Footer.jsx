import logo from '../assets/logo.png'

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="container">
        <img src={logo} alt="PredicTube" className="footer-logo" />
        <span className="footer-meta">© {new Date().getFullYear()} PredicTube. All rights reserved.</span>
      </div>
    </footer>
  )
}
