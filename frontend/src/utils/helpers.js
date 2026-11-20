export function buildQuery(params = {}) {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, String(value))
    }
  })
  const text = query.toString()
  return text ? `?${text}` : ''
}

export function asArray(value) {
  return Array.isArray(value) ? value : []
}

export function fileExtension(filename = '') {
  const parts = String(filename).toLowerCase().split('.')
  return parts.length > 1 ? parts.pop() : ''
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export function filenameFromDisposition(disposition, fallback) {
  const encoded = disposition?.match(/filename\*=UTF-8''([^;]+)/i)?.[1]
  if (encoded) {
    try {
      return decodeURIComponent(encoded)
    } catch {
      return fallback
    }
  }
  const plain = disposition?.match(/filename="?([^";]+)"?/i)?.[1]
  return plain || fallback
}
