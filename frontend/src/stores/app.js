import { reactive } from 'vue'
import { request } from '../api/client'

export const appState = reactive({
  meta: { departments: [], date_range: { min: '', max: '' } },
  metaLoading: false,
  metaError: '',
})

export const filters = reactive({
  start: '',
  end: '',
  dept_code: '',
})

let metaPromise = null

export function loadMeta(force = false) {
  if (appState.meta.date_range.max && !force) return Promise.resolve()
  if (metaPromise) return metaPromise

  metaPromise = (async () => {
    appState.metaLoading = true
    appState.metaError = ''
    try {
      const data = await request('/meta')
      appState.meta = {
        departments: Array.isArray(data?.departments) ? data.departments : [],
        date_range: data?.date_range || { min: '', max: '' },
      }
      if (!filters.start) filters.start = appState.meta.date_range.min || ''
      if (!filters.end) filters.end = appState.meta.date_range.max || ''
    } catch (error) {
      appState.metaError = error.message
    } finally {
      appState.metaLoading = false
    }
  })().finally(() => { metaPromise = null })

  return metaPromise
}

export function filterParams() {
  return {
    start: filters.start,
    end: filters.end,
    dept_code: filters.dept_code,
  }
}
