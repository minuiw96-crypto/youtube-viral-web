import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { askQuestion, getAccessToken } from '../api/client'

export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [contextVideoId, setContextVideoId] = useState(undefined)
  const messagesRef = useRef(null)
  const isLoggedIn = Boolean(getAccessToken())

  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight
    }
  }, [messages, open])

  async function handleSend(e) {
    e.preventDefault()
    const question = input.trim()
    if (!question || loading) return

    setMessages((m) => [...m, { role: 'user', text: question }])
    setInput('')
    setLoading(true)
    try {
      const data = await askQuestion({ question, contextVideoId })
      setContextVideoId(data.selected_video_id)
      setMessages((m) => [...m, { role: 'assistant', text: data.answer }])
    } catch (err) {
      setMessages((m) => [...m, { role: 'assistant', text: err.message || '답변을 가져오지 못했습니다.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {open && (
        <div className="chat-panel">
          <div className="chat-panel-header">
            <span>PredicTube AI</span>
            <button type="button" onClick={() => setOpen(false)} aria-label="채팅 닫기">✕</button>
          </div>

          {isLoggedIn ? (
            <>
              <div className="chat-messages" ref={messagesRef}>
                {messages.length === 0 && (
                  <p className="chat-empty">채널이나 영상에 대해 무엇이든 물어보세요.</p>
                )}
                {messages.map((m, i) => (
                  <div key={i} className={`chat-bubble ${m.role}`}>{m.text}</div>
                ))}
                {loading && <div className="chat-bubble assistant">답변을 생각하고 있어요…</div>}
              </div>
              <form className="chat-input-row" onSubmit={handleSend}>
                <input
                  type="text"
                  placeholder="질문을 입력하세요"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={loading}
                />
                <button type="submit" className="chat-send" disabled={loading || !input.trim()} aria-label="전송">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M3 11.5 21 3l-6 18-4-7-8-2.5Z" />
                  </svg>
                </button>
              </form>
            </>
          ) : (
            <div className="chat-messages">
              <p className="chat-empty">
                AI 챗봇은 로그인 후 이용할 수 있습니다.<br />
                <Link to="/login" onClick={() => setOpen(false)}>로그인하러 가기</Link>
              </p>
            </div>
          )}
        </div>
      )}

      <button
        type="button"
        className="chat-fab"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? '채팅 닫기' : '채팅 열기'}
      >
        {open ? (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M6 6l12 12M18 6 6 18" />
          </svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
            <path d="M4 4h16a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H9l-5 4v-4H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z" />
          </svg>
        )}
      </button>
    </>
  )
}
