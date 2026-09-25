<script setup lang="ts">
import type { ShipmentStatus } from '@/api/types'
import { STATUS } from '@/constants/logistics'

withDefaults(defineProps<{ status: ShipmentStatus; size?: string }>(), { size: 'small' })
</script>

<template>
  <v-chip :color="STATUS[status].color" :size="size" variant="tonal" :prepend-icon="STATUS[status].icon" class="font-weight-bold">
    {{ STATUS[status].label }}
  </v-chip>
</template>
