<script setup lang="ts">
import { mdiArrowRight, mdiClose, mdiMagnify, mdiRefresh } from '@mdi/js'
import { useQuery } from '@tanstack/vue-query'
import L from 'leaflet'
import { computed, ref, shallowRef, watch } from 'vue'
import { http } from '@/api/http'
import type { LiveShipment, Mode } from '@/api/types'
import StatusChip from '@/components/logistics/StatusChip.vue'
import BaseMap from '@/components/map/BaseMap.vue'
import { MODE_BY_VALUE, MODES } from '@/constants/logistics'
import { useOrgStore } from '@/stores/org'
import { formatDateTime, timeAgo } from '@/utils/format'
import { HEALTH_COLOR, splitRoute, unwrap, vehicleIcon } from '@/utils/map'

const orgStore = useOrgStore()

const { data, isFetching, dataUpdatedAt, refetch } = useQuery({
  queryKey: computed(() => ['tracking', orgStore.currentId, 'live']),
  queryFn: async () => (await http.get<LiveShipment[]>('/tracking/live/')).data,
  refetchInterval: 60_000, // positions are estimated on the server clock
})

type HealthFilter = 'all' | 'late' | 'risk' | 'ok'
const health = ref<HealthFilter>('all')
const modes = ref<Mode[]>([])
const search = ref('')
const selectedId = ref<string | null>(null)

const rows = computed(() =>
  (data.value ?? []).filter((s) => {
    if (health.value !== 'all' && (s.eta_health ?? 'ok') !== health.value) return false
    if (modes.value.length && !modes.value.includes(s.mode)) return false
    const q = search.value.trim().toLowerCase()
    return !q || [s.reference, s.tracking_number, s.customer, s.origin.code, s.destination.code].some((v) => v.toLowerCase().includes(q))
  }),
)
const counts = computed(() => {
  const all = data.value ?? []
  return {
    all: all.length,
    late: all.filter((s) => s.eta_health === 'late').length,
    risk: all.filter((s) => s.eta_health === 'risk').length,
    ok: all.filter((s) => !s.eta_health || s.eta_health === 'ok').length,
  }
})
const selected = computed(() => rows.value.find((s) => s.id === selectedId.value) ?? null)

// ---------------- map layers
const map = shallowRef<L.Map | null>(null)
let vehicles: L.LayerGroup | null = null
let routeLayer: L.LayerGroup | null = null
let fitted = false

function drawVehicles() {
  if (!map.value) return
  vehicles?.remove()
  vehicles = L.layerGroup().addTo(map.value)
  for (const s of rows.value) {
    if (!s.position) continue
    L.marker([s.position.lat, s.position.lng], {
      icon: vehicleIcon(s.mode, s.eta_health, s.id === selectedId.value),
      zIndexOffset: s.id === selectedId.value ? 1000 : s.eta_health === 'late' ? 500 : 0,
    })
      .bindTooltip(`<strong>${s.reference}</strong><br>${s.origin.code} → ${s.destination.code}`, { direction: 'top', offset: [0, -14] })
      .on('click', () => (selectedId.value = s.id))
      .addTo(vehicles)
  }
  if (!fitted && rows.value.length) {
    const pts = rows.value.filter((s) => s.position).map((s) => [s.position!.lat, s.position!.lng] as [number, number])
    if (pts.length) map.value.fitBounds(L.latLngBounds(pts), { padding: [48, 48], maxZoom: 5 })
    fitted = true
  }
}

function drawRoute() {
  routeLayer?.remove()
  routeLayer = null
  const s = selected.value
  if (!map.value || !s) return
  routeLayer = L.layerGroup().addTo(map.value)
  const route = unwrap(s.route)
  const color = HEALTH_COLOR[s.eta_health ?? 'ok']!
  const { done, todo } = splitRoute(route, s.position?.progress ?? 0)
  L.polyline(todo, { color, weight: 3, opacity: 0.5, dashArray: '6 8' }).addTo(routeLayer)
  L.polyline(done, { color, weight: 4 }).addTo(routeLayer)
  map.value.flyToBounds(L.latLngBounds(route), { padding: [60, 60], maxZoom: 6, duration: 0.6 })
}

function onReady(m: L.Map) {
  map.value = m
  drawVehicles()
}
watch([rows, selectedId], () => {
  drawVehicles()
  drawRoute()
})

const HEALTH_TABS: { value: HealthFilter; label: string; color?: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'late', label: 'Late', color: 'error' },
  { value: 'risk', label: 'At risk', color: 'warning' },
  { value: 'ok', label: 'On track', color: 'primary' },
]
const HEALTH_LABEL: Record<string, string> = { late: 'Past ETA', risk: 'ETA at risk', ok: 'On track' }
</script>

<template>
  <div class="cp-live">
    <v-card class="cp-card cp-live__panel">
      <div class="pa-4 pb-2">
        <div class="d-flex align-center">
          <div>
            <div class="text-h6 font-weight-bold">Live map</div>
            <div class="text-caption text-medium-emphasis">
              {{ counts.all }} shipments moving · updated {{ dataUpdatedAt ? timeAgo(new Date(dataUpdatedAt).toISOString()) : '…' }}
            </div>
          </div>
          <v-spacer />
          <v-btn :icon="mdiRefresh" variant="text" size="small" :loading="isFetching" aria-label="Refresh" @click="refetch()" />
        </div>
        <v-text-field v-model="search" :prepend-inner-icon="mdiMagnify" placeholder="Reference, customer, port…" density="compact" hide-details clearable class="mt-3" />
        <div class="d-flex flex-wrap ga-1 mt-3">
          <v-chip
            v-for="t in HEALTH_TABS"
            :key="t.value"
            :color="health === t.value ? (t.color ?? 'primary') : undefined"
            :variant="health === t.value ? 'flat' : 'tonal'"
            size="small"
            @click="health = t.value"
          >
            {{ t.label }} · {{ counts[t.value] }}
          </v-chip>
        </div>
        <v-btn-toggle v-model="modes" multiple density="compact" class="cp-segmented mt-3 w-100" variant="text">
          <v-btn v-for="m in MODES" :key="m.value" :value="m.value" :prepend-icon="m.icon" class="text-none flex-grow-1">{{ m.label }}</v-btn>
        </v-btn-toggle>
      </div>
      <v-divider />
      <div class="cp-live__list">
        <button
          v-for="s in rows"
          :key="s.id"
          type="button"
          class="cp-live__row"
          :class="{ 'is-selected': s.id === selectedId }"
          @click="selectedId = s.id === selectedId ? null : s.id"
        >
          <span class="cp-live__dot" :style="{ background: HEALTH_COLOR[s.eta_health ?? 'none'] }" />
          <div style="min-width: 0" class="flex-grow-1 text-left">
            <div class="d-flex align-center ga-2">
              <v-icon :icon="MODE_BY_VALUE[s.mode].icon" size="15" class="text-medium-emphasis" />
              <span class="font-weight-bold text-body-2">{{ s.reference }}</span>
              <v-spacer />
              <span class="mono text-caption">{{ s.origin.code }}→{{ s.destination.code }}</span>
            </div>
            <div class="text-caption text-medium-emphasis text-truncate">{{ s.customer }}</div>
            <v-progress-linear :model-value="(s.position?.progress ?? 0) * 100" :color="HEALTH_COLOR[s.eta_health ?? 'ok']" height="3" rounded class="mt-1" />
          </div>
        </button>
        <div v-if="!rows.length && !isFetching" class="pa-6 text-center text-body-2 text-medium-emphasis">No shipments match.</div>
      </div>
    </v-card>

    <div class="cp-live__map cp-card">
      <BaseMap @ready="onReady" />
      <v-card v-if="selected" class="cp-card cp-live__detail pa-4" elevation="8">
        <div class="d-flex align-start ga-2">
          <div class="flex-grow-1" style="min-width: 0">
            <div class="d-flex align-center ga-2 flex-wrap">
              <span class="text-subtitle-1 font-weight-bold">{{ selected.reference }}</span>
              <StatusChip :status="selected.status" />
            </div>
            <div class="text-caption text-medium-emphasis">{{ selected.customer }} · {{ selected.carrier ?? 'No carrier' }}</div>
          </div>
          <v-btn :icon="mdiClose" size="small" variant="text" aria-label="Close" @click="selectedId = null" />
        </div>
        <div class="d-flex align-center ga-2 mt-3 text-body-2">
          <strong class="mono">{{ selected.origin.code }}</strong>
          <v-progress-linear :model-value="(selected.position?.progress ?? 0) * 100" :color="HEALTH_COLOR[selected.eta_health ?? 'ok']" height="6" rounded />
          <strong class="mono">{{ selected.destination.code }}</strong>
        </div>
        <div class="d-flex justify-space-between text-caption text-medium-emphasis mt-1">
          <span>{{ Math.round((selected.position?.progress ?? 0) * 100) }}% of {{ selected.distance_km.toLocaleString() }} km</span>
          <span :class="selected.eta_health === 'late' ? 'text-error font-weight-bold' : ''">
            ETA {{ formatDateTime(selected.eta) }}
          </span>
        </div>
        <v-chip v-if="selected.eta_health && selected.eta_health !== 'ok'" size="small" :color="selected.eta_health === 'late' ? 'error' : 'warning'" variant="tonal" class="mt-2">
          {{ HEALTH_LABEL[selected.eta_health] }}
        </v-chip>
        <v-btn block color="primary" variant="tonal" class="mt-3" :append-icon="mdiArrowRight" :to="{ name: 'shipment-detail', params: { id: selected.id } }">
          Open shipment
        </v-btn>
      </v-card>
      <div class="cp-live__legend">
        <span><i :style="{ background: HEALTH_COLOR.ok }" /> On track</span>
        <span><i :style="{ background: HEALTH_COLOR.risk }" /> At risk</span>
        <span><i :style="{ background: HEALTH_COLOR.late }" /> Past ETA</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cp-live {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 16px;
  height: calc(100vh - 68px - 64px - 40px);
  min-height: 520px;
}
.cp-live__panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.cp-live__list {
  overflow-y: auto;
  flex: 1;
  padding: 6px;
}
.cp-live__row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  padding: 10px;
  border-radius: 12px;
  color: inherit;
}
.cp-live__row:hover {
  background: rgba(var(--v-theme-on-surface), 0.04);
}
.cp-live__row.is-selected {
  background: rgba(var(--v-theme-primary), 0.1);
}
.cp-live__dot {
  width: 9px;
  height: 9px;
  margin-top: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.cp-live__map {
  position: relative;
  overflow: hidden;
  min-height: 420px;
}
.cp-live__detail {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 320px;
  max-width: calc(100% - 32px);
  z-index: 500;
}
.cp-live__legend {
  position: absolute;
  left: 12px;
  bottom: 24px;
  z-index: 500;
  display: flex;
  gap: 12px;
  padding: 6px 12px;
  border-radius: 10px;
  font-size: 0.75rem;
  background: rgba(var(--v-theme-surface), 0.92);
  box-shadow: var(--cp-shadow-sm);
}
.cp-live__legend i {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  margin-right: 4px;
}
@media (max-width: 960px) {
  .cp-live {
    grid-template-columns: 1fr;
    height: auto;
  }
  .cp-live__panel {
    max-height: 420px;
  }
  .cp-live__map {
    height: 70vh;
  }
}
</style>
