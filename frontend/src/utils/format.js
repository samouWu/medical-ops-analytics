export function formatNumber(value, format = 'number') {
  if (value === null || value === undefined || value === '') return '—'
  const number = Number(value)
  if (!Number.isFinite(number)) return String(value)

  const options = { maximumFractionDigits: 2 }
  if (format === 'integer' || format === 'int') {
    options.maximumFractionDigits = 0
  } else if (format === 'decimal' || format === 'currency' || format === 'percent') {
    options.minimumFractionDigits = 2
    options.maximumFractionDigits = 2
  }
  return new Intl.NumberFormat('zh-CN', options).format(number)
}

export function formatMetric(value, unit = '', format = 'number') {
  const formatted = formatNumber(value, format)
  if (formatted === '—' || !unit) return formatted
  return `${formatted}${unit}`
}

export function compactNumber(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return '—'
  return new Intl.NumberFormat('zh-CN', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(number)
}

export function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
}

export function errorMessage(error) {
  return error?.message || '请求失败，请稍后重试'
}
