<script setup lang="ts">
import {
  mdiAccountHardHatOutline,
  mdiArrowLeft,
  mdiArrowRight,
  mdiCameraOutline,
  mdiCancel,
  mdiCheck,
  mdiFileDocumentOutline,
  mdiMapMarkerCheckOutline,
  mdiMapMarkerOutline,
  mdiPhoneOutline,
  mdiSnowflake,
  mdiTruckOutline,
} from '@mdi/js'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { errorMessage, fieldErrors, http } from '@/api/http'
import type { FleetOptions, ShipmentDocument, Trip, TripStop } from '@/api/types'
import { VEHICLE_TYPES } from '@/constants/logistics'
import { TRIP_STATUS } from '@/constants/procurement'
import { useNotify } from '@/stores/notify'
import { useOrgStore } from '@/stores/org'
import { openDocument } from '@/utils/download'
import { formatDateTime, formatMoney, formatNumber } from '@/utils/format'

const route = useRoute()
const orgStore = useOrgStore()
const notify = useNotify()
const queryClient = useQueryClient()
const id = computed(() => route.params.id as string)
const key = computed(() => ['trips', orgStore.currentId, 'detail', id.value])

const { data: trip, isLoading, isError } = useQuery({
  queryKey: key,
  queryFn: async () => (await http.get<Trip>(`/trips/${id.value}/`)).data,
})
const shipmentId = computed(() => trip.value?.stops[0]?.shipment.id)
const { data: pods } = useQuery({
  queryKey: computed(() => ['documents', orgStore.currentId, shipmentId.value, 'pod']),
  queryFn: async () => (await http.get<ShipmentDocument[]>('/documents/', { params: { shipment: shipmentId.value, doc_type: 'pod' } })).data,
  enabled: computed(() => !!shipmentId.value),
})

const canRun = computed(() => orgStore.can('trips.update'))
const canCancel = computed(() => orgStore.can('trips.manage') && ['planned', 'dispatched'].includes(trip.value?.status ?? ''))
const vehicleLabel = (v: string) => VEHICLE_TYPES.find((t) => t.value === v)?.title ?? v

function apply(updated: Trip, message: string) {
  queryClient.setQueryData(key.value, updated)
  queryClient.invalidateQueries({ queryKey: ['trips', orgStore.currentId] })
  queryClient.invalidateQueries({ queryKey: ['shipments', orgStore.currentId] })
  queryClient.invalidateQueries({ queryKey: ['documents', orgStore.currentId] })
  notify.success(message)
}

// ---------------- dispatch (vehicle + driver)
const assignOpen = ref(false)
const assign = reactive({ vehicle: null as string | null, driver: null as string | null })
const assignErrors = ref<Record<string, string>>({})
const { data: fleet } = useQuery({
  queryKey: computed(() => ['trips', orgStore.currentId, id.value, 'fleet']),
  queryFn: async () => (await http.get<FleetOptions>(`/trips/${id.value}/fleet/`)).data,
  enabled: assignOpen,
})
function startAssign() {
  assign.vehicle = trip.value?.vehicle?.id ?? null
  assign.driver = trip.value?.driver?.id ?? null
  assignErrors.value = {}
  assignOpen.value = true
}
const busy = ref<string | null>(null)
async function saveAssign() {
  busy.value = 'assign'
  assignErrors.value = {}
  try {
    const { data } = await http.post<Trip>(`/trips/${id.value}/assign/`, assign)
    apply(data, `Dispatched ${data.vehicle?.plate_number} with ${data.driver?.name}`)
    assignOpen.value = false
  } catch (e) {
    assignErrors.value = fieldErrors(e)
    if (!Object.keys(assignErrors.value).length) notify.error(errorMessage(e))
  } finally {
    busy.value = null
  }
}

// ---------------- stops
async function arrive(stop: TripStop) {
  busy.value = `arrive-${stop.id}`
  try {
    const { data } = await http.post<Trip>(`/trips/${id.value}/stops/${stop.id}/arrive/`)
    apply(data, `Arrived at ${stop.location.name}`)
  } catch (e) {
    notify.error(errorMessage(e))
  } finally {
    busy.value = null
  }
}

const completing = ref<TripStop | null>(null)
const pod = reactive({ receiver: '', file: null as File | null })
const podErrors = ref<Record<string, string>>({})
function startComplete(stop: TripStop) {
  completing.value = stop
  pod.receiver = ''
  pod.file = null
  podErrors.value = {}
}
async function confirmComplete() {
  const stop = completing.value
  if (!stop) return
  busy.value = `complete-${stop.id}`
  podErrors.value = {}
  try {
    const body = new FormData()
    body.append('receiver_name', pod.receiver)
    if (pod.file) body.append('pod', pod.file)
    const { data } = await http.post<Trip>(`/trips/${id.value}/stops/${stop.id}/complete/`, body)
    apply(data, stop.kind === 'pickup' ? 'Loaded and departed' : `Delivered, signed by ${pod.receiver}`)
    completing.value = null
  } catch (e) {
    podErrors.value = fieldErrors(e)
    if (!Object.keys(podErrors.value).length) notify.error(errorMessage(e))
  } finally {
    busy.value = null
  }
}

const cancelOpen = ref(false)
const cancelReason = ref('')
async function cancel() {
  try {
    const { data } = await http.post<Trip>(`/trips/${id.value}/cancel/`, { reason: cancelReason.value })
    apply(data, 'Trip cancelled')
    cancelOpen.value = false
  } catch (e) {
    notify.error(errorMessage(e))
  }
}

function stopState(s: TripStop) {
  if (s.completed_at) return 'done'
  if (String(s.id) === trip.value?.next_stop_id) return 'current'
  return 'todo'
}
</script>

<template>
  <div>
    <v-btn variant="text" :prepend-icon="mdiArrowLeft" class="mb-2 ml-n2" :to="{ name: 'trips' }">Trips</v-btn>
    <v-alert v-if="isError" type="error" variant="tonal" text="This trip doesn't exist or isn't yours." />
    <v-skeleton-loader v-else-if="isLoading || !trip" type="heading, card, card" class="bg-transparent" />

    <template v-else>
      <div class="d-flex flex-wrap align-center ga-3 mb-5">
        <v-avatar :color="TRIP_STATUS[trip.status].color" variant="tonal" rounded="lg" size="52"><v-icon :icon="TRIP_STATUS[trip.status].icon" size="28" /></v-avatar>
        <div class="flex-grow-1">
          <div class="d-flex flex-wrap align-center ga-2">
            <h1 class="text-h5 font-weight-bold">{{ trip.reference }}</h1>
            <v-chip :color="TRIP_STATUS[trip.status].color" variant="tonal" size="small">{{ TRIP_STATUS[trip.status].label }}</v-chip>
          </div>
          <div class="text-body-2 text-medium-emphasis">
            {{ trip.carrier.name }} · {{ formatMoney(trip.agreed_rate, trip.currency) }} agreed
            <template v-if="trip.tender"> · from <router-link :to="{ name: 'tender-detail', params: { id: trip.tender.id } }">{{ trip.tender.reference }}</router-link></template>
          </div>
        </div>
        <v-btn v-if="orgStore.can('shipments.view')" variant="tonal" :to="{ name: 'shipment-detail', params: { id: shipmentId } }" :append-icon="mdiArrowRight">
          {{ trip.stops[0]?.shipment.reference }}
        </v-btn>
        <v-btn v-if="canCancel" variant="text" color="error" :prepend-icon="mdiCancel" @click="cancelOpen = true">Cancel trip</v-btn>
      </div>

      <v-row>
        <v-col cols="12" md="4">
          <v-card class="cp-card pa-5 mb-4">
            <div class="d-flex align-center mb-3">
              <div class="cp-section-title">Truck & driver</div>
              <v-spacer />
              <v-btn v-if="canRun && ['planned', 'dispatched'].includes(trip.status)" size="small" :variant="trip.vehicle ? 'text' : 'flat'" color="primary" @click="startAssign">
                {{ trip.vehicle ? 'Change' : 'Dispatch' }}
              </v-btn>
            </div>
            <template v-if="trip.vehicle">
              <div class="d-flex align-center ga-3 mb-3">
                <v-avatar color="primary" variant="tonal" rounded="lg"><v-icon :icon="mdiTruckOutline" /></v-avatar>
                <div>
                  <div class="font-weight-bold mono">{{ trip.vehicle.plate_number }}</div>
                  <div class="text-caption text-medium-emphasis">{{ vehicleLabel(trip.vehicle.vehicle_type) }} · {{ formatNumber(trip.vehicle.capacity_kg, 'kg') }}</div>
                </div>
              </div>
              <div class="d-flex align-center ga-3">
                <v-avatar color="secondary" variant="tonal" rounded="lg"><v-icon :icon="mdiAccountHardHatOutline" /></v-avatar>
                <div>
                  <div class="font-weight-bold">{{ trip.driver?.name }}</div>
                  <div class="text-caption text-medium-emphasis">{{ trip.driver?.phone }}</div>
                </div>
              </div>
            </template>
            <v-alert v-else type="warning" variant="tonal" density="compact" text="No truck assigned yet. Dispatch before the pickup time." />
            <v-divider class="my-4" />
            <div class="cp-kv"><span>Load</span><strong>{{ formatNumber(trip.load_kg, 'kg') }}</strong></div>
            <div class="cp-kv"><span>Planned</span><strong>{{ formatDateTime(trip.planned_start) }}</strong></div>
            <div class="cp-kv"><span>Due</span><strong>{{ formatDateTime(trip.planned_end) }}</strong></div>
            <div v-if="trip.started_at" class="cp-kv"><span>Started</span><strong>{{ formatDateTime(trip.started_at) }}</strong></div>
            <div v-if="trip.completed_at" class="cp-kv"><span>Completed</span><strong>{{ formatDateTime(trip.completed_at) }}</strong></div>
          </v-card>

          <v-card v-if="pods?.length" class="cp-card pa-5">
            <div class="cp-section-title mb-3">Proof of delivery</div>
            <v-list density="compact" class="pa-0">
              <v-list-item v-for="d in pods" :key="d.id" :prepend-icon="mdiFileDocumentOutline" :title="d.file_name" :subtitle="d.notes" @click="openDocument(d.id, d.file_name)" />
            </v-list>
          </v-card>
        </v-col>

        <v-col cols="12" md="8">
          <v-card class="cp-card pa-5">
            <div class="cp-section-title mb-4">Stops</div>
            <div v-for="s in trip.stops" :key="s.id" class="cp-stop" :data-state="stopState(s)">
              <div class="cp-stop__dot">
                <v-icon :icon="s.completed_at ? mdiCheck : s.kind === 'pickup' ? mdiMapMarkerOutline : mdiMapMarkerCheckOutline" size="16" />
              </div>
              <div class="flex-grow-1" style="min-width: 0">
                <div class="d-flex flex-wrap align-center ga-2">
                  <span class="text-overline" style="line-height: 1.4">{{ s.sequence }} · {{ s.kind }}</span>
                  <v-chip v-if="s.shipment.is_temperature_controlled" size="x-small" color="info" variant="tonal" :prepend-icon="mdiSnowflake">Reefer</v-chip>
                </div>
                <div class="font-weight-bold">{{ s.location.name }}</div>
                <div class="text-body-2 text-medium-emphasis">{{ s.location.city }}, {{ s.location.country }} · {{ s.party.name }}</div>
                <div v-if="s.party.contact || s.party.phone" class="text-caption text-medium-emphasis d-flex align-center ga-1">
                  <v-icon :icon="mdiPhoneOutline" size="13" /> {{ s.party.contact }} {{ s.party.phone }}
                </div>
                <div class="text-caption mt-1">
                  Planned {{ formatDateTime(s.planned_at) }}
                  <template v-if="s.arrived_at"> · arrived {{ formatDateTime(s.arrived_at) }}</template>
                  <template v-if="s.completed_at"> · {{ s.kind === 'pickup' ? 'loaded' : 'delivered' }} {{ formatDateTime(s.completed_at) }}</template>
                  <template v-if="s.receiver_name"> · signed by <strong>{{ s.receiver_name }}</strong></template>
                </div>
                <div class="text-caption text-medium-emphasis">
                  {{ s.shipment.total_packages }} pkg · {{ formatNumber(s.shipment.gross_weight_kg, 'kg') }} · {{ s.shipment.commodity }}
                </div>
              </div>
              <div v-if="canRun && stopState(s) === 'current'" class="d-flex flex-column ga-2">
                <v-btn v-if="!s.arrived_at" size="small" variant="tonal" :loading="busy === `arrive-${s.id}`" @click="arrive(s)">Arrived</v-btn>
                <v-btn size="small" color="primary" variant="flat" :prepend-icon="s.kind === 'delivery' ? mdiCameraOutline : undefined" @click="startComplete(s)">
                  {{ s.kind === 'pickup' ? 'Loaded & depart' : 'Deliver + POD' }}
                </v-btn>
              </div>
            </div>
            <v-alert v-if="trip.status === 'planned' && canRun" type="info" variant="tonal" density="compact" class="mt-2" text="Dispatch a truck and driver to start running stops." />
          </v-card>
        </v-col>
      </v-row>

      <!-- Dispatch dialog -->
      <v-dialog v-model="assignOpen" max-width="520">
        <v-card class="cp-card pa-2">
          <v-card-title class="font-weight-bold">Dispatch truck & driver</v-card-title>
          <v-card-text>
            <div class="text-body-2 text-medium-emphasis mb-4">Load: {{ formatNumber(fleet?.load_kg ?? trip.load_kg, 'kg') }}</div>
            <v-select
              v-model="assign.vehicle"
              :items="fleet?.vehicles ?? []"
              item-value="id"
              :item-title="(v) => `${v.plate_number} · ${vehicleLabel(v.vehicle_type)}`"
              :item-props="(v) => ({ disabled: !v.fits || !!v.busy_on, subtitle: !v.fits ? `Only ${v.capacity_kg.toLocaleString()} kg` : v.busy_on ? `On ${v.busy_on}` : `${v.capacity_kg.toLocaleString()} kg payload` })"
              label="Vehicle"
              :error-messages="assignErrors.vehicle"
            />
            <v-select
              v-model="assign.driver"
              :items="fleet?.drivers ?? []"
              item-value="id"
              :item-title="(d) => `${d.name} · ${d.phone}`"
              label="Driver"
              :error-messages="assignErrors.driver"
            />
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="assignOpen = false">Cancel</v-btn>
            <v-btn color="primary" variant="flat" :loading="busy === 'assign'" :disabled="!assign.vehicle || !assign.driver" @click="saveAssign">Dispatch</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <!-- Complete stop dialog -->
      <v-dialog :model-value="!!completing" max-width="480" @update:model-value="(v: boolean) => !v && (completing = null)">
        <v-card v-if="completing" class="cp-card pa-2">
          <v-card-title class="font-weight-bold">{{ completing.kind === 'pickup' ? 'Confirm loading' : 'Confirm delivery' }}</v-card-title>
          <v-card-text>
            <template v-if="completing.kind === 'pickup'">
              {{ completing.shipment.total_packages }} packages loaded on {{ trip.vehicle?.plate_number }} at {{ completing.location.name }}. The shipment moves to
              <strong>in transit</strong> and the customer sees it on their tracking.
            </template>
            <template v-else>
              <v-text-field v-model="pod.receiver" label="Received by (name)" :error-messages="podErrors.receiver_name" autofocus />
              <v-file-input
                v-model="pod.file"
                label="Signed POD (photo or PDF)"
                accept="image/*,application/pdf"
                :prepend-icon="mdiCameraOutline"
                :error-messages="podErrors.pod || podErrors.file"
                show-size
              />
            </template>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="completing = null">Cancel</v-btn>
            <v-btn
              color="primary"
              variant="flat"
              :loading="busy === `complete-${completing.id}`"
              :disabled="completing.kind === 'delivery' && (!pod.receiver.trim() || !pod.file)"
              @click="confirmComplete"
            >
              {{ completing.kind === 'pickup' ? 'Loaded & depart' : 'Complete delivery' }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <v-dialog v-model="cancelOpen" max-width="440">
        <v-card class="cp-card pa-2">
          <v-card-title class="font-weight-bold">Cancel trip</v-card-title>
          <v-card-text><v-textarea v-model="cancelReason" label="Reason" rows="2" auto-grow /></v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="cancelOpen = false">Keep it</v-btn>
            <v-btn color="error" variant="flat" :disabled="!cancelReason.trim()" @click="cancel">Cancel trip</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </template>
  </div>
</template>

<style scoped>
.cp-kv {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 4px 0;
  font-size: 0.9rem;
  color: rgba(var(--v-theme-on-surface), 0.72);
}
.cp-kv strong {
  color: rgb(var(--v-theme-on-surface));
}
.cp-stop {
  position: relative;
  display: flex;
  gap: 14px;
  padding: 0 0 22px 0;
}
.cp-stop:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 15px;
  top: 32px;
  bottom: 0;
  width: 2px;
  background: rgba(var(--v-border-color), 0.15);
}
.cp-stop[data-state='done']:not(:last-child)::before {
  background: rgb(var(--v-theme-success));
}
.cp-stop__dot {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: 50%;
  border: 2px solid rgba(var(--v-border-color), 0.2);
  background: rgb(var(--v-theme-surface));
  color: rgba(var(--v-theme-on-surface), 0.5);
}
.cp-stop[data-state='done'] .cp-stop__dot {
  background: rgb(var(--v-theme-success));
  border-color: rgb(var(--v-theme-success));
  color: #fff;
}
.cp-stop[data-state='current'] .cp-stop__dot {
  border-color: rgb(var(--v-theme-secondary));
  color: rgb(var(--v-theme-secondary));
  box-shadow: 0 0 0 5px rgba(var(--v-theme-secondary), 0.15);
}
</style>
