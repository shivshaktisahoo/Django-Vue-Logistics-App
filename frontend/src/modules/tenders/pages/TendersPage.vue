<script setup lang="ts">
import { mdiArrowRightThin, mdiClockOutline, mdiFire, mdiGavel, mdiPlus, mdiSnowflake, mdiWeightKilogram } from '@mdi/js'
import { keepPreviousData, useQuery } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { http } from '@/api/http'
import type { Paginated, Tender, TenderStatus } from '@/api/types'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { VEHICLE_TYPES } from '@/constants/logistics'
import { BID_STATUS, TENDER_STATUS } from '@/constants/procurement'
import { useOrgStore } from '@/stores/org'
import { countdown } from '@/utils/download'
import { formatDateTime, formatMoney, formatNumber } from '@/utils/format'
import NewTenderDialog from '../components/NewTenderDialog.vue'

const orgStore = useOrgStore()
const isCarrier = computed(() => orgStore.role === 'carrier')
const canManage = computed(() => orgStore.can('tenders.manage'))

type Tab = TenderStatus | 'all'
const tab = ref<Tab>('open')
const page = ref(1)
const dialog = ref(false)

const params = computed(() => ({ status: tab.value === 'all' ? undefined : tab.value, page: page.value }))
const { data, isFetching } = useQuery({
  queryKey: computed(() => ['tenders', orgStore.currentId, params.value]),
  queryFn: async () => (await http.get<Paginated<Tender>>('/tenders/', { params: params.value })).data,
  placeholderData: keepPreviousData,
  refetchInterval: 60_000,
})
const { data: summary } = useQuery({
  queryKey: computed(() => ['tenders', orgStore.currentId, 'summary']),
  queryFn: async () => (await http.get<{ counts: Record<string, number> }>('/tenders/summary/')).data.counts,
})
const pages = computed(() => Math.max(1, Math.ceil((data.value?.count ?? 0) / 25)))
const vehicleLabel = (v: string) => VEHICLE_TYPES.find((t) => t.value === v)?.title ?? v

/** Positive = over target (bad for us), negative = under target. */
function vsTarget(t: Tender): number | null {
  if (!t.best_amount || !t.target_rate) return null
  return Math.round(((Number(t.best_amount) - Number(t.target_rate)) / Number(t.target_rate)) * 100)
}
</script>

<template>
  <div>
    <PageHeader
      :title="isCarrier ? 'Load board' : 'Tenders & bids'"
      :subtitle="isCarrier ? 'Loads you are invited to price. Bids are sealed; other carriers never see yours.' : 'Spot RFQs for road legs: invite carriers, compare sealed bids, award in one click.'"
      :icon="mdiGavel"
    >
      <template #actions>
        <v-btn v-if="canManage" color="primary" :prepend-icon="mdiPlus" @click="dialog = true">New tender</v-btn>
      </template>
    </PageHeader>

    <v-alert v-if="isCarrier && summary?.awaiting_my_bid" type="info" variant="tonal" class="mb-4" :icon="mdiGavel">
      <strong>{{ summary.awaiting_my_bid }}</strong> open load{{ summary.awaiting_my_bid === 1 ? '' : 's' }} waiting for your bid.
    </v-alert>

    <v-card class="cp-card">
      <div class="px-3 pt-2">
        <v-tabs v-model="tab" color="primary" density="comfortable" @update:model-value="page = 1">
          <v-tab v-for="s in ['open', 'closed', 'awarded', 'cancelled', 'all'] as Tab[]" :key="s" :value="s" class="text-none">
            {{ s === 'all' ? 'All' : TENDER_STATUS[s as TenderStatus].label }}
            <v-chip v-if="s !== 'all' && summary?.[s]" size="x-small" class="ml-2" variant="tonal">{{ summary[s] }}</v-chip>
          </v-tab>
        </v-tabs>
      </div>
      <v-divider />
      <v-progress-linear :active="isFetching" indeterminate color="primary" height="2" />

      <div class="pa-4 d-flex flex-column ga-3">
        <router-link
          v-for="t in data?.results ?? []"
          :key="t.id"
          :to="{ name: 'tender-detail', params: { id: t.id } }"
          class="cp-tender"
        >
          <div class="cp-tender__main">
            <div class="d-flex flex-wrap align-center ga-2 mb-1">
              <span class="font-weight-bold">{{ t.reference }}</span>
              <v-chip size="x-small" :color="TENDER_STATUS[t.status].color" variant="tonal" :prepend-icon="TENDER_STATUS[t.status].icon">
                {{ TENDER_STATUS[t.status].label }}
              </v-chip>
              <span v-if="t.customer" class="text-caption text-medium-emphasis">· {{ t.customer }}</span>
            </div>
            <div class="d-flex align-center ga-2 text-body-1 font-weight-medium">
              {{ t.shipment.origin.city }} <v-icon :icon="mdiArrowRightThin" /> {{ t.shipment.destination.city }}
              <span class="mono text-caption text-medium-emphasis">{{ t.shipment.origin.code }}→{{ t.shipment.destination.code }}</span>
            </div>
            <div class="d-flex flex-wrap ga-3 text-caption text-medium-emphasis mt-1">
              <span>{{ vehicleLabel(t.vehicle_type) }}</span>
              <span class="d-inline-flex align-center ga-1"><v-icon :icon="mdiWeightKilogram" size="14" />{{ formatNumber(t.shipment.gross_weight_kg, 'kg') }} · {{ t.shipment.total_packages }} pallets</span>
              <span v-if="t.shipment.is_temperature_controlled" class="text-info d-inline-flex align-center ga-1"><v-icon :icon="mdiSnowflake" size="14" />Reefer</span>
              <span v-if="t.shipment.is_hazardous" class="text-error d-inline-flex align-center ga-1"><v-icon :icon="mdiFire" size="14" />DG</span>
              <span>Pickup {{ formatDateTime(t.pickup_at) }}</span>
            </div>
          </div>

          <div class="cp-tender__side">
            <div v-if="t.status === 'open'" class="text-caption d-flex align-center ga-1 justify-end" :class="new Date(t.closes_at).getTime() - Date.now() < 3 * 3600_000 ? 'text-warning font-weight-bold' : 'text-medium-emphasis'">
              <v-icon :icon="mdiClockOutline" size="14" /> Closes {{ countdown(t.closes_at) }}
            </div>
            <template v-if="!isCarrier">
              <div class="text-h6 font-weight-bold num">{{ t.best_amount ? formatMoney(t.best_amount, t.currency) : '—' }}</div>
              <div class="text-caption text-medium-emphasis">
                {{ t.bid_count }} of {{ t.invited_count }} bid
                <span v-if="vsTarget(t) !== null" :class="vsTarget(t)! <= 0 ? 'text-success' : 'text-error'" class="font-weight-bold">
                  · {{ vsTarget(t)! > 0 ? '+' : '' }}{{ vsTarget(t) }}% vs target
                </span>
              </div>
              <div v-if="t.awarded_to" class="text-caption text-success font-weight-bold">→ {{ t.awarded_to }}</div>
            </template>
            <template v-else>
              <template v-if="t.my_bid">
                <div class="text-h6 font-weight-bold num">{{ formatMoney(t.my_bid.amount, t.my_bid.currency) }}</div>
                <v-chip size="x-small" :color="BID_STATUS[t.my_bid.status].color" variant="tonal">Your bid · {{ BID_STATUS[t.my_bid.status].label }}</v-chip>
              </template>
              <v-btn v-else-if="t.status === 'open'" color="primary" size="small" variant="flat">Place bid</v-btn>
              <div v-else class="text-caption text-medium-emphasis">You didn't bid</div>
            </template>
          </div>
        </router-link>
        <EmptyState
          v-if="!data?.results.length && !isFetching"
          :icon="mdiGavel"
          :title="tab === 'open' ? 'No open tenders' : 'Nothing here'"
          :text="isCarrier ? 'New loads you are invited to will appear here.' : 'Tender a booked road shipment to get carrier prices.'"
        />
      </div>
      <div v-if="pages > 1" class="d-flex justify-center pb-4"><v-pagination v-model="page" :length="pages" density="comfortable" rounded /></div>
    </v-card>

    <NewTenderDialog v-model="dialog" />
  </div>
</template>

<style scoped>
.cp-tender {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 16px;
  border-radius: 14px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  color: inherit;
  text-decoration: none;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}
.cp-tender:hover {
  border-color: rgba(var(--v-theme-primary), 0.4);
  box-shadow: var(--cp-shadow-md);
}
.cp-tender__main {
  flex: 1 1 360px;
  min-width: 0;
}
.cp-tender__side {
  flex: 0 0 auto;
  text-align: right;
  min-width: 170px;
}
@media (max-width: 600px) {
  .cp-tender__side {
    text-align: left;
  }
}
</style>
