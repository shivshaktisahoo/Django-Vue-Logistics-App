<script setup lang="ts">
/**
 * Covers its (position: relative) parent while a request is in flight: the form behind
 * is hidden and cannot be edited or re-submitted.
 */
withDefaults(defineProps<{ active: boolean; message?: string; hint?: string }>(), {
  message: 'Please wait…',
  hint: '',
})
</script>

<template>
  <v-overlay
    :model-value="active"
    contained
    persistent
    no-click-animation
    class="cp-overlay align-center justify-center"
    :scrim="true"
    role="status"
    aria-live="polite"
  >
    <div class="d-flex flex-column align-center text-center pa-6" style="max-width: 320px">
      <div class="cp-overlay-spinner mb-4">
        <v-progress-circular indeterminate color="primary" size="52" width="4" />
        <img src="/favicon.svg" width="22" height="22" alt="" />
      </div>
      <div class="text-subtitle-1 font-weight-bold">{{ message }}</div>
      <div v-if="hint" class="text-body-2 text-medium-emphasis mt-1">{{ hint }}</div>
    </div>
  </v-overlay>
</template>

<style scoped>
.cp-overlay-spinner {
  position: relative;
  display: grid;
  place-items: center;
}
.cp-overlay-spinner img {
  position: absolute;
}
</style>
