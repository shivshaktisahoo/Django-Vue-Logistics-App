import { onScopeDispose, ref, watch, type Ref } from 'vue'

/** Returns a ref that follows `source` once it has been stable for `delay` ms. */
export function useDebounced<T>(source: Ref<T>, delay = 250): Ref<T> {
  const debounced = ref(source.value) as Ref<T>
  let timer: ReturnType<typeof setTimeout> | undefined
  watch(source, (value) => {
    clearTimeout(timer)
    timer = setTimeout(() => (debounced.value = value), delay)
  })
  onScopeDispose(() => clearTimeout(timer))
  return debounced
}
