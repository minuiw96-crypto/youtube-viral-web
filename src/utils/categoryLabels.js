const CATEGORY_LABELS = {
  MUKBANG: '먹방',
  GAMING: '게임',
  BEAUTY: '뷰티',
  COOKING: '요리',
  TRAVEL: '여행',
  MUSIC: '음악',
  SPORTS: '스포츠',
  EDUCATION: '교육',
  ENTERTAINMENT: '엔터테인먼트',
}

export function formatCategory(raw) {
  if (!raw) return '-'
  const key = raw.toUpperCase().replace(/^[A-Z]{2}_/, '')
  if (CATEGORY_LABELS[key]) return CATEGORY_LABELS[key]
  return key
    .split('_')
    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
    .join(' ')
}
