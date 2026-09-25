<script setup lang="ts">
/** Full-page brand loader for transitions like sign-in and business setup. */
defineProps<{ message: string | null }>()
</script>

<template>
  <Transition name="fade">
    <div v-if="message" class="cp-fullscreen" role="status" aria-live="polite">
      <div class="cp-fullscreen__logo">
        <img src="/favicon.svg" width="56" height="56" alt="" />
      </div>
      <div class="text-h6 font-weight-bold mt-6">{{ message }}</div>
      <v-progress-linear indeterminate color="primary" rounded height="4" class="mt-4" style="width: 180px" />
    </div>
  </Transition>
</template>

<style scoped>
.cp-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 2900;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgb(var(--v-theme-background));
}
.cp-fullscreen__logo {
  animation: pulse 1.2s ease-in-out infinite;
  filter: drop-shadow(0 12px 24px rgba(29, 78, 216, 0.35));
}
@keyframes pulse {
  50% {
    transform: scale(0.92);
  }
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
