<script setup lang="ts">
import { mdiArrowRightThin } from '@mdi/js'
import type { LocationRef, Mode } from '@/api/types'
import { MODE_BY_VALUE } from '@/constants/logistics'

defineProps<{ origin: LocationRef; destination: LocationRef; mode?: Mode; dense?: boolean }>()
</script>

<template>
  <div class="d-flex align-center ga-2" style="min-width: 0">
    <v-icon v-if="mode" :icon="MODE_BY_VALUE[mode].icon" size="18" class="text-medium-emphasis flex-shrink-0" />
    <div style="min-width: 0">
      <div class="d-flex align-center ga-1 font-weight-bold mono">
        {{ origin.code }} <v-icon :icon="mdiArrowRightThin" size="18" class="text-medium-emphasis" /> {{ destination.code }}
      </div>
      <div v-if="!dense" class="text-caption text-medium-emphasis text-truncate">
        {{ origin.city || origin.name }} → {{ destination.city || destination.name }}
      </div>
    </div>
  </div>
</template>
