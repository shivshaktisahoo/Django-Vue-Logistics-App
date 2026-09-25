<script setup lang="ts">
import { mdiAlertOutline, mdiClockAlertOutline, mdiFire, mdiMagnify, mdiPackageVariantClosed, mdiPlus, mdiSnowflake } from '@mdi/js'
import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { http } from '@/api/http'
import type { Mode, Paginated, ShipmentListItem, ShipmentStatus } from '@/api/types'
import StatusChip from '@/components/logistics/StatusChip.vue'
import RouteLabel from '@/components/logistics/RouteLabel.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useDebounced } from '@/composables/useDebounced'
import { ACTIVE_STATUSES, MODES, STATUS, STATUS_TABS } from '@/constants/logistics'
import { useOrgStore } from '@/stores/org'
import { formatDate, formatNumber, timeAgo } from '@/utils/format'
import { etaHealth } from '@/utils/shipments'

const orgStore = useOrgStore()
const route = useRoute()
const router = useRouter()

type Tab = (typeof STATUS_TABS)[number]
const tab = ref<Tab>((route.query.tab as Tab) || 'active')
const search = ref((route.query.q as string) || '')
const modes = ref<Mode[]>([])
const page = ref(1)
const pageSize = ref(25)
const sortBy = ref<{ key: string; order: 'asc' | 'desc' }[]>([])
const debouncedSearch = useDebounced(search, 300)

const isCustomer = computed(() => orgStore.role === 'customer')
const canBook = computed(() => orgStore.can('shipments.book'))

watch([tab, debouncedSearch, modes], () => {
  page.value = 1
  router.replace({ query: { ...route.query, tab: tab.value, q: debouncedSearch.value || undefined } })
})

function statusParam(t: Tab): string | undefined {
  if (t === 'all') return undefined
  if (t === 'active') return ACTIVE_STATUSES.join(',')
  if (t === 'in_transit') return 'picked_up,in_transit,out_for_delivery'
  return t
}

const baseParams = computed(() => ({
  search: debouncedSearch.value || undefined,
  mode: modes.value.length ? modes.value.join(',') : undefined,
}))

const params = computed(() => ({
  ...baseParams.value,
  status: statusParam(tab.value),
  page: page.value,
  page_size: pageSize.value,
  ordering: sortBy.value[0] ? `${sortBy.value[0].order === 'desc' ? '-' : ''}${sortBy.value[0].key}` : undefined,
}))

const { data, isFetching, isError, refetch } = useQuery({
  queryKey: computed(() => ['shipments', orgStore.currentId, params.value]),
  queryFn: async () => (await http.get<Paginated<ShipmentListItem>>('/shipments/', { params: params.value })).data,
  placeholderData: keepPreviousData,
})

const { data: summary } = useQuery({
  queryKey: computed(() => ['shipments', orgStore.currentId, 'summary', baseParams.value]),
  queryFn: async () =>
    (await http.get<{ counts: Partial<Record<ShipmentStatus, number>> }>('/shipments/summary/', { params: baseParams.value })).data
      .counts,
  placeholderData: keepPreviousData,
})

function tabCount(t: Tab): number | undefined {
  const c = summary.value
  if (!c) return undefined
  const sum = (list: string[]) => list.reduce((n, s) => n + (c[s as ShipmentStatus] ?? 0), 0)
  if (t === 'all') return sum(Object.keys(STATUS))
  if (t === 'active') return sum(ACTIVE_STATUSES)
  return sum(statusParam(t)!.split(','))
}

const TAB_LABEL: Record<Tab, string> = {
  active: 'Active',
  all: 'All',
  draft: 'Drafts',
  booked: 'Booked',
  in_transit: 'Moving',
  at_customs: 'Customs',
  on_hold: 'On hold',
  delivered: 'Delivered',
  picked_up: 'Picked up',
  out_for_delivery: 'Out for delivery',
  cancelled: 'Cancelled',
}

const headers = computed(() =>
  [
    { title: 'Shipment', key: 'reference', sortable: true },
    { title: 'Route', key: 'route', sortable: false },
    isCustomer.value ? null : { title: 'Customer', key: 'customer', sortable: false },
    { title: 'Status', key: 'status', sortable: true },
    { title: 'ETD', key: 'etd', sortable: true },
    { title: 'ETA', key: 'eta', sortable: true },
    { title: 'Cargo', key: 'cargo', sortable: false, align: 'end' as const },
  ].filter((h) => h !== null),
)

function open(_: unknown, row: { item: ShipmentListItem }) {
  router.push({ name: 'shipment-detail', params: { id: row.item.id } })
}
</script>

<template>
  <div>
    <PageHeader
      title="Shipments"
      :subtitle="isCustomer ? 'Your bookings with us, from request to proof of delivery.' : 'Every booking across air, ocean and road.'"
      :icon="mdiPackageVariantClosed"
    >
      <template #actions>
        <v-btn v-if="canBook" color="primary" :prepend-icon="mdiPlus" :to="{ name: 'shipment-new' }">
          {{ isCustomer ? 'Request booking' : 'New shipment' }}
        </v-btn>
      </template>
    </PageHeader>

    <v-card class="cp-card">
      <div class="px-3 pt-2">
        <v-tabs v-model="tab" color="primary" density="comfortable" show-arrows>
          <v-tab v-for="t in STATUS_TABS" :key="t" :value="t" class="text-none">
            {{ TAB_LABEL[t] }}
            <v-chip v-if="tabCount(t) !== undefined" size="x-small" class="ml-2" variant="tonal" :color="tab === t ? 'primary' : undefined">
              {{ tabCount(t) }}
            </v-chip>
          </v-tab>
        </v-tabs>
      </div>
      <v-divider />

      <div class="d-flex flex-wrap align-center ga-3 pa-4">
        <v-text-field
          v-model="search"
          :prepend-inner-icon="mdiMagnify"
          placeholder="Reference, tracking no., HBL/MBL, PO, commodity…"
          hide-details
          clearable
          density="compact"
          style="min-width: 260px; max-width: 460px"
        />
        <v-btn-toggle v-model="modes" multiple density="compact" class="cp-segmented" variant="text">
          <v-btn v-for="m in MODES" :key="m.value" :value="m.value" :prepend-icon="m.icon" class="text-none">{{ m.label }}</v-btn>
        </v-btn-toggle>
      </div>

      <v-alert v-if="isError" type="error" variant="tonal" class="ma-4" text="Couldn't load shipments.">
        <template #append><v-btn variant="text" @click="refetch()">Retry</v-btn></template>
      </v-alert>

      <v-data-table-server
        v-model:page="page"
        v-model:items-per-page="pageSize"
        v-model:sort-by="sortBy"
        :headers="headers"
        :items="data?.results ?? []"
        :items-length="data?.count ?? 0"
        :loading="isFetching"
        :items-per-page-options="[25, 50, 100]"
        class="cp-table"
        hover
        @click:row="open"
      >
        <template #[`item.reference`]="{ item }">
          <div class="py-2">
            <div class="d-flex align-center ga-1 font-weight-bold">
              {{ item.reference }}
              <v-icon v-if="item.is_hazardous" :icon="mdiFire" size="15" color="error" title="Dangerous goods" />
              <v-icon v-if="item.is_temperature_controlled" :icon="mdiSnowflake" size="15" color="info" title="Temperature controlled" />
            </div>
            <div class="text-caption text-medium-emphasis mono">{{ item.tracking_number }}</div>
            <div class="text-caption text-medium-emphasis text-truncate" style="max-width: 200px">{{ item.commodity }}</div>
          </div>
        </template>
        <template #[`item.route`]="{ item }">
          <RouteLabel :origin="item.origin" :destination="item.destination" :mode="item.mode" />
        </template>
        <template #[`item.customer`]="{ item }">
          <div class="font-weight-medium text-truncate" style="max-width: 180px">{{ item.customer.name }}</div>
          <div class="text-caption text-medium-emphasis">{{ item.customer_reference || '—' }}</div>
        </template>
        <template #[`item.status`]="{ item }">
          <StatusChip :status="item.status" />
          <div class="text-caption text-medium-emphasis mt-1">{{ timeAgo(item.updated_at) }}</div>
        </template>
        <template #[`item.etd`]="{ item }">
          <div class="num">{{ formatDate(item.atd ?? item.etd) }}</div>
          <div class="text-caption text-medium-emphasis">{{ item.atd ? 'Departed' : 'Planned' }}</div>
        </template>
        <template #[`item.eta`]="{ item }">
          <div class="num d-flex align-center ga-1">
            {{ formatDate(item.ata ?? item.eta) }}
            <v-icon v-if="etaHealth(item) === 'late'" :icon="mdiClockAlertOutline" color="error" size="16" title="Past ETA" />
            <v-icon v-else-if="etaHealth(item) === 'risk'" :icon="mdiAlertOutline" color="warning" size="16" title="ETA at risk" />
          </div>
          <div class="text-caption" :class="etaHealth(item) === 'late' ? 'text-error font-weight-medium' : 'text-medium-emphasis'">
            {{ item.ata ? 'Delivered' : etaHealth(item) === 'late' ? 'Overdue' : 'Estimated' }}
          </div>
        </template>
        <template #[`item.cargo`]="{ item }">
          <div class="num">{{ formatNumber(item.chargeable_weight_kg, 'kg') }}</div>
          <div class="text-caption text-medium-emphasis">{{ item.total_packages }} pkg · chargeable</div>
        </template>
        <template #no-data>
          <EmptyState
            :icon="mdiPackageVariantClosed"
            title="No shipments here"
            :text="search ? 'Nothing matches your search. Try a reference, tracking number or PO.' : 'Shipments in this stage will show up here.'"
          />
        </template>
      </v-data-table-server>
    </v-card>
  </div>
</template>
