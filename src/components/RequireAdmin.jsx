import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { getAccessToken, getCurrentUser } from '../api/client'

export default function RequireAdmin({ children }) {
  const [state, setState] = useState({ loading: true, allowed: false, unauthorized: false })

  useEffect(() => {
    let active = true
    getCurrentUser()
      .then((data) => {
        if (!active) return
        const user = data.user || data
        setState({ loading: false, allowed: user?.role === 'admin', unauthorized: false })
      })
      .catch((error) => {
        if (active) setState({ loading: false, allowed: false, unauthorized: error?.status === 401 })
      })
    return () => { active = false }
  }, [])

  if (!getAccessToken() || state.unauthorized) return <Navigate to="/login" replace />
  if (state.loading) return <div className="route-guard-state"><span className="loading-spinner" />관리자 권한을 확인하는 중입니다.</div>
  if (!state.allowed) return <Navigate to="/home" replace />
  return children
}
