import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type { AuthResponse } from './types'

/**
 * Session state lives here (not in Pinia) so the HTTP layer has no store
 * dependency; the auth store registers callbacks via `configureSession`.
 */
let accessToken: string | null = null
let orgId: string | null = null
let onSessionExpired: () => void = () => {}
let onRefreshed: (res: AuthResponse) => void = () => {}

export function setAccessToken(token: string | null) {
  accessToken = token
}
export function setOrgId(id: string | null) {
  orgId = id
}
export function configureSession(opts: { onExpired: () => void; onRefreshed: (res: AuthResponse) => void }) {
  onSessionExpired = opts.onExpired
  onRefreshed = opts.onRefreshed
}

// Generous timeout: a free-tier backend can take ~30 s to wake from sleep.
export const http = axios.create({ baseURL: '/api/v1', withCredentials: true, timeout: 60_000 })

http.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  if (orgId) config.headers['X-Org-Id'] = orgId
  return config
})

// Single-flight refresh: concurrent 401s share one refresh request.
let refreshing: Promise<AuthResponse> | null = null

export function refreshSession(): Promise<AuthResponse> {
  refreshing ??= axios
    .post<AuthResponse>('/api/v1/auth/refresh/', null, { withCredentials: true, timeout: 60_000 })
    .then((res) => {
      if (res.status === 204) throw new Error('No session') // first visit: nothing to restore
      setAccessToken(res.data.access)
      onRefreshed(res.data)
      return res.data
    })
    .finally(() => {
      refreshing = null
    })
  return refreshing
}

type RetryConfig = InternalAxiosRequestConfig & { _retried?: boolean }

http.interceptors.response.use(undefined, async (error: AxiosError) => {
  const config = error.config as RetryConfig | undefined
  const isAuthCall = config?.url?.startsWith('/auth/')
  if (error.response?.status === 401 && config && !config._retried && !isAuthCall) {
    config._retried = true
    try {
      await refreshSession()
      return http(config)
    } catch {
      onSessionExpired()
    }
  }
  return Promise.reject(error)
})

/** DRF field errors → { field: 'first message' } for form display. */
export function fieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof AxiosError) || error.response?.status !== 400) return {}
  const data = error.response.data as Record<string, unknown>
  const out: Record<string, string> = {}
  for (const [key, value] of Object.entries(data ?? {})) {
    if (key === 'detail' || key === 'non_field_errors') continue
    out[key] = Array.isArray(value) ? String(value[0]) : String(value)
  }
  return out
}

/** Best human-readable message for a failed request. */
export function errorMessage(error: unknown, fallback = 'Something went wrong. Please try again.') {
  if (error instanceof AxiosError) {
    if (!error.response) return 'Network error — check your connection.'
    const data = error.response.data as Record<string, unknown> | undefined
    const detail = data?.detail ?? (data?.non_field_errors as string[] | undefined)?.[0]
    if (typeof detail === 'string') return detail
    const first = Object.values(fieldErrors(error))[0]
    if (first) return first
  }
  return fallback
}
