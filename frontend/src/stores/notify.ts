import { defineStore } from 'pinia'
import { ref } from 'vue'

interface Toast {
  text: string
  color: 'success' | 'error' | 'info' | 'warning'
  action?: { label: string; handler: () => void }
}

/** App-wide snackbar. Supports an optional action (e.g. Undo). */
export const useNotify = defineStore('notify', () => {
  const toast = ref<Toast | null>(null)
  const visible = ref(false)

  function show(text: string, color: Toast['color'] = 'success', action?: Toast['action']) {
    toast.value = { text, color, action }
    visible.value = true
  }

  return {
    toast,
    visible,
    show,
    success: (text: string, action?: Toast['action']) => show(text, 'success', action),
    error: (text: string) => show(text, 'error'),
  }
})
