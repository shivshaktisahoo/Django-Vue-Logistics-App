<script setup lang="ts">
import {
  mdiAlertOutline,
  mdiArrowLeft,
  mdiCalendarClock,
  mdiChevronDown,
  mdiClockAlertOutline,
  mdiContentCopy,
  mdiShareVariantOutline,
  mdiFire,
  mdiPencilOutline,
  mdiSnowflake,
} from '@mdi/js'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { http } from '@/api/http'
import type { Shipment, ShipmentStatus } from '@/api/types'
import RouteLabel from '@/components/logistics/RouteLabel.vue'
import StatusChip from '@/components/logistics/StatusChip.vue'
import { CONTAINER_TYPES, MODE_BY_VALUE, PACKAGE_KINDS, SERVICE_LABEL, STATUS, TRANSITION_ACTION } from '@/constants/logistics'
import { useNotify } from '@/stores/notify'
import { useOrgStore } from '@/stores/org'
import { formatDateTime, formatMoney, formatNumber } from '@/utils/format'
import { etaHealth, hoursLate } from '@/utils/shipments'
import AuditTrail from '../components/AuditTrail.vue'
import RoadProcurement from '../components/RoadProcurement.vue'
import ShipmentDocuments from '../components/ShipmentDocuments.vue'
import EventTimeline from '../components/EventTimeline.vue'
import JourneyBar from '../components/JourneyBar.vue'
import StatusDialog from '../components/StatusDialog.vue'
import RouteMap from '@/components/map/RouteMap.vue'
import ExceptionCard from '@/modules/exceptions/components/ExceptionCard.vue'
import type { LiveShipment, Paginated, ShipmentExceptionItem } from '@/api/types'

const route = useRoute()
const orgStore = useOrgStore()
const notify = useNotify()
const queryClient = useQueryClient()
const id = computed(() => route.params.id as string)

const key = computed(() => ['shipment', orgStore.currentId, id.value])
const { data: s, isLoading, isError } = useQuery({
  queryKey: key,
  queryFn: async () => (await http.get<Shipment>(`/shipments/${id.value}/`)).data,
})

const tab = ref('overview')

const hasRoute = computed(() => !!s.value && !['draft', 'cancelled'].includes(s.value.status))
const { data: live } = useQuery({
  queryKey: computed(() => [...key.value, 'live']),
  queryFn: async () => (await http.get<LiveShipment>(`/tracking/shipments/${id.value}/`)).data,
  enabled: hasRoute,
})
const { data: openExceptions } = useQuery({
  queryKey: computed(() => ['exceptions', orgStore.currentId, 'shipment', id.value]),
  queryFn: async () =>
    (await http.get<Paginated<ShipmentExceptionItem>>('/exceptions/', { params: { shipment: id.value, status: 'open,acknowledged' } })).data
      .results,
  enabled: computed(() => orgStore.can('exceptions.view')),
})
function refreshExceptions() {
  queryClient.invalidateQueries({ queryKey: ['exceptions', orgStore.currentId] })
  queryClient.invalidateQueries({ queryKey: [...key.value, 'audit'] })
  queryClient.invalidateQueries({ queryKey: [...key.value, 'live'] })
  queryClient.invalidateQueries({ queryKey: ['exceptions', orgStore.currentId] })
}
const dialog = ref<{ open: boolean; target: ShipmentStatus | 'resume' | null }>({ open: false, target: null })
const isInternal = computed(() => orgStore.role === 'admin' || orgStore.role === 'ops')

// The first "forward" move is the primary button; hold/cancel live in the menu.
const SIDE_ACTIONS = new Set(['on_hold', 'cancelled'])
const primary = computed(() => s.value?.allowed_transitions.find((t) => !SIDE_ACTIONS.has(t)) ?? null)
const secondary = computed(() => s.value?.allowed_transitions.filter((t) => t !== primary.value) ?? [])
const health = computed(() => (s.value ? etaHealth(s.value) : null))
const late = computed(() => (s.value ? hoursLate(s.value) : 0))

function act(target: ShipmentStatus | 'resume') {
  dialog.value = { open: true, target }
}

function onChanged(updated: Shipment) {
  queryClient.setQueryData(key.value, updated)
  queryClient.invalidateQueries({ queryKey: ['shipments', orgStore.currentId] })
  queryClient.invalidateQueries({ queryKey: [...key.value, 'events'] })
  queryClient.invalidateQueries({ queryKey: [...key.value, 'audit'] })
  notify.success(`${updated.reference} is now ${STATUS[updated.status].label.toLowerCase()}`)
}

function shareLink() {
  if (s.value) copy(`${window.location.origin}/track/${s.value.tracking_number}`, 'Public tracking link copied')
}

async function copy(text: string, message = 'Copied') {
  await navigator.clipboard?.writeText(text)
  notify.success(message)
}

const kindLabel = (k: string) => PACKAGE_KINDS.find((p) => p.value === k)?.title ?? k
const containerLabel = (t: string) => CONTAINER_TYPES.find((c) => c.value === t)?.title ?? t
const billLabels = computed(() =>
  s.value?.mode === 'air' ? ['HAWB', 'MAWB', 'Flight'] : s.value?.mode === 'ocean' ? ['House B/L', 'Master B/L', 'Vessel / voyage'] : ['CMR note', 'Master ref', 'Trip ref'],
)
</script>

<template>
  <div>
    <v-btn variant="text" :prepend-icon="mdiArrowLeft" class="mb-2 ml-n2" :to="{ name: 'shipments' }">Shipments</v-btn>

    <v-alert v-if="isError" type="error" variant="tonal" text="This shipment doesn't exist or you don't have access to it." />
    <v-skeleton-loader v-else-if="isLoading || !s" type="heading, paragraph, card" class="bg-transparent" />

    <template v-else>
      <!-- Header -->
      <div class="d-flex flex-wrap align-start ga-4 mb-5">
        <v-avatar color="primary" variant="tonal" rounded="lg" size="52" class="d-none d-sm-flex">
          <v-icon :icon="MODE_BY_VALUE[s.mode].icon" size="28" />
        </v-avatar>
        <div class="flex-grow-1" style="min-width: 0">
          <div class="d-flex flex-wrap align-center ga-2">
            <h1 class="text-h5 font-weight-bold">{{ s.reference }}</h1>
            <StatusChip :status="s.status" />
            <v-chip v-if="s.is_hazardous" size="small" color="error" variant="tonal" :prepend-icon="mdiFire">DG</v-chip>
            <v-chip v-if="s.is_temperature_controlled" size="small" color="info" variant="tonal" :prepend-icon="mdiSnowflake">Reefer</v-chip>
          </div>
          <div class="d-flex flex-wrap align-center ga-2 text-body-2 text-medium-emphasis mt-1">
            <span>Tracking</span>
            <button class="mono cp-copy" type="button" @click="copy(s.tracking_number)">
              {{ s.tracking_number }} <v-icon :icon="mdiContentCopy" size="13" />
            </button>
            <span>· {{ MODE_BY_VALUE[s.mode].label }} {{ SERVICE_LABEL[s.service_type] }} · {{ s.incoterm }}</span>
          </div>
        </div>
        <div class="d-flex flex-wrap ga-2">
          <v-btn v-if="hasRoute" variant="text" :prepend-icon="mdiShareVariantOutline" @click="shareLink">Share tracking</v-btn>
          <v-btn v-if="s.can_edit" variant="tonal" :prepend-icon="mdiPencilOutline" :to="{ name: 'shipment-edit', params: { id: s.id } }">Edit</v-btn>
          <v-btn v-if="primary" :color="TRANSITION_ACTION[primary].color" :prepend-icon="TRANSITION_ACTION[primary].icon" @click="act(primary)">
            {{ TRANSITION_ACTION[primary].label }}
          </v-btn>
          <v-menu v-if="secondary.length">
            <template #activator="{ props }">
              <v-btn v-bind="props" variant="tonal" :append-icon="mdiChevronDown">More</v-btn>
            </template>
            <v-list density="comfortable">
              <v-list-item
                v-for="t in secondary"
                :key="t"
                :prepend-icon="TRANSITION_ACTION[t].icon"
                :title="TRANSITION_ACTION[t].label"
                :base-color="TRANSITION_ACTION[t].color"
                @click="act(t)"
              />
            </v-list>
          </v-menu>
        </div>
      </div>

      <!-- Alerts -->
      <v-alert v-if="s.status === 'on_hold'" type="warning" variant="tonal" class="mb-4" title="Shipment on hold">
        Held while {{ STATUS[s.held_from_status as ShipmentStatus]?.label.toLowerCase() }}. See the timeline for the reason.
      </v-alert>
      <v-alert v-else-if="s.status === 'draft' && isInternal" type="info" variant="tonal" class="mb-4" title="Awaiting confirmation">
        Check the details, assign a carrier and confirm the booking.
      </v-alert>
      <v-alert v-else-if="health === 'late' && !openExceptions?.length" type="error" variant="tonal" class="mb-4" :icon="mdiClockAlertOutline" title="Past ETA">
        The promised arrival was {{ formatDateTime(s.eta) }} and the shipment hasn't been delivered.
      </v-alert>
      <v-alert v-else-if="health === 'risk' && !openExceptions?.length" type="warning" variant="tonal" class="mb-4" :icon="mdiAlertOutline" title="ETA at risk">
        Due within 24 hours but not yet at the destination.
      </v-alert>

      <!-- Open exceptions -->
      <div v-if="openExceptions?.length" class="d-flex flex-column ga-2 mb-4">
        <ExceptionCard
          v-for="e in openExceptions"
          :key="e.id"
          :exc="e"
          :can-manage="orgStore.can('exceptions.manage')"
          :show-shipment="false"
          @changed="refreshExceptions"
        />
      </div>

      <!-- Journey -->
      <v-card class="cp-card pa-5 pa-md-6 mb-5">
        <div class="d-flex flex-wrap align-center justify-space-between ga-4 mb-6">
          <RouteLabel :origin="s.origin" :destination="s.destination" :mode="s.mode" />
          <div class="d-flex flex-wrap ga-6">
            <div>
              <div class="text-caption text-medium-emphasis">{{ s.atd ? 'Departed' : 'ETD' }}</div>
              <div class="font-weight-bold num">{{ formatDateTime(s.atd ?? s.etd) }}</div>
            </div>
            <div>
              <div class="text-caption text-medium-emphasis">{{ s.ata ? 'Delivered' : 'ETA' }}</div>
              <div class="font-weight-bold num" :class="{ 'text-error': health === 'late' }">{{ formatDateTime(s.ata ?? s.eta) }}</div>
              <div v-if="late >= 1" class="text-caption text-error">{{ Math.round(late) }} h after ETA</div>
            </div>
          </div>
        </div>
        <JourneyBar :shipment="s" />
      </v-card>

      <v-card v-if="live" class="cp-card overflow-hidden mb-5">
        <RouteMap
          :route="live.route"
          :position="live.position"
          :origin="live.origin"
          :destination="live.destination"
          :mode="live.mode"
          :health="live.eta_health"
          height="340px"
        />
      </v-card>

      <v-row>
        <v-col cols="12" lg="7">
          <v-card class="cp-card">
            <v-tabs v-model="tab" color="primary" class="px-2">
              <v-tab value="overview" class="text-none">Overview</v-tab>
              <v-tab value="cargo" class="text-none">Cargo ({{ s.packages.length }})</v-tab>
              <v-tab v-if="orgStore.can('documents.view')" value="documents" class="text-none">Documents</v-tab>
              <v-tab v-if="orgStore.can('audit.view')" value="activity" class="text-none">Activity</v-tab>
            </v-tabs>
            <v-divider />
            <v-window v-model="tab" class="pa-5">
              <v-window-item value="overview">
                <v-row>
                  <v-col v-for="p in [
                    { label: 'Customer', party: s.customer },
                    { label: 'Shipper', party: s.shipper },
                    { label: 'Consignee', party: s.consignee },
                  ]" :key="p.label" cols="12" sm="4">
                    <div class="cp-section-title mb-1">{{ p.label }}</div>
                    <div class="font-weight-bold">{{ p.party.name }}</div>
                    <div class="text-body-2 text-medium-emphasis">{{ p.party.city }} {{ p.party.country }}</div>
                  </v-col>
                </v-row>
                <v-divider class="my-5" />
                <div class="cp-grid">
                  <div><span>Carrier</span>{{ s.carrier ? `${s.carrier.name} (${s.carrier.code})` : 'Not assigned' }}</div>
                  <div><span>{{ billLabels[2] }}</span>{{ s.voyage_number || '—' }}</div>
                  <div><span>{{ billLabels[0] }}</span><span class="mono">{{ s.house_bill || '—' }}</span></div>
                  <div><span>{{ billLabels[1] }}</span><span class="mono">{{ s.master_bill || '—' }}</span></div>
                  <div><span>Customer ref</span>{{ s.customer_reference || '—' }}</div>
                  <div><span>Commodity</span>{{ s.commodity }}</div>
                  <div><span>HS code</span><span class="mono">{{ s.hs_code || '—' }}</span></div>
                  <div><span>Declared value</span>{{ s.declared_value ? formatMoney(s.declared_value, s.currency) : '—' }}</div>
                </div>
                <template v-if="s.special_instructions">
                  <v-divider class="my-5" />
                  <div class="cp-section-title mb-1">Special instructions</div>
                  <div class="text-body-2" style="white-space: pre-line">{{ s.special_instructions }}</div>
                </template>
              </v-window-item>

              <v-window-item value="cargo">
                <div class="d-flex flex-wrap ga-6 mb-5">
                  <div><div class="text-caption text-medium-emphasis">Pieces</div><div class="text-h6 font-weight-bold num">{{ s.total_packages }}</div></div>
                  <div><div class="text-caption text-medium-emphasis">Gross</div><div class="text-h6 font-weight-bold num">{{ formatNumber(s.gross_weight_kg, 'kg') }}</div></div>
                  <div><div class="text-caption text-medium-emphasis">Volume</div><div class="text-h6 font-weight-bold num">{{ formatNumber(s.volume_cbm, 'm³') }}</div></div>
                  <div><div class="text-caption text-medium-emphasis">Chargeable</div><div class="text-h6 font-weight-bold num text-primary">{{ formatNumber(s.chargeable_weight_kg, 'kg') }}</div></div>
                </div>
                <v-table density="comfortable" class="cp-table">
                  <thead>
                    <tr><th>Type</th><th>Details</th><th class="text-end">Qty</th><th class="text-end">Weight</th><th class="text-end">Volume</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="p in s.packages" :key="p.id">
                      <td>{{ p.kind === 'container' ? containerLabel(p.container_type) : kindLabel(p.kind) }}</td>
                      <td>
                        <div v-if="p.container_number" class="mono font-weight-bold">{{ p.container_number }}</div>
                        <div v-if="p.seal_number" class="text-caption text-medium-emphasis">Seal {{ p.seal_number }}</div>
                        <div v-if="p.length_cm" class="text-caption text-medium-emphasis">{{ Number(p.length_cm) }}×{{ Number(p.width_cm) }}×{{ Number(p.height_cm) }} cm</div>
                        <div class="text-caption">{{ p.description }}</div>
                      </td>
                      <td class="text-end num">{{ p.quantity }}</td>
                      <td class="text-end num">{{ formatNumber(p.weight_kg, 'kg') }}</td>
                      <td class="text-end num">{{ Number(p.volume_cbm) ? formatNumber(p.volume_cbm, 'm³') : '—' }}</td>
                    </tr>
                  </tbody>
                </v-table>
              </v-window-item>

              <v-window-item v-if="orgStore.can('documents.view')" value="documents">
                <ShipmentDocuments :shipment-id="s.id" />
              </v-window-item>

              <v-window-item v-if="orgStore.can('audit.view')" value="activity">
                <AuditTrail :entity-id="s.id" />
              </v-window-item>
            </v-window>
          </v-card>
        </v-col>

        <v-col cols="12" lg="5">
          <RoadProcurement v-if="s.mode === 'road'" :shipment="s" />
          <v-card class="cp-card pa-5">
            <EventTimeline :shipment-id="s.id" :can-add="orgStore.can('tracking.update') && !['draft', 'cancelled'].includes(s.status)" />
          </v-card>
          <div class="text-caption text-medium-emphasis mt-3 d-flex align-center ga-1">
            <v-icon :icon="mdiCalendarClock" size="14" /> Times shown in your local time zone.
          </div>
        </v-col>
      </v-row>

      <StatusDialog v-model="dialog.open" :shipment="s" :target="dialog.target" @done="onChanged" />
    </template>
  </div>
</template>

<style scoped>
.cp-copy {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 1px 8px;
  border-radius: 8px;
  background: rgba(var(--v-theme-on-surface), 0.05);
  color: inherit;
}
.cp-copy:hover {
  background: rgba(var(--v-theme-primary), 0.1);
}
.cp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px 24px;
}
.cp-grid > div {
  display: flex;
  flex-direction: column;
  font-size: 0.92rem;
  font-weight: 500;
}
.cp-grid > div > span:first-child {
  font-size: 0.75rem;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.55);
  margin-bottom: 2px;
}
</style>
