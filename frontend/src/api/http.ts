import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'
import type { TokenResponse } from '@/types'

interface EasterEggNotice {
  first_discovery: boolean
  message: string
}

function decodeEasterEggNotices(encoded: string): EasterEggNotice[] {
  const base64 = encoded.replace(/-/g, '+').replace(/_/g, '/')
  const padded = base64.padEnd(base64.length + ((4 - base64.length % 4) % 4), '=')
  const binary = window.atob(padded)
  const bytes = Uint8Array.from(binary, character => character.charCodeAt(0))
  const decoded: unknown = JSON.parse(new TextDecoder().decode(bytes))
  if (!Array.isArray(decoded)) return []
  return decoded.filter((notice): notice is EasterEggNotice => (
    typeof notice === 'object'
    && notice !== null
    && typeof notice.first_discovery === 'boolean'
    && typeof notice.message === 'string'
    && notice.message.length > 0
  ))
}

function showEasterEggNotices(response: AxiosResponse) {
  const encoded = response.headers['x-easter-egg']
  if (typeof encoded !== 'string' || !encoded) return
  try {
    for (const notice of decodeEasterEggNotices(encoded)) {
      window.dispatchEvent(new CustomEvent('toast', {
        detail: {
          message: notice.message,
          type: notice.first_discovery ? 'success' : 'info',
          duration: notice.first_discovery ? 12000 : 6000,
        },
      }))
    }
  } catch (error) {
    console.warn('Failed to decode easter egg notice', error)
  }
}

class HttpClient {
  private instance: AxiosInstance
  private refreshPromise: Promise<RefreshOutcome> | null = null

  constructor(baseURL: string = '/api') {
    this.instance = axios.create({
      baseURL,
      timeout: 15000,
    })

    // 请求拦截器
    this.instance.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // 响应拦截器
    this.instance.interceptors.response.use(
      // Keep the Axios response envelope. The FastAPI endpoints return raw
      // JSON payloads, and callers consistently consume them through `.data`.
      (response) => {
        showEasterEggNotices(response)
        return response
      },
      (error) => {
        const request = error.config as (AxiosRequestConfig & { _retry?: boolean }) | undefined
        const refreshToken = localStorage.getItem('refresh_token')
        if (error.response?.status === 401 && refreshToken && request && !request._retry && !String(request.url || '').includes('/auth/refresh')) {
          request._retry = true
          if (!this.refreshPromise) {
            this.refreshPromise = axios.post<TokenResponse>('/api/auth/refresh', { refresh_token: refreshToken })
              .then((response): RefreshOutcome => {
                if (localStorage.getItem('refresh_token') !== refreshToken) {
                  return { status: 'stale' }
                }
                localStorage.setItem('access_token', response.data.access_token)
                localStorage.setItem('refresh_token', response.data.refresh_token)
                return { status: 'refreshed', accessToken: response.data.access_token }
              })
              .catch((): RefreshOutcome => (
                localStorage.getItem('refresh_token') === refreshToken
                  ? { status: 'failed', refreshToken }
                  : { status: 'stale' }
              ))
              .finally(() => { this.refreshPromise = null })
          }
          return this.refreshPromise.then((outcome) => {
            if (outcome.status === 'refreshed') {
              request.headers = request.headers || {}
              request.headers.Authorization = `Bearer ${outcome.accessToken}`
              return this.instance.request(request)
            }
            if (outcome.status === 'failed' && localStorage.getItem('refresh_token') === outcome.refreshToken) {
              localStorage.removeItem('access_token')
              localStorage.removeItem('refresh_token')
              localStorage.removeItem('user_uid')
              localStorage.removeItem('user_role')
              if (window.location.pathname !== '/login') window.location.href = '/login'
            }
            return Promise.reject(error)
          })
        }
        if (error.response?.status === 401) {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('user_uid')
          localStorage.removeItem('user_role')
          if (window.location.pathname !== '/login') window.location.href = '/login'
        }
        // Let each request owner render a local retry/error state. A failed
        // background request (for example the footer version) must not replace
        // the user's current page with a global 500 route.
        return Promise.reject(error)
      }
    )
  }

  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.instance.get(url, config)
  }

  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.instance.post(url, data, config)
  }

  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.instance.put(url, data, config)
  }

  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.instance.delete(url, config)
  }
}

type RefreshOutcome =
  | { status: 'refreshed'; accessToken: string }
  | { status: 'stale' }
  | { status: 'failed'; refreshToken: string }

export const http = new HttpClient()
export default http
