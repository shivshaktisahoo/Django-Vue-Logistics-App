<script setup lang="ts">
defineProps<{ title: string; subtitle?: string; icon?: string }>()
</script>

<template>
  <div class="d-flex flex-wrap align-center ga-4 mb-6">
    <v-avatar v-if="icon" color="primary" variant="tonal" rounded="lg" size="48" class="d-none d-sm-flex">
      <v-icon :icon="icon" size="26" />
    </v-avatar>
    <div class="flex-grow-1" style="min-width: 0">
      <h1 class="text-h5 font-weight-bold">{{ title }}</h1>
      <div v-if="subtitle || $slots.subtitle" class="text-body-2 text-medium-emphasis mt-1">
        <slot name="subtitle">{{ subtitle }}</slot>
      </div>
    </div>
    <div class="d-flex flex-wrap align-center ga-2">
      <slot name="actions" />
    </div>
  </div>
</template>
