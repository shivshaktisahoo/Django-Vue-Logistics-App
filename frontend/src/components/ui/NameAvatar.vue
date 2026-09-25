<script setup lang="ts">
import { computed } from 'vue'
import { initials } from '@/utils/format'

const props = withDefaults(defineProps<{ name: string; size?: number | string }>(), { size: 36 })

const COLORS = ['indigo', 'teal', 'deep-purple', 'pink', 'orange', 'cyan', 'green', 'blue', 'amber-darken-2', 'red']

// Stable colour per name, so the same party always looks the same.
const color = computed(() => {
  let h = 0
  for (const ch of props.name) h = (h * 31 + ch.charCodeAt(0)) >>> 0
  return COLORS[h % COLORS.length]
})
</script>

<template>
  <v-avatar :color="color" variant="tonal" :size="size" rounded="lg">
    <span class="font-weight-bold" style="font-size: 0.8rem">{{ initials(name) }}</span>
  </v-avatar>
</template>
