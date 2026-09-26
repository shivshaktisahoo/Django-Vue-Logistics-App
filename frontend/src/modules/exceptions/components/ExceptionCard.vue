<script setup lang="ts">
import { mdiAccountArrowLeftOutline, mdiCheckAll, mdiEyeCheckOutline, mdiRobotOutline } from '@mdi/js'
import { ref } from 'vue'
import { errorMessage, http } from '@/api/http'
import type { ShipmentExceptionItem } from '@/api/types'
import { MODE_BY_VALUE } from '@/constants/logistics'
import { SEVERITY } from '@/constants/exceptions'
import { useAuthStore } from '@/stores/auth'
import { useNotify } from '@/stores/notify'
import { formatDateTime, timeAgo } from '@/utils/format'

const props = withDefaults(defineProps<{ exc: ShipmentExceptionItem; canManage: boolean; showShipment?: boolean }>(), { showShipment: true })
const emit = defineEmits<{ changed: [exc: ShipmentExceptionItem] }>()
const auth = useAuthStore()
const notify = useNotify()

const busy = ref<string | null>(null)
const resolveOpen = ref(false)
const note = ref('')

async function run(action: 'acknowledge' | 'assign' | 'resolve', body?: object) {
  busy.value = action
  try {
    const { data } = await http.post<ShipmentExceptionItem>(`/exceptions/${props.exc.id}/${action}/`, body)
    emit('changed', data)
    notify.success(action === 'resolve' ? 'Exception resolved' : action === 'assign' ? 'Assigned to you' : 'Acknowledged')
    resolveOpen.value = false
  } catch (e) {
    notify.error(errorMessage(e))
  } finally {
    busy.value = null
  }
}
</script>

<template>
  <div class="cp-exc" :data-severity="exc.severity" :class="{ 'is-resolved': exc.status === 'resolved' }">
    <div class="d-flex flex-wrap align-start ga-3">
      <v-avatar :color="SEVERITY[exc.severity].color" variant="tonal" rounded="lg" size="40">
        <v-icon :icon="SEVERITY[exc.severity].icon" />
      </v-avatar>
      <div class="flex-grow-1" style="min-width: 0">
        <div class="d-flex flex-wrap align-center ga-2">
          <span class="font-weight-bold">{{ exc.title }}</span>
          <v-chip size="x-small" :color="SEVERITY[exc.severity].color" variant="flat">{{ SEVERITY[exc.severity].label }}</v-chip>
          <v-chip size="x-small" variant="outlined">{{ exc.kind_label }}</v-chip>
          <v-chip v-if="exc.status === 'acknowledged'" size="x-small" color="primary" variant="tonal">Acknowledged</v-chip>
        </div>
        <div class="text-body-2 text-medium-emphasis mt-1">{{ exc.detail }}</div>
        <div class="d-flex flex-wrap align-center ga-3 text-caption text-medium-emphasis mt-2">
          <router-link v-if="showShipment" :to="{ name: 'shipment-detail', params: { id: exc.shipment.id } }" class="cp-exc__ship">
            <v-icon :icon="MODE_BY_VALUE[exc.shipment.mode].icon" size="14" />
            <strong>{{ exc.shipment.reference }}</strong>
            <span class="mono">{{ exc.shipment.origin }}→{{ exc.shipment.destination }}</span>
            · {{ exc.shipment.customer }}
          </router-link>
          <span>Detected {{ timeAgo(exc.detected_at) }}</span>
          <span v-if="exc.assignee_name">· Owner: <strong>{{ exc.assignee_name }}</strong></span>
        </div>
        <div v-if="exc.status === 'resolved'" class="cp-exc__resolution mt-2">
          <v-icon :icon="exc.auto_resolved ? mdiRobotOutline : mdiCheckAll" size="15" />
          {{ exc.auto_resolved ? 'Auto-resolved' : `Resolved by ${exc.resolved_by_name}` }} {{ formatDateTime(exc.resolved_at) }}:
          {{ exc.resolution_note }}
        </div>
      </div>
      <div v-if="canManage && exc.status !== 'resolved'" class="d-flex flex-wrap ga-2">
        <v-btn v-if="exc.status === 'open'" size="small" variant="tonal" :prepend-icon="mdiEyeCheckOutline" :loading="busy === 'acknowledge'" @click="run('acknowledge')">
          Acknowledge
        </v-btn>
        <v-btn
          v-if="exc.assignee_id !== auth.user?.id"
          size="small"
          variant="text"
          :prepend-icon="mdiAccountArrowLeftOutline"
          :loading="busy === 'assign'"
          @click="run('assign', { assignee: auth.user?.id })"
        >
          Take it
        </v-btn>
        <v-btn size="small" color="success" variant="flat" :prepend-icon="mdiCheckAll" @click="resolveOpen = true">Resolve</v-btn>
      </div>
    </div>

    <v-dialog v-model="resolveOpen" max-width="480">
      <v-card class="cp-card pa-2">
        <v-card-title class="font-weight-bold">Resolve exception</v-card-title>
        <v-card-text>
          <div class="text-body-2 text-medium-emphasis mb-3">{{ exc.title }} · {{ exc.shipment.reference }}</div>
          <v-textarea v-model="note" label="What was done?" placeholder="e.g. Carrier confirmed rollover; customer informed of new ETA" rows="3" auto-grow autofocus />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="resolveOpen = false">Cancel</v-btn>
          <v-btn color="success" variant="flat" :disabled="!note.trim()" :loading="busy === 'resolve'" @click="run('resolve', { note })">Resolve</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
.cp-exc {
  position: relative;
  padding: 16px 16px 16px 20px;
  border-radius: 14px;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  overflow: hidden;
}
.cp-exc::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: rgb(var(--v-theme-info));
}
.cp-exc[data-severity='medium']::before {
  background: rgb(var(--v-theme-warning));
}
.cp-exc[data-severity='high']::before {
  background: #f4511e;
}
.cp-exc[data-severity='critical']::before {
  background: rgb(var(--v-theme-error));
}
.cp-exc.is-resolved {
  opacity: 0.75;
}
.cp-exc.is-resolved::before {
  background: rgb(var(--v-theme-success));
}
.cp-exc__ship {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: rgb(var(--v-theme-primary));
  text-decoration: none;
}
.cp-exc__ship:hover {
  text-decoration: underline;
}
.cp-exc__resolution {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  color: rgb(var(--v-theme-success));
}
</style>
