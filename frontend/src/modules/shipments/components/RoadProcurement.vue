<script setup lang="ts">
import { mdiArrowRight, mdiGavel, mdiTruckOutline } from '@mdi/js'
import { useQuery } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { http } from '@/api/http'
import type { Paginated, Shipment, Tender, Trip } from '@/api/types'
import { TENDER_STATUS, TRIP_STATUS } from '@/constants/procurement'
import NewTenderDialog from '@/modules/tenders/components/NewTenderDialog.vue'
import { useOrgStore } from '@/stores/org'
import { countdown } from '@/utils/download'
import { formatMoney } from '@/utils/format'

/** Tender → trip status for a road shipment, with a shortcut to tender it. */
const props = defineProps<{ shipment: Shipment }>()
const orgStore = useOrgStore()
const dialog = ref(false)

const { data: tenders } = useQuery({
  queryKey: computed(() => ['tenders', orgStore.currentId, 'for-shipment', props.shipment.id]),
  queryFn: async () => (await http.get<Paginated<Tender>>('/tenders/', { params: { shipment: props.shipment.id } })).data.results,
  enabled: computed(() => orgStore.can('tenders.view')),
})
const { data: trips } = useQuery({
  queryKey: computed(() => ['trips', orgStore.currentId, 'for-shipment', props.shipment.id]),
  queryFn: async () => (await http.get<Paginated<Trip>>('/trips/', { params: { shipment: props.shipment.id } })).data.results,
  enabled: computed(() => orgStore.can('trips.view')),
})

const live = computed(() => tenders.value?.find((t) => t.status !== 'cancelled') ?? null)
const trip = computed(() => trips.value?.find((t) => t.status !== 'cancelled') ?? null)
const canTender = computed(
  () => orgStore.can('tenders.manage') && ['draft', 'booked'].includes(props.shipment.status) && !live.value && tenders.value !== undefined,
)
</script>

<template>
  <v-card v-if="live || trip || canTender" class="cp-card pa-5 mb-4">
    <div class="cp-section-title mb-3">Road procurement</div>
    <div v-if="trip" class="d-flex align-center ga-3 mb-3">
      <v-avatar :color="TRIP_STATUS[trip.status].color" variant="tonal" rounded="lg"><v-icon :icon="mdiTruckOutline" /></v-avatar>
      <div class="flex-grow-1" style="min-width: 0">
        <div class="font-weight-bold">{{ trip.reference }} · {{ TRIP_STATUS[trip.status].label }}</div>
        <div class="text-caption text-medium-emphasis">
          {{ trip.carrier.name }} · {{ trip.vehicle ? `${trip.vehicle.plate_number}, ${trip.driver?.name}` : 'truck not assigned yet' }}
        </div>
      </div>
      <v-btn size="small" variant="tonal" :append-icon="mdiArrowRight" :to="{ name: 'trip-detail', params: { id: trip.id } }">Trip</v-btn>
    </div>
    <div v-if="live" class="d-flex align-center ga-3">
      <v-avatar :color="TENDER_STATUS[live.status].color" variant="tonal" rounded="lg"><v-icon :icon="mdiGavel" /></v-avatar>
      <div class="flex-grow-1" style="min-width: 0">
        <div class="font-weight-bold">{{ live.reference }} · {{ TENDER_STATUS[live.status].label }}</div>
        <div class="text-caption text-medium-emphasis">
          <template v-if="live.status === 'open'">{{ live.bid_count }} of {{ live.invited_count }} bid · closes {{ countdown(live.closes_at) }}</template>
          <template v-else-if="live.awarded_to">Won by {{ live.awarded_to }}</template>
          <template v-else>{{ live.bid_count }} bids to review</template>
          <template v-if="live.best_amount"> · best {{ formatMoney(live.best_amount, live.currency) }}</template>
        </div>
      </div>
      <v-btn size="small" variant="tonal" :append-icon="mdiArrowRight" :to="{ name: 'tender-detail', params: { id: live.id } }">Tender</v-btn>
    </div>
    <template v-if="canTender">
      <div class="text-body-2 text-medium-emphasis mb-3">No carrier secured for this road leg yet.</div>
      <v-btn color="primary" block :prepend-icon="mdiGavel" @click="dialog = true">Tender this load</v-btn>
      <NewTenderDialog v-model="dialog" :shipment-id="shipment.id" />
    </template>
  </v-card>
</template>
