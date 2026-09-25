import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { http, refreshSession, setAccessToken } from '@/api/http'
import type { AuthResponse, Role, User } from '@/api/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const ready = ref(false) // true once the startup session check has finished

  const isAuthenticated = computed(() => user.value !== null)

  function applySession(res: AuthResponse) {
    setAccessToken(res.access)
    user.value = res.user
  }

  function clearSession() {
    setAccessToken(null)
    user.value = null
  }

  /** On startup, silently restore the session from the httpOnly refresh cookie. */
  async function bootstrap() {
    if (ready.value) return
    try {
      applySession(await refreshSession())
    } catch {
      clearSession()
    } finally {
      ready.value = true
    }
  }

  async function login(email: string, password: string) {
    const { data } = await http.post<AuthResponse>('/auth/login/', { email, password })
    applySession(data)
    return data
  }

  async function demoLogin(role: Role) {
    const { data } = await http.post<AuthResponse>('/auth/demo/', { role })
    applySession(data)
    return data
  }

  async function register(payload: { email: string; full_name: string; password: string }) {
    const { data } = await http.post<AuthResponse>('/auth/register/', payload)
    applySession(data)
    return data
  }

  async function logout() {
    try {
      await http.post('/auth/logout/')
    } finally {
      clearSession()
    }
  }

  return { user, ready, isAuthenticated, applySession, clearSession, bootstrap, login, demoLogin, register, logout }
})
