<script setup lang="ts">
import { computed } from 'vue'
import { useServerStatus } from '@/composables/useServerStatus'

const state = useServerStatus()

const view = computed(
  () =>
    ({
      checking: { color: 'grey', text: 'Connecting to the demo server…' },
      waking: {
        color: 'warning',
        text: 'Waking the demo server — free-tier hosting sleeps when idle. Usually under 30 seconds.',
      },
      ready: { color: 'success', text: 'Demo server is live' },
      offline: { color: 'error', text: 'The demo server is not responding. Please try again shortly.' },
    })[state.value],
)
</script>

<template>
  <div class="cp-server d-flex align-start ga-2 text-caption" role="status" aria-live="polite">
    <span class="cp-server__dot" :class="`bg-${view.color}`" :data-pulse="state === 'checking' || state === 'waking'" />
    <span class="text-medium-emphasis">{{ view.text }}</span>
  </div>
</template>

<style scoped>
.cp-server__dot {
  width: 8px;
  height: 8px;
  margin-top: 5px;
  flex-shrink: 0;
  border-radius: 50%;
}
.cp-server__dot[data-pulse='true'] {
  animation: blink 1s ease-in-out infinite;
}
@keyframes blink {
  50% {
    opacity: 0.3;
  }
}
</style>
