import axios from 'axios'
import { clearSession, getToken } from '../stores/auth'
import { filenameFromDisposition } from '../utils/helpers'

const API_PREFIX = '/api/v1'

export class ApiError extends Error {
  constructor(message, { code, status, traceId } = {}) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.traceId = traceId
  }
}

function handleUnauthorized() {
  clearSession()
  if (!window.location.pathname.includes('/login')) {
    window.location.assign('/login')
  }
}

const http = axios.create({
  baseURL: API_PREFIX,
  timeout: 30000,
})

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  config.headers.Accept = 'application/json'
  return config
})

function toApiError(error) {
  if (error.response?.status === 401) handleUnauthorized()
  const payload = error.response?.data
  if (payload instanceof Blob) {
    return new ApiError(error.message || '文件下载失败', { status: error.response?.status })
  }
  return new ApiError(payload?.message || error.message || '数据服务请求失败', {
    code: payload?.code,
    status: error.response?.status,
    traceId: payload?.trace_id,
  })
}

export async function request(path, options = {}) {
  const { method = 'GET', body, query, headers = {}, signal } = options
  try {
    const response = await http.request({
      url: path,
      method,
      data: body,
      params: query,
      headers,
      signal,
    })
    const payload = response.data
    if (payload && payload.code !== 0) {
      throw new ApiError(payload.message || '业务请求未成功', {
        code: payload.code,
        status: response.status,
        traceId: payload.trace_id,
      })
    }
    return payload?.data
  } catch (error) {
    if (axios.isCancel(error) || error.name === 'AbortError') throw error
    if (error instanceof ApiError) throw error
    throw toApiError(error)
  }
}

export async function downloadFile(path, query = {}, fallback = '医疗运营数据.xlsx', options = {}) {
  const { method = 'GET', body } = options
  try {
    const response = await http.request({
      url: path,
      method,
      data: body,
      params: query,
      responseType: 'blob',
    })
    const filename = filenameFromDisposition(response.headers['content-disposition'], fallback)
    return { blob: response.data, filename }
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw toApiError(error)
  }
}
