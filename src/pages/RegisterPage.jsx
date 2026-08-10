import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Logo from '../components/Logo'
import ThemeToggle from '../components/ThemeToggle'
import { registerUser, loginUser, saveAccessToken } from '../api/client'

const initialForm = {
  name: '',
  channel_name: '',
  email: '',
  password: '',
  password_confirm: '',
}

export default function RegisterPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (form.password !== form.password_confirm) {
      setError('비밀번호가 일치하지 않습니다.')
      return
    }
    setLoading(true)
    try {
      await registerUser(form)
      const { access_token } = await loginUser({ email: form.email, password: form.password })
      saveAccessToken(access_token)
      navigate('/')
    } catch (err) {
      setError(err.message || '회원가입에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-top-bar">
        <ThemeToggle />
      </div>
      <Logo className="auth-logo" linkTo="/" />
      <p className="auth-slogan">영상이 뜨기 전에, 먼저 확인하세요</p>

      <form className="auth-card" onSubmit={handleSubmit}>
        {error && <div className="form-error">{error}</div>}
        <div className="field">
          <label htmlFor="name">이름</label>
          <input id="name" required value={form.name} onChange={update('name')} />
        </div>
        <div className="field">
          <label htmlFor="channel_name">채널명</label>
          <input id="channel_name" required value={form.channel_name} onChange={update('channel_name')} />
        </div>
        <div className="field">
          <label htmlFor="email">이메일</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={form.email}
            onChange={update('email')}
          />
        </div>
        <div className="field">
          <label htmlFor="password">비밀번호</label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            value={form.password}
            onChange={update('password')}
          />
        </div>
        <div className="field">
          <label htmlFor="password_confirm">비밀번호 확인</label>
          <input
            id="password_confirm"
            type="password"
            autoComplete="new-password"
            required
            value={form.password_confirm}
            onChange={update('password_confirm')}
          />
        </div>
        <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
          {loading ? '가입 중...' : '회원가입'}
        </button>
        <p className="auth-switch">
          이미 계정이 있으신가요? <Link to="/login">로그인</Link>
        </p>
      </form>
    </div>
  )
}
