import { defineStore } from 'pinia'
import { ref } from 'vue'

/** Global UI state: route-change progress and full-screen transitions. */
export const useUiStore = defineStore('ui', () => {
  const navigating = ref(false)
  const fullscreenMessage = ref<string | null>(null)
  return { navigating, fullscreenMessage }
})
