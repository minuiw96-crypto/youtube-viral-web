function numeric(value) {
  if (value === null || value === undefined || value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

export function formatSubscriberCount(value) {
  const parsed = numeric(value)
  if (parsed === null) return '-'
  if (parsed >= 10000) return `${Math.round(parsed / 10000)}만`
  if (parsed >= 1000) {
    const thousands = Math.floor(parsed / 100) / 10
    return `${Number.isInteger(thousands) ? thousands : thousands.toFixed(1).replace(/\.0$/, '')}천`
  }
  return Math.round(parsed).toLocaleString('ko-KR')
}
