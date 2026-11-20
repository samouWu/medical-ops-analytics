const MONEY_UNIT = /元/

/** 金额超过 10 万元时折算为万元展示，避免卡片出现超长数字串 */
export const MONEY_WAN_THRESHOLD = 100000

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

export function isMoneyUnit(unit = '') {
  return MONEY_UNIT.test(String(unit ?? ''))
}

/** 金额拆分：返回 { value, unit }，大额金额自动换算成万元 */
export function splitMoney(value, unit = '元', threshold = MONEY_WAN_THRESHOLD) {
  const text = String(unit ?? '')
  const number = Number(value)
  if (!isMoneyUnit(text) || !Number.isFinite(number) || Math.abs(number) < threshold) {
    return { value, unit: text }
  }
  return { value: number / 10000, unit: text.replace('元', '万元') }
}

export function formatMoney(value, unit = '元', format = 'currency') {
  const display = splitMoney(value, unit)
  const text = formatNumber(display.value, format)
  if (text === '—' || !display.unit) return text
  return `${text}${display.unit}`
}

export function formatMetric(value, unit = '', format = 'number') {
  if (isMoneyUnit(unit)) return formatMoney(value, unit, format === 'number' ? 'currency' : format)
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
