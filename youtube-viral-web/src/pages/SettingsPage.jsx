import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import DashboardHeader from '../components/DashboardHeader'
import ThemeToggle from '../components/ThemeToggle'
import { clearAccessToken, deleteAccount, getCurrentUser, updateConnectedChannel } from '../api/client'

export default function SettingsPage() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [editingChannel, setEditingChannel] = useState(false)
  const [channelName, setChannelName] = useState('')
  const [savingChannel, setSavingChannel] = useState(false)
  const [channelMessage, setChannelMessage] = useState('')
  const [deleting, setDeleting] = useState(false)
  const [deleteMessage, setDeleteMessage] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    let active = true
    getCurrentUser().then((data) => {
      if (!active) return
      const current = data.user || data
      setUser(current)
      setChannelName(current.channel_title || current.channel_name || '')
    }).catch(() => {}).finally(() => active && setLoading(false))
    return () => { active = false }
  }, [])

  async function changeChannel(event) {
    event.preventDefault()
    if (!channelName.trim()) return
    setSavingChannel(true)
    setChannelMessage('')
    try {
      const data = await updateConnectedChannel(channelName.trim())
      const nextUser = data.user || data
      setUser(nextUser)
      setChannelName(nextUser.channel_title || channelName.trim())
      setEditingChannel(false)
      setChannelMessage('연결 채널을 변경했습니다.')
    } catch (error) {
      setChannelMessage(error.message || '연결 채널을 변경하지 못했습니다.')
    } finally {
      setSavingChannel(false)
    }
  }

  async function withdraw() {
    if (!window.confirm('회원 탈퇴 후에는 계정과 연결 정보를 복구할 수 없습니다. 탈퇴하시겠습니까?')) return
    setDeleting(true)
    setDeleteMessage('')
    try {
      await deleteAccount()
      clearAccessToken()
      navigate('/')
    } catch (error) {
      setDeleteMessage(error.message || '회원 탈퇴를 처리하지 못했습니다.')
      setDeleting(false)
    }
  }

  return (
    <div className="dashboard-shell">
      <Sidebar />
      <main className="dashboard-main dashboard-page settings-dashboard">
        <DashboardHeader title="설정" />
        <div className="settings-layout-new">
          <div className="settings-content">
            <section className="settings-section" id="account">
              <div className="settings-section-heading"><div><h2>계정 정보</h2></div></div>
              <div className="account-summary">
                <span className="settings-avatar">{(user?.name || user?.email || 'P').slice(0, 1).toUpperCase()}</span>
                <div><strong>{loading ? '계정 확인 중' : user?.name || 'PredicTube 회원'}</strong><span>{user?.email || '-'}</span></div>
                <span className="account-status"><i />활성</span>
              </div>
              <dl className="settings-data-list">
                <div><dt>이메일</dt><dd>{user?.email || '-'}</dd></div>
                <div className="channel-setting-row">
                  <dt>연결 채널</dt>
                  <dd>
                    <span>{user?.channel_title || user?.channel_name || '연결 정보 없음'}</span>
                    <button type="button" className="settings-inline-button" onClick={() => { setEditingChannel((value) => !value); setChannelMessage('') }}>변경</button>
                  </dd>
                </div>
              </dl>
              {editingChannel && (
                <form className="channel-change-form" onSubmit={changeChannel}>
                  <label htmlFor="settings-channel-name">새 YouTube 채널명</label>
                  <div><input id="settings-channel-name" value={channelName} onChange={(event) => setChannelName(event.target.value)} maxLength="200" required /><button type="submit" disabled={savingChannel}>{savingChannel ? '변경 중' : '연결하기'}</button></div>
                </form>
              )}
              {channelMessage && <p className="settings-feedback">{channelMessage}</p>}
            </section>

            <section className="settings-section" id="appearance">
              <div className="settings-section-heading"><div><h2>화면 설정</h2></div></div>
              <div className="settings-action-row"><div><strong>라이트 / 다크 모드</strong><span>현재 모드에서 반대 모드로 전환합니다.</span></div><ThemeToggle /></div>
            </section>

            <section className="settings-section danger-section" id="withdrawal">
              <div className="settings-section-heading"><div><h2>회원 탈퇴</h2></div></div>
              <div className="settings-action-row"><div><strong>PredicTube 계정 삭제</strong><span>탈퇴 후에는 계정 정보를 복구할 수 없습니다.</span></div><button type="button" className="danger-button" onClick={withdraw} disabled={deleting}>{deleting ? '처리 중' : '회원 탈퇴'}</button></div>
              {deleteMessage && <p className="settings-feedback danger-feedback">{deleteMessage}</p>}
            </section>
          </div>
        </div>
      </main>
    </div>
  )
}
