import { Link } from 'react-router-dom'
import logo from '../assets/logo.png'

export default function Logo({ className = 'nav-logo', linkTo = '/' }) {
  const img = <img src={logo} alt="PredicTube" className={className} />
  if (!linkTo) return img
  return <Link to={linkTo}>{img}</Link>
}
