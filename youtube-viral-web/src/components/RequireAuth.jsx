import { Navigate } from 'react-router-dom'
import { getAccessToken } from '../api/client'

export default function RequireAuth({ children }) {
  if (!getAccessToken()) {
    return <Navigate to="/login" replace />
  }
  return children
}
