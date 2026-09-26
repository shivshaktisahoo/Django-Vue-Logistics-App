<script setup lang="ts">
import { mdiArrowLeft, mdiCheckCircle, mdiMagnify, mdiPackageVariantClosed } from '@mdi/js'
import { useQuery } from '@tanstack/vue-query'
import axios from 'axios'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { PublicTracking } from '@/api/types'
import StatusChip from '@/components/logistics/StatusChip.vue'
import RouteMap from '@/components/map/RouteMap.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { BRAND } from '@/config/brand'
import { MODE_BY_VALUE } from '@/constants/logistics'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime, timeAgo } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const number = computed(() => ((route.params.number as string | undefined) ?? '').toUpperCase())
const input = ref(number.value)
watch(number, (n) => (input.value = n))

const { data, isLoading, isError, error } = useQuery({
  queryKey: computed(() => ['public-track', number.value]),
  // Plain axios: this page works without a session and never sends one.
  queryFn: async () => (await axios.get<PublicTracking>(`/api/v1/public/track/${encodeURIComponent(number.value)}/`, { timeout: 60_000 })).data,
  enabled: computed(() => number.value.length >= 6),
  retry: false,
})
const notFound = computed(() => isError.value && axios.isAxiosError(error.value) && error.value.response?.status === 404)

function search() {
  const n = input.value.trim().toUpperCase()
  if (n) router.push({ name: 'track', params: { number: n } })
}
</script>

<template>
  <v-main class="cp-track">
    <header class="cp-track__hero">
      <div class="cp-track__glow" />
      <div class="cp-track__inner">
        <div class="d-flex align-center ga-3 mb-8">
          <router-link :to="auth.isAuthenticated ? '/' : '/login'" class="d-flex align-center ga-3 text-white" style="text-decoration: none">
            <img src="/favicon.svg" width="34" height="34" alt="" />
            <span class="text-h6 font-weight-bold">{{ BRAND.name }}</span>
          </router-link>
          <v-spacer />
          <v-btn v-if="auth.isAuthenticated" variant="tonal" color="white" :prepend-icon="mdiArrowLeft" to="/">Back to app</v-btn>
          <v-btn v-else variant="tonal" color="white" to="/login">Sign in</v-btn>
        </div>
        <h1 class="cp-track__title">Track a shipment</h1>
        <p class="text-body-1 mb-6" style="opacity: 0.8">Enter the tracking number from your booking confirmation. No login needed.</p>
        <v-form class="d-flex ga-2 cp-track__search" @submit.prevent="search">
          <v-text-field
            v-model="input"
            placeholder="e.g. CPZ9YW7KH6Z6"
            :prepend-inner-icon="mdiMagnify"
            bg-color="white"
            base-color="white"
            color="primary"
            hide-details
            class="mono"
            aria-label="Tracking number"
          />
          <v-btn type="submit" color="secondary" size="x-large" height="48" class="px-6">Track</v-btn>
        </v-form>
      </div>
    </header>

    <div class="cp-track__body">
      <v-skeleton-loader v-if="isLoading" type="card, list-item-two-line@4" class="bg-transparent" />
      <v-card v-else-if="notFound" class="cp-card">
        <EmptyState
          :icon="mdiPackageVariantClosed"
          title="We couldn't find that shipment"
          :text="`No shipment matches ${number}. Check the number on your booking confirmation.`"
        />
      </v-card>
      <v-alert v-else-if="isError" type="error" variant="tonal" text="Tracking is unavailable right now. Please try again in a minute." />

      <template v-else-if="data">
        <v-card class="cp-card pa-5 pa-md-6 mb-4">
          <div class="d-flex flex-wrap align-center ga-3 mb-4">
            <v-avatar color="primary" variant="tonal" rounded="lg" size="46"><v-icon :icon="MODE_BY_VALUE[data.mode].icon" /></v-avatar>
            <div class="flex-grow-1">
              <div class="text-caption text-medium-emphasis">{{ data.service }} · handled by {{ data.forwarder }}</div>
              <div class="text-h6 font-weight-bold mono">{{ data.tracking_number }}</div>
            </div>
            <StatusChip :status="data.status" size="default" />
          </div>
          <div class="cp-track__route">
            <div>
              <div class="text-caption text-medium-emphasis">From</div>
              <div class="font-weight-bold">{{ data.origin.city || data.origin.name }}, {{ data.origin.country }}</div>
              <div class="text-caption text-medium-emphasis">{{ data.atd ? 'Departed' : 'Planned' }} {{ formatDateTime(data.atd ?? data.etd) }}</div>
            </div>
            <div class="cp-track__bar">
              <v-progress-linear :model-value="(data.position?.progress ?? (data.status === 'delivered' ? 1 : 0)) * 100" color="secondary" height="6" rounded />
              <div class="text-caption text-medium-emphasis text-center mt-1">{{ data.distance_km.toLocaleString() }} km</div>
            </div>
            <div class="text-right">
              <div class="text-caption text-medium-emphasis">To</div>
              <div class="font-weight-bold">{{ data.destination.city || data.destination.name }}, {{ data.destination.country }}</div>
              <div class="text-caption" :class="data.eta_health === 'late' ? 'text-error font-weight-bold' : 'text-medium-emphasis'">
                {{ data.ata ? 'Delivered' : 'Estimated' }} {{ formatDateTime(data.ata ?? data.eta) }}
              </div>
            </div>
          </div>
        </v-card>

        <v-row>
          <v-col cols="12" md="7">
            <v-card class="cp-card overflow-hidden">
              <RouteMap
                :route="data.route"
                :position="data.position"
                :origin="data.origin"
                :destination="data.destination"
                :mode="data.mode"
                :health="data.eta_health"
                height="420px"
              />
            </v-card>
          </v-col>
          <v-col cols="12" md="5">
            <v-card class="cp-card pa-5">
              <div class="cp-section-title mb-4">Journey updates</div>
              <v-timeline side="end" align="start" density="compact" truncate-line="both">
                <v-timeline-item
                  v-for="(e, i) in data.events"
                  :key="`${e.code}-${e.occurred_at}`"
                  :dot-color="i === 0 ? 'secondary' : 'grey-lighten-1'"
                  :icon="i === 0 ? undefined : mdiCheckCircle"
                  size="x-small"
                >
                  <div class="font-weight-bold text-body-2">{{ e.label }}</div>
                  <div v-if="e.description && e.description !== e.label" class="text-body-2">{{ e.description }}</div>
                  <div class="text-caption text-medium-emphasis">
                    {{ formatDateTime(e.occurred_at) }} ({{ timeAgo(e.occurred_at) }})<template v-if="e.location"> · {{ e.location }}</template>
                  </div>
                </v-timeline-item>
              </v-timeline>
            </v-card>
          </v-col>
        </v-row>
      </template>

      <div class="text-caption text-medium-emphasis text-center mt-8">
        Positions between milestones are estimated from the schedule. Powered by {{ BRAND.name }}.
      </div>
    </div>
  </v-main>
</template>

<style scoped>
.cp-track__hero {
  position: relative;
  overflow: hidden;
  color: #fff;
  background: var(--cp-sidebar-gradient);
  padding: 24px 20px 72px;
}
.cp-track__glow {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(520px circle at 90% 0%, rgba(20, 184, 166, 0.4), transparent 60%),
    radial-gradient(420px circle at 0% 100%, rgba(29, 78, 216, 0.5), transparent 60%);
}
.cp-track__inner,
.cp-track__body {
  position: relative;
  max-width: 1080px;
  margin: 0 auto;
}
.cp-track__body {
  margin-top: -44px;
  padding: 0 20px 48px;
}
.cp-track__title {
  font-size: clamp(1.8rem, 4vw, 2.6rem);
  font-weight: 800;
  letter-spacing: -0.03em;
}
.cp-track__search {
  max-width: 560px;
}
.cp-track__route {
  display: grid;
  grid-template-columns: 1fr minmax(80px, 1.2fr) 1fr;
  gap: 16px;
  align-items: center;
}
@media (max-width: 600px) {
  .cp-track__route {
    grid-template-columns: 1fr 1fr;
  }
  .cp-track__bar {
    grid-column: 1 / -1;
    order: 3;
  }
}
</style>
