const TOKEN_KEY = 'predictube_access_token'

const ERROR_MESSAGES = {
  EMAIL_EXISTS: '이미 가입된 이메일입니다.',
  WEAK_PASSWORD: '비밀번호는 8자 이상, 영문 소문자와 숫자를 포함해야 합니다.',
  INVALID_EMAIL: '올바른 이메일 형식이 아닙니다.',
  INVALID_CREDENTIALS: '이메일 또는 비밀번호가 올바르지 않습니다.',
  ACCOUNT_DISABLED: '비활성화된 계정입니다.',
  ADMIN_REQUIRED: '관리자 권한이 필요합니다.',
}

export class ApiError extends Error {
  constructor(message, status, code) {
    super(message)
    this.status = status
    this.code = code
  }
}

export function getAccessToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function saveAccessToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearAccessToken() {
  localStorage.removeItem(TOKEN_KEY)
}

async function apiRequest(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  if (options.body) headers['Content-Type'] = 'application/json'
  const token = getAccessToken()
  if (token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(path, { ...options, headers })
  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new ApiError(ERROR_MESSAGES[data.code] || data.error || '요청 처리 중 오류가 발생했습니다.', response.status, data.code)
  }
  return data
}

export function loginUser({ email, password }) {
  return apiRequest('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function registerUser({ email, password, password_confirm, name, channel_name }) {
  return apiRequest('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, password_confirm, name, channel_name }),
  })
}

export function getCurrentUser() {
  return apiRequest('/api/auth/me')
}

export function getChannelSummary(channelId) {
  const query = channelId ? `?channel_id=${encodeURIComponent(channelId)}` : ''
  return apiRequest(`/api/channel/summary${query}`)
}

export function getChannelVideos(channelId) {
  const query = channelId ? `?channel_id=${encodeURIComponent(channelId)}` : ''
  return apiRequest(`/api/channel/videos${query}`)
}

export function getVideoRanking() {
  return apiRequest('/api/dashboard/admin-overview')
}

export function predictFromUrl(url) {
  return apiRequest('/api/predict', {
    method: 'POST',
    body: JSON.stringify({ url }),
  })
}

export function askQuestion({ question, channelId, videoId, contextVideoId }) {
  return apiRequest('/api/chat', {
    method: 'POST',
    body: JSON.stringify({
      question,
      channel_id: channelId,
      video_id: videoId,
      context_video_id: contextVideoId,
    }),
  })
}
