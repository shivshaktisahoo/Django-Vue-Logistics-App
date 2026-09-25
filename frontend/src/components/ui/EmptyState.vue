<script setup lang="ts">
defineProps<{ icon: string; title: string; text?: string }>()
</script>

<template>
  <div class="d-flex flex-column align-center text-center py-12 px-4">
    <div class="cp-empty-icon mb-4">
      <v-icon :icon="icon" size="36" color="primary" />
    </div>
    <div class="text-subtitle-1 font-weight-bold">{{ title }}</div>
    <div v-if="text" class="text-body-2 text-medium-emphasis mt-1 mb-5" style="max-width: 380px">{{ text }}</div>
    <slot />
  </div>
</template>

<style scoped>
.cp-empty-icon {
  width: 80px;
  height: 80px;
  border-radius: 24px;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at 30% 20%, rgba(var(--v-theme-primary), 0.22), transparent 60%),
    rgba(var(--v-theme-primary), 0.08);
}
</style>
