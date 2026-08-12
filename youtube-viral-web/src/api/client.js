const TOKEN_KEY = 'predictube_access_token'

const ERROR_MESSAGES = {
  EMAIL_EXISTS: '이미 가입된 이메일입니다.',
  WEAK_PASSWORD: '비밀번호는 8자 이상, 영문 소문자와 숫자를 포함해야 합니다.',
  INVALID_EMAIL: '올바른 이메일 형식이 아닙니다.',
  INVALID_CREDENTIALS: '이메일 또는 비밀번호가 올바르지 않습니다.',
  ACCOUNT_DISABLED: '비활성화된 계정입니다.',
  ADMIN_REQUIRED: '관리자 권한이 필요합니다.',
  CHANNEL_NOT_CONNECTED: '연결된 YouTube 채널을 확인해 주세요.',
  INVALID_CHANNEL_NAME: '올바른 YouTube 채널명을 입력해 주세요.',
  BACKEND_NOT_CONFIGURED: '서버 연결 설정을 확인해 주세요.',
}

function safeErrorMessage(data, status) {
  const mapped = ERROR_MESSAGES[data.code]
  if (mapped) return mapped
  const raw = typeof data.error === 'string' ? data.error : ''
  if (/project_category|video_url|channel_id|subscriber_count|content_domain|[a-z]+_[a-z]+/i.test(raw)) {
    if (/categor/i.test(raw)) return '영상 카테고리를 확인하지 못했습니다. 연결 채널 정보를 확인해 주세요.'
    if (/url/i.test(raw)) return '올바른 YouTube 영상 주소를 입력해 주세요.'
    return '입력 정보를 확인해 주세요.'
  }
  if (raw && /[가-힣]/.test(raw)) return raw
  if (status === 404) return '요청한 기능을 서버에서 찾지 못했습니다.'
  if (status >= 500) return '서버 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.'
  return '요청 정보를 확인하고 다시 시도해 주세요.'
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
    throw new ApiError(safeErrorMessage(data, response.status), response.status, data.code)
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

export function getVideoMetadata(videoId) {
  return apiRequest(`/api/video/metadata?video_id=${encodeURIComponent(videoId)}`)
}

export function getVideoRanking() {
  return getAdminOverview()
}

export function getAdminOverview() {
  return apiRequest('/api/dashboard/admin-overview')
}

export function predictFromUrl(url, projectCategory) {
  return apiRequest('/api/predict', {
    method: 'POST',
    body: JSON.stringify({ video_url: url, project_category: projectCategory }),
  })
}

export function updateConnectedChannel(channelName) {
  return apiRequest('/api/auth/channel', {
    method: 'PATCH',
    body: JSON.stringify({ channel_name: channelName }),
  })
}

export function deleteAccount() {
  return apiRequest('/api/auth/me', { method: 'DELETE' })
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
