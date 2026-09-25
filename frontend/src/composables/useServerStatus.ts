import axios from 'axios'
import { ref } from 'vue'

export type ServerState = 'checking' | 'waking' | 'ready' | 'offline'

const state = ref<ServerState>('checking')
let started = false

/**
 * The API runs on a free tier that sleeps when idle. Ping the liveness endpoint as
 * soon as the app loads, so the server is (usually) awake by the time the visitor
 * clicks "sign in", and tell them honestly what's happening if it isn't.
 */
export function useServerStatus() {
  if (!started) {
    started = true
    const slow = setTimeout(() => {
      if (state.value === 'checking') state.value = 'waking'
    }, 1500)
    const ping = async (attempt = 0): Promise<void> => {
      try {
        await axios.get('/api/v1/health/', { timeout: 70_000 })
        state.value = 'ready'
        clearTimeout(slow)
      } catch {
        if (attempt < 3) return ping(attempt + 1)
        state.value = 'offline'
      }
    }
    void ping()
  }
  return state
}
