<script setup lang="ts">
import {
  mdiArrowLeft,
  mdiArrowRight,
  mdiCancel,
  mdiClockOutline,
  mdiFire,
  mdiLightningBolt,
  mdiSnowflake,
  mdiTrophyOutline,
  mdiTruckOutline,
} from '@mdi/js'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage, fieldErrors, http } from '@/api/http'
import type { Bid, TenderDetail } from '@/api/types'
import { VEHICLE_TYPES } from '@/constants/logistics'
import { BID_STATUS, TENDER_STATUS } from '@/constants/procurement'
import { useNotify } from '@/stores/notify'
import { useOrgStore } from '@/stores/org'
import { countdown } from '@/utils/download'
import { formatDateTime, formatMoney, formatNumber, timeAgo } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const orgStore = useOrgStore()
const notify = useNotify()
const queryClient = useQueryClient()
const id = computed(() => route.params.id as string)
const key = computed(() => ['tenders', orgStore.currentId, 'detail', id.value])

const { data: t, isLoading, isError } = useQuery({
  queryKey: key,
  queryFn: async () => (await http.get<TenderDetail>(`/tenders/${id.value}/`)).data,
  refetchInterval: 30_000,
})

const isCarrier = computed(() => orgStore.role === 'carrier')
const canManage = computed(() => orgStore.can('tenders.manage'))
const activeBids = computed(() => (t.value?.bids ?? []).filter((b) => b.status !== 'withdrawn'))
const cheapest = computed(() => Math.min(...activeBids.value.map((b) => Number(b.amount))))
const fastest = computed(() => Math.min(...activeBids.value.map((b) => b.transit_hours)))
const canAward = computed(() => canManage.value && (t.value?.status === 'open' || t.value?.status === 'closed'))
const vehicleLabel = computed(() => VEHICLE_TYPES.find((v) => v.value === t.value?.vehicle_type)?.title ?? t.value?.vehicle_type)

function vsTarget(amount: string) {
  if (!t.value?.target_rate) return null
  return Math.round(((Number(amount) - Number(t.value.target_rate)) / Number(t.value.target_rate)) * 100)
}
function refresh() {
  queryClient.invalidateQueries({ queryKey: ['tenders', orgStore.currentId] })
}

// ---------------- carrier: place / revise / withdraw
const bidForm = reactive({ amount: '', transit_hours: 24, notes: '' })
const bidErrors = ref<Record<string, string>>({})
const bidding = ref(false)
watch(
  t,
  (v) => {
    if (v?.my_bid && !bidForm.amount) Object.assign(bidForm, { amount: v.my_bid.amount, transit_hours: v.my_bid.transit_hours, notes: v.my_bid.notes })
  },
  { immediate: true },
)
async function placeBid() {
  bidding.value = true
  bidErrors.value = {}
  try {
    const { data } = await http.post<Bid>(`/tenders/${id.value}/bid/`, bidForm)
    notify.success(data.revision > 1 ? `Bid revised to ${formatMoney(data.amount, data.currency)}` : 'Bid submitted')
    refresh()
  } catch (e) {
    bidErrors.value = fieldErrors(e)
    if (!Object.keys(bidErrors.value).length) notify.error(errorMessage(e))
  } finally {
    bidding.value = false
  }
}
async function withdraw() {
  try {
    await http.post(`/tenders/${id.value}/withdraw/`)
    notify.success('Bid withdrawn')
    refresh()
  } catch (e) {
    notify.error(errorMessage(e))
  }
}

// ---------------- ops: award / cancel
const awardBid = ref<Bid | null>(null)
const awarding = ref(false)
async function confirmAward() {
  if (!awardBid.value) return
  awarding.value = true
  try {
    const { data } = await http.post<{ trip_id: string }>(`/tenders/${id.value}/award/`, { bid: awardBid.value.id })
    notify.success(`Awarded to ${awardBid.value.carrier_name}. Trip created.`)
    refresh()
    queryClient.invalidateQueries({ queryKey: ['shipments', orgStore.currentId] })
    router.push({ name: 'trip-detail', params: { id: data.trip_id } })
  } catch (e) {
    notify.error(errorMessage(e))
  } finally {
    awarding.value = false
    awardBid.value = null
  }
}
const cancelOpen = ref(false)
const cancelReason = ref('')
async function cancelTender() {
  try {
    await http.post(`/tenders/${id.value}/cancel/`, { reason: cancelReason.value })
    notify.success('Tender cancelled')
    cancelOpen.value = false
    refresh()
  } catch (e) {
    notify.error(errorMessage(e))
  }
}
</script>

<template>
  <div>
    <v-btn variant="text" :prepend-icon="mdiArrowLeft" class="mb-2 ml-n2" :to="{ name: 'tenders' }">{{ isCarrier ? 'Load board' : 'Tenders' }}</v-btn>
    <v-alert v-if="isError" type="error" variant="tonal" text="This tender doesn't exist or you weren't invited to it." />
    <v-skeleton-loader v-else-if="isLoading || !t" type="heading, card, card" class="bg-transparent" />

    <template v-else>
      <div class="d-flex flex-wrap align-center ga-3 mb-5">
        <div class="flex-grow-1">
          <div class="d-flex flex-wrap align-center ga-2">
            <h1 class="text-h5 font-weight-bold">{{ t.reference }}</h1>
            <v-chip :color="TENDER_STATUS[t.status].color" variant="tonal" size="small" :prepend-icon="TENDER_STATUS[t.status].icon">
              {{ TENDER_STATUS[t.status].label }}
            </v-chip>
          </div>
          <div class="text-body-2 text-medium-emphasis mt-1">
            {{ t.shipment.origin.city }}, {{ t.shipment.origin.country }} → {{ t.shipment.destination.city }}, {{ t.shipment.destination.country }}
            <template v-if="t.customer"> · for {{ t.customer }}</template>
          </div>
        </div>
        <v-btn v-if="!isCarrier" variant="tonal" :to="{ name: 'shipment-detail', params: { id: t.shipment.id } }" :append-icon="mdiArrowRight">
          {{ t.shipment.reference }}
        </v-btn>
        <v-btn v-if="t.trip_id" color="primary" :to="{ name: 'trip-detail', params: { id: t.trip_id } }" :prepend-icon="mdiTruckOutline">Open trip</v-btn>
        <v-btn v-if="canAward" variant="text" color="error" :prepend-icon="mdiCancel" @click="cancelOpen = true">Cancel tender</v-btn>
      </div>

      <v-alert v-if="t.status === 'closed' && canManage" type="warning" variant="tonal" class="mb-4" title="Bidding has closed">
        Compare the bids below and award the load before the pickup on {{ formatDateTime(t.pickup_at) }}.
      </v-alert>
      <v-alert v-if="t.status === 'cancelled'" type="error" variant="tonal" class="mb-4" :text="`Cancelled: ${t.cancel_reason}`" />

      <v-row>
        <v-col cols="12" md="5">
          <v-card class="cp-card pa-5 mb-4">
            <div class="cp-section-title mb-3">Load</div>
            <div class="text-h6 font-weight-bold">{{ t.shipment.commodity }}</div>
            <div class="d-flex flex-wrap ga-2 mt-2">
              <v-chip size="small" variant="tonal" :prepend-icon="mdiTruckOutline">{{ vehicleLabel }}</v-chip>
              <v-chip v-if="t.shipment.is_temperature_controlled" size="small" color="info" variant="tonal" :prepend-icon="mdiSnowflake">Temperature controlled</v-chip>
              <v-chip v-if="t.shipment.is_hazardous" size="small" color="error" variant="tonal" :prepend-icon="mdiFire">Dangerous goods</v-chip>
            </div>
            <div class="cp-kv mt-4"><span>Pallets</span><strong>{{ t.shipment.total_packages }}</strong></div>
            <div class="cp-kv"><span>Gross weight</span><strong>{{ formatNumber(t.shipment.gross_weight_kg, 'kg') }}</strong></div>
            <div class="cp-kv"><span>Volume</span><strong>{{ formatNumber(t.shipment.volume_cbm, 'm³') }}</strong></div>
            <v-divider class="my-3" />
            <div class="cp-kv"><span>Pickup</span><strong>{{ formatDateTime(t.pickup_at) }}</strong></div>
            <div class="cp-kv"><span>Deliver by</span><strong>{{ formatDateTime(t.deliver_by) }}</strong></div>
            <div class="cp-kv">
              <span>Bidding {{ t.status === 'open' ? 'closes' : 'closed' }}</span>
              <strong class="d-flex align-center ga-1"><v-icon :icon="mdiClockOutline" size="14" />{{ countdown(t.closes_at) }}</strong>
            </div>
            <div v-if="t.target_rate" class="cp-kv"><span>Target rate (internal)</span><strong>{{ formatMoney(t.target_rate, t.currency) }}</strong></div>
            <template v-if="t.notes">
              <v-divider class="my-3" />
              <div class="text-body-2" style="white-space: pre-line">{{ t.notes }}</div>
            </template>
          </v-card>
        </v-col>

        <v-col cols="12" md="7">
          <!-- Operations: ranked sealed bids -->
          <v-card v-if="t.bids" class="cp-card pa-5">
            <div class="d-flex align-center mb-3">
              <div class="cp-section-title">Bids · {{ activeBids.length }} of {{ t.invited_count }} carriers</div>
            </div>
            <div v-if="!t.bids.length" class="text-body-2 text-medium-emphasis py-6 text-center">No bids yet. Invited: {{ t.invited_carriers?.map((c) => c.name).join(', ') }}.</div>
            <div v-for="(b, i) in t.bids" :key="b.id" class="cp-bid" :class="{ 'is-won': b.status === 'won', 'is-muted': b.status === 'withdrawn' || b.status === 'lost' }">
              <div class="cp-bid__rank">{{ b.status === 'withdrawn' ? '—' : i + 1 }}</div>
              <div class="flex-grow-1" style="min-width: 0">
                <div class="d-flex flex-wrap align-center ga-2">
                  <span class="font-weight-bold">{{ b.carrier_name }}</span>
                  <v-chip v-if="Number(b.amount) === cheapest && b.status !== 'withdrawn'" size="x-small" color="success" variant="tonal" :prepend-icon="mdiTrophyOutline">Cheapest</v-chip>
                  <v-chip v-if="b.transit_hours === fastest && b.status !== 'withdrawn'" size="x-small" color="info" variant="tonal" :prepend-icon="mdiLightningBolt">Fastest</v-chip>
                  <v-chip v-if="b.status !== 'submitted'" size="x-small" :color="BID_STATUS[b.status].color" variant="tonal">{{ BID_STATUS[b.status].label }}</v-chip>
                </div>
                <div class="text-caption text-medium-emphasis">
                  {{ b.transit_hours }} h transit · updated {{ timeAgo(b.updated_at) }}<template v-if="b.revision > 1"> · revision {{ b.revision }}</template>
                  <template v-if="b.notes"> · “{{ b.notes }}”</template>
                </div>
              </div>
              <div class="text-right">
                <div class="font-weight-bold num text-subtitle-1">{{ formatMoney(b.amount, b.currency) }}</div>
                <div v-if="vsTarget(b.amount) !== null" class="text-caption font-weight-bold" :class="vsTarget(b.amount)! <= 0 ? 'text-success' : 'text-error'">
                  {{ vsTarget(b.amount)! > 0 ? '+' : '' }}{{ vsTarget(b.amount) }}% vs target
                </div>
              </div>
              <v-btn v-if="canAward && b.status === 'submitted'" color="primary" variant="flat" size="small" class="ml-2" @click="awardBid = b">Award</v-btn>
            </div>
          </v-card>

          <!-- Carrier: sealed bid form -->
          <v-card v-else-if="isCarrier" class="cp-card pa-5">
            <div class="cp-section-title mb-3">Your bid</div>
            <template v-if="t.status === 'open'">
              <div class="text-body-2 text-medium-emphasis mb-4">Bids are sealed. You can revise until bidding closes {{ countdown(t.closes_at) }}.</div>
              <v-row dense>
                <v-col cols="12" sm="6">
                  <v-text-field v-model="bidForm.amount" type="number" :label="`All-in rate (${t.currency})`" :error-messages="bidErrors.amount" />
                </v-col>
                <v-col cols="12" sm="6">
                  <v-text-field v-model.number="bidForm.transit_hours" type="number" label="Transit time" suffix="hours" :error-messages="bidErrors.transit_hours" />
                </v-col>
                <v-col cols="12"><v-text-field v-model="bidForm.notes" label="Note to the forwarder (optional)" /></v-col>
              </v-row>
              <div class="d-flex flex-wrap ga-2">
                <v-btn color="primary" :loading="bidding" :disabled="!bidForm.amount" @click="placeBid">{{ t.my_bid?.status === 'submitted' ? 'Revise bid' : 'Submit bid' }}</v-btn>
                <v-btn v-if="t.my_bid?.status === 'submitted'" variant="text" color="error" @click="withdraw">Withdraw</v-btn>
              </div>
              <div v-if="t.my_bid" class="text-caption text-medium-emphasis mt-3">
                Current: {{ formatMoney(t.my_bid.amount, t.my_bid.currency) }}, {{ t.my_bid.transit_hours }} h ·
                {{ BID_STATUS[t.my_bid.status].label.toLowerCase() }} {{ timeAgo(t.my_bid.updated_at) }}
              </div>
            </template>
            <template v-else>
              <div v-if="t.my_bid" class="d-flex align-center ga-3">
                <div class="text-h5 font-weight-bold num">{{ formatMoney(t.my_bid.amount, t.my_bid.currency) }}</div>
                <v-chip :color="BID_STATUS[t.my_bid.status].color" variant="tonal">{{ BID_STATUS[t.my_bid.status].label }}</v-chip>
              </div>
              <div v-else class="text-body-2 text-medium-emphasis">You didn't bid on this load.</div>
              <div class="text-body-2 mt-3">
                <template v-if="t.status === 'awarded'">Awarded to <strong>{{ t.awarded_to }}</strong>.</template>
                <template v-else-if="t.status === 'closed'">Bidding closed; the forwarder is reviewing bids.</template>
              </div>
            </template>
          </v-card>
        </v-col>
      </v-row>

      <v-dialog :model-value="!!awardBid" max-width="460" @update:model-value="(v: boolean) => !v && (awardBid = null)">
        <v-card v-if="awardBid" class="cp-card pa-2">
          <v-card-title class="font-weight-bold">Award to {{ awardBid.carrier_name }}?</v-card-title>
          <v-card-text>
            {{ formatMoney(awardBid.amount, awardBid.currency) }} · {{ awardBid.transit_hours }} h transit. Other bidders are notified they weren't selected,
            the carrier is booked on {{ t.shipment.reference }}, and a trip is created for them to dispatch.
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="awardBid = null">Cancel</v-btn>
            <v-btn color="primary" variant="flat" :loading="awarding" @click="confirmAward">Award & create trip</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <v-dialog v-model="cancelOpen" max-width="440">
        <v-card class="cp-card pa-2">
          <v-card-title class="font-weight-bold">Cancel tender</v-card-title>
          <v-card-text><v-textarea v-model="cancelReason" label="Reason" rows="2" auto-grow /></v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="cancelOpen = false">Keep it</v-btn>
            <v-btn color="error" variant="flat" :disabled="!cancelReason.trim()" @click="cancelTender">Cancel tender</v-btn>
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
.cp-bid {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  margin-bottom: 8px;
}
.cp-bid.is-won {
  border-color: rgb(var(--v-theme-success));
  background: rgba(var(--v-theme-success), 0.06);
}
.cp-bid.is-muted {
  opacity: 0.55;
}
.cp-bid__rank {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: 50%;
  font-weight: 700;
  font-size: 0.8rem;
  background: rgba(var(--v-theme-primary), 0.1);
  color: rgb(var(--v-theme-primary));
}
</style>
