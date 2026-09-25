import { onBeforeUnmount, onMounted } from 'vue'

function isTyping(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null
  return !!el && (el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName))
}

/**
 * Register a keyboard shortcut for the component's lifetime.
 * `combo` examples: "ctrl+k", "n", "/", "f9". Plain keys are ignored while typing in a field;
 * function keys (F1–F12) always fire, which POS counters rely on.
 */
export function useHotkey(combo: string, handler: (e: KeyboardEvent) => void) {
  const parts = combo.toLowerCase().split('+')
  const key = parts.pop()!
  const needsMod = parts.includes('ctrl') || parts.includes('meta')

  function onKey(e: KeyboardEvent) {
    if (e.key.toLowerCase() !== key) return
    const mod = e.ctrlKey || e.metaKey
    if (needsMod !== mod) return
    const isFunctionKey = /^f\d{1,2}$/.test(key)
    if (!needsMod && !isFunctionKey && isTyping(e.target)) return
    e.preventDefault()
    handler(e)
  }

  onMounted(() => window.addEventListener('keydown', onKey))
  onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
}
