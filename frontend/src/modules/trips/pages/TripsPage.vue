<script setup lang="ts">
import { mdiArrowRightThin, mdiTruckOutline } from '@mdi/js'
import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { http } from '@/api/http'
import type { Paginated, Trip, TripStatus } from '@/api/types'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { TRIP_STATUS } from '@/constants/procurement'
import { useOrgStore } from '@/stores/org'
import { formatDateTime, formatMoney } from '@/utils/format'

const orgStore = useOrgStore()
const router = useRouter()
const isCarrier = computed(() => orgStore.role === 'carrier')

type Tab = 'active' | TripStatus | 'all'
const tab = ref<Tab>('active')
const page = ref(1)
const statusParam = computed(() =>
  tab.value === 'all' ? undefined : tab.value === 'active' ? 'planned,dispatched,in_progress' : tab.value,
)
const params = computed(() => ({ status: statusParam.value, page: page.value, ordering: tab.value === 'completed' ? '-planned_start' : 'planned_start' }))

const { data, isFetching } = useQuery({
  queryKey: computed(() => ['trips', orgStore.currentId, params.value]),
  queryFn: async () => (await http.get<Paginated<Trip>>('/trips/', { params: params.value })).data,
  placeholderData: keepPreviousData,
})

const headers = computed(() =>
  [
    { title: 'Trip', key: 'reference' },
    { title: 'Route', key: 'route', sortable: false },
    isCarrier.value ? null : { title: 'Carrier', key: 'carrier', sortable: false },
    { title: 'Truck & driver', key: 'vehicle', sortable: false },
    { title: 'Pickup', key: 'planned_start', sortable: false },
    { title: 'Progress', key: 'status', sortable: false },
    { title: 'Rate', key: 'agreed_rate', sortable: false, align: 'end' as const },
  ].filter((h) => h !== null),
)

function openTrip(_: unknown, row: { item: Trip }) {
  router.push({ name: 'trip-detail', params: { id: row.item.id } })
}

function progress(t: Trip) {
  return (t.stops.filter((s) => s.completed_at).length / Math.max(t.stops.length, 1)) * 100
}
</script>

<template>
  <div>
    <PageHeader
      :title="isCarrier ? 'My trips' : 'Trips'"
      :subtitle="isCarrier ? 'Loads you won: dispatch a truck, run the stops, capture the POD.' : 'Road execution by your haulage partners.'"
      :icon="mdiTruckOutline"
    />
    <v-card class="cp-card">
      <div class="px-3 pt-2">
        <v-tabs v-model="tab" color="primary" density="comfortable" @update:model-value="page = 1">
          <v-tab value="active" class="text-none">Active</v-tab>
          <v-tab value="completed" class="text-none">Completed</v-tab>
          <v-tab value="cancelled" class="text-none">Cancelled</v-tab>
          <v-tab value="all" class="text-none">All</v-tab>
        </v-tabs>
      </div>
      <v-divider />
      <v-data-table-server
        v-model:page="page"
        :headers="headers"
        :items="data?.results ?? []"
        :items-length="data?.count ?? 0"
        :items-per-page="25"
        :loading="isFetching"
        class="cp-table"
        hover
        @click:row="openTrip"
      >
        <template #[`item.reference`]="{ item }">
          <div class="font-weight-bold">{{ item.reference }}</div>
          <div class="text-caption text-medium-emphasis">{{ item.stops[0]?.shipment.reference }}</div>
        </template>
        <template #[`item.route`]="{ item }">
          <div class="d-flex align-center ga-1 mono font-weight-bold">
            {{ item.stops[0]?.location.code }} <v-icon :icon="mdiArrowRightThin" size="18" /> {{ item.stops[item.stops.length - 1]?.location.code }}
          </div>
          <div class="text-caption text-medium-emphasis">{{ item.stops[0]?.shipment.commodity }}</div>
        </template>
        <template #[`item.carrier`]="{ item }">{{ item.carrier.name }}</template>
        <template #[`item.vehicle`]="{ item }">
          <template v-if="item.vehicle">
            <div class="mono font-weight-bold">{{ item.vehicle.plate_number }}</div>
            <div class="text-caption text-medium-emphasis">{{ item.driver?.name }}</div>
          </template>
          <span v-else class="text-warning text-caption font-weight-bold">Not dispatched</span>
        </template>
        <template #[`item.planned_start`]="{ item }">{{ formatDateTime(item.planned_start) }}</template>
        <template #[`item.status`]="{ item }">
          <v-chip size="small" :color="TRIP_STATUS[item.status].color" variant="tonal" :prepend-icon="TRIP_STATUS[item.status].icon">
            {{ TRIP_STATUS[item.status].label }}
          </v-chip>
          <v-progress-linear :model-value="progress(item)" :color="TRIP_STATUS[item.status].color" height="3" rounded class="mt-1" style="max-width: 140px" />
        </template>
        <template #[`item.agreed_rate`]="{ item }"><span class="num">{{ formatMoney(item.agreed_rate, item.currency) }}</span></template>
        <template #no-data>
          <EmptyState :icon="mdiTruckOutline" title="No trips here" :text="isCarrier ? 'Win a tender on the load board to get a trip.' : 'Award a tender to create a trip.'" />
        </template>
      </v-data-table-server>
    </v-card>
  </div>
</template>
