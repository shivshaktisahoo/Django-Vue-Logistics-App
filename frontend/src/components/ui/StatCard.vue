<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router'

withDefaults(
  defineProps<{
    label: string
    value?: string | number | null
    icon: string
    color?: string
    caption?: string
    loading?: boolean
    to?: RouteLocationRaw
  }>(),
  { color: 'primary', value: null, caption: '', loading: false, to: undefined },
)
</script>

<template>
  <v-card class="cp-card pa-4 pa-sm-5 h-100" :class="{ 'cp-card--hover': !!to }" :to="to" :ripple="!!to">
    <div class="d-flex align-start justify-space-between ga-3">
      <div style="min-width: 0">
        <div class="text-body-2 text-medium-emphasis font-weight-medium">{{ label }}</div>
        <v-skeleton-loader v-if="loading" type="heading" width="110" class="mt-2 bg-transparent" />
        <div v-else class="cp-stat-value font-weight-bold num mt-1">{{ value ?? '—' }}</div>
        <div v-if="caption" class="text-caption text-medium-emphasis mt-1">{{ caption }}</div>
      </div>
      <v-avatar :color="color" variant="tonal" rounded="lg" size="44" class="d-none d-sm-flex">
        <v-icon :icon="icon" size="24" />
      </v-avatar>
    </div>
  </v-card>
</template>

<style scoped>
.cp-stat-value {
  font-size: clamp(1.05rem, 4.2vw, 1.5rem);
  line-height: 1.3;
  letter-spacing: -0.02em;
  overflow-wrap: anywhere;
}
</style>
