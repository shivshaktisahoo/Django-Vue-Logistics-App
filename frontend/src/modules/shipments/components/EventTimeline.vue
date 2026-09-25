<script setup lang="ts">
import { mdiCircleMedium, mdiEyeOffOutline, mdiMapMarkerOutline, mdiPlus } from '@mdi/js'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, reactive, ref } from 'vue'
import { errorMessage, fieldErrors, http } from '@/api/http'
import type { TrackingEvent } from '@/api/types'
import EmptyState from '@/components/ui/EmptyState.vue'
import { useLookups } from '@/composables/useLookups'
import { EVENT_ICON, MANUAL_EVENT_CODES, STATUS } from '@/constants/logistics'
import { useNotify } from '@/stores/notify'
import { useOrgStore } from '@/stores/org'
import { formatDateTime, timeAgo } from '@/utils/format'

const props = defineProps<{ shipmentId: string; canAdd: boolean }>()
const orgStore = useOrgStore()
const notify = useNotify()
const queryClient = useQueryClient()
const { locations } = useLookups()

const key = computed(() => ['shipment', orgStore.currentId, props.shipmentId, 'events'])
const { data: events, isLoading } = useQuery({
  queryKey: key,
  queryFn: async () => (await http.get<TrackingEvent[]>(`/shipments/${props.shipmentId}/events/`)).data,
})

const CODE_STATUS: Record<string, keyof typeof STATUS> = {
  BKD: 'booked',
  PUP: 'picked_up',
  DEP: 'in_transit',
  CUS: 'at_customs',
  OFD: 'out_for_delivery',
  DLV: 'delivered',
  HLD: 'on_hold',
  CAN: 'cancelled',
}
function color(e: TrackingEvent) {
  if (e.code === 'DLY') return 'warning'
  const s = CODE_STATUS[e.code]
  return s ? STATUS[s].color : 'grey'
}
function icon(e: TrackingEvent) {
  const s = CODE_STATUS[e.code]
  return EVENT_ICON[e.code] ?? (s ? STATUS[s].icon : mdiCircleMedium)
}

// ---- add milestone
const open = ref(false)
const nowLocal = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60_000).toISOString().slice(0, 16)
const form = reactive({ code: 'ARR', occurred_at: nowLocal(), location_id: null as string | null, description: '', is_public: true })
const errors = ref<Record<string, string>>({})
const saving = ref(false)

function start() {
  Object.assign(form, { code: 'ARR', occurred_at: nowLocal(), location_id: null, description: '', is_public: true })
  errors.value = {}
  open.value = true
}

async function save() {
  saving.value = true
  errors.value = {}
  try {
    await http.post(`/shipments/${props.shipmentId}/events/`, { ...form, occurred_at: new Date(form.occurred_at).toISOString() })
    queryClient.invalidateQueries({ queryKey: key.value })
    queryClient.invalidateQueries({ queryKey: ['shipment', orgStore.currentId, props.shipmentId, 'audit'] })
    notify.success('Milestone added')
    open.value = false
  } catch (e) {
    errors.value = fieldErrors(e)
    if (!Object.keys(errors.value).length) notify.error(errorMessage(e))
  } finally {
    saving.value = false
  }
}

defineExpose({ refresh: () => queryClient.invalidateQueries({ queryKey: key.value }) })
</script>

<template>
  <div>
    <div class="d-flex align-center mb-4">
      <div class="cp-section-title">Milestones</div>
      <v-spacer />
      <v-btn v-if="canAdd" size="small" variant="tonal" color="primary" :prepend-icon="mdiPlus" @click="start">Add milestone</v-btn>
    </div>

    <v-skeleton-loader v-if="isLoading" type="list-item-avatar-two-line@4" class="bg-transparent" />
    <EmptyState v-else-if="!events?.length" :icon="mdiMapMarkerOutline" title="No milestones yet" text="They appear once the booking is confirmed." />
    <v-timeline v-else side="end" align="start" density="compact" truncate-line="both">
      <v-timeline-item v-for="e in events" :key="e.id" :dot-color="color(e)" size="small" :icon="icon(e)" fill-dot>
        <div class="d-flex flex-wrap align-center ga-2">
          <span class="font-weight-bold">{{ e.code_label }}</span>
          <v-chip size="x-small" variant="outlined" class="mono">{{ e.code }}</v-chip>
          <v-chip v-if="!e.is_public" size="x-small" color="grey" :prepend-icon="mdiEyeOffOutline">Internal</v-chip>
        </div>
        <div v-if="e.description && e.description !== e.code_label" class="text-body-2 mt-1">{{ e.description }}</div>
        <div class="text-caption text-medium-emphasis mt-1">
          {{ formatDateTime(e.occurred_at) }} ({{ timeAgo(e.occurred_at) }})
          <template v-if="e.location"> · {{ e.location.code }} {{ e.location.name }}</template>
          · {{ e.created_by_name }}
        </div>
      </v-timeline-item>
    </v-timeline>

    <v-dialog v-model="open" max-width="520">
      <v-card class="cp-card pa-2">
        <v-card-title class="font-weight-bold">Add milestone</v-card-title>
        <v-card-text>
          <v-row dense>
            <v-col cols="12"><v-select v-model="form.code" :items="MANUAL_EVENT_CODES" label="Event" :error-messages="errors.code" /></v-col>
            <v-col cols="12" sm="6"><v-text-field v-model="form.occurred_at" type="datetime-local" label="When" :max="nowLocal()" :error-messages="errors.occurred_at" /></v-col>
            <v-col cols="12" sm="6">
              <v-autocomplete v-model="form.location_id" :items="locations.data.value ?? []" :item-title="(l) => `${l.code} · ${l.name}`" item-value="id" label="Location" clearable />
            </v-col>
            <v-col cols="12"><v-textarea v-model="form.description" label="Details" rows="2" auto-grow /></v-col>
            <v-col cols="12">
              <v-switch v-model="form.is_public" color="primary" label="Visible to the customer" hide-details inset />
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="open = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" :loading="saving" @click="save">Add</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
