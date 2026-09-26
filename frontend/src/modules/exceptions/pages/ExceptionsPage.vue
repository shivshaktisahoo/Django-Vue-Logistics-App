<script setup lang="ts">
import { mdiAccountCheckOutline, mdiAlertDecagramOutline, mdiAlertOctagonOutline, mdiBellAlertOutline, mdiRadar, mdiShieldCheckOutline } from '@mdi/js'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref } from 'vue'
import { errorMessage, http } from '@/api/http'
import type { ExceptionSeverity, ExceptionSummary, Paginated, ShipmentExceptionItem } from '@/api/types'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatCard from '@/components/ui/StatCard.vue'
import { SEVERITY } from '@/constants/exceptions'
import { useNotify } from '@/stores/notify'
import { useOrgStore } from '@/stores/org'
import ExceptionCard from '../components/ExceptionCard.vue'

const orgStore = useOrgStore()
const notify = useNotify()
const queryClient = useQueryClient()
const canManage = computed(() => orgStore.can('exceptions.manage'))

type Tab = 'open,acknowledged' | 'open' | 'acknowledged' | 'resolved'
const tab = ref<Tab>('open,acknowledged')
const severities = ref<ExceptionSeverity[]>([])
const mine = ref(false)
const page = ref(1)

const params = computed(() => ({
  status: tab.value,
  severity: severities.value.length ? severities.value.join(',') : undefined,
  mine: mine.value || undefined,
  page: page.value,
  ordering: tab.value === 'resolved' ? '-detected_at' : undefined,
}))
const baseKey = computed(() => ['exceptions', orgStore.currentId])

const { data, isFetching } = useQuery({
  queryKey: computed(() => [...baseKey.value, params.value]),
  queryFn: async () => (await http.get<Paginated<ShipmentExceptionItem>>('/exceptions/', { params: params.value })).data,
  placeholderData: keepPreviousData,
})
const { data: summary } = useQuery({
  queryKey: computed(() => [...baseKey.value, 'summary']),
  queryFn: async () => (await http.get<ExceptionSummary>('/exceptions/summary/')).data,
})

// Unresolved first by severity, then newest.
const RANK: Record<ExceptionSeverity, number> = { critical: 0, high: 1, medium: 2, low: 3 }
const items = computed(() =>
  [...(data.value?.results ?? [])].sort((a, b) =>
    tab.value === 'resolved' ? 0 : RANK[a.severity] - RANK[b.severity] || b.detected_at.localeCompare(a.detected_at),
  ),
)
const pages = computed(() => Math.max(1, Math.ceil((data.value?.count ?? 0) / 25)))

function onChanged() {
  queryClient.invalidateQueries({ queryKey: baseKey.value })
}

const scanning = ref(false)
async function scan() {
  scanning.value = true
  try {
    const { data: r } = await http.post<{ scanned: number; opened: number; escalated: number; resolved: number }>('/exceptions/scan/')
    notify.success(`Checked ${r.scanned} shipments · ${r.opened} new, ${r.escalated} escalated, ${r.resolved} cleared`)
    onChanged()
  } catch (e) {
    notify.error(errorMessage(e))
  } finally {
    scanning.value = false
  }
}
</script>

<template>
  <div>
    <PageHeader
      title="Exceptions"
      subtitle="Shipments that need attention: raised and cleared automatically by the rule engine, worked by your team."
      :icon="mdiBellAlertOutline"
    >
      <template #actions>
        <v-btn v-if="canManage" variant="tonal" :prepend-icon="mdiRadar" :loading="scanning" @click="scan">Run check now</v-btn>
      </template>
    </PageHeader>

    <v-row class="mb-2">
      <v-col cols="6" md="3"><StatCard label="Open" :value="summary?.open" :icon="mdiBellAlertOutline" color="warning" :loading="!summary" /></v-col>
      <v-col cols="6" md="3"><StatCard label="Critical" :value="summary?.critical" :icon="mdiAlertOctagonOutline" color="error" :loading="!summary" /></v-col>
      <v-col cols="6" md="3"><StatCard label="High" :value="summary?.high" :icon="mdiAlertDecagramOutline" color="deep-orange" :loading="!summary" /></v-col>
      <v-col cols="6" md="3">
        <StatCard label="Assigned to me" :value="summary?.mine" :icon="mdiAccountCheckOutline" color="primary" :loading="!summary" />
      </v-col>
    </v-row>

    <v-card class="cp-card">
      <div class="px-3 pt-2">
        <v-tabs v-model="tab" color="primary" density="comfortable" @update:model-value="page = 1">
          <v-tab value="open,acknowledged" class="text-none">Unresolved</v-tab>
          <v-tab value="open" class="text-none">New</v-tab>
          <v-tab value="acknowledged" class="text-none">In progress</v-tab>
          <v-tab value="resolved" class="text-none">Resolved</v-tab>
        </v-tabs>
      </div>
      <v-divider />
      <div class="d-flex flex-wrap align-center ga-2 pa-4">
        <v-chip-group v-model="severities" multiple filter @update:model-value="page = 1">
          <v-chip v-for="(meta, key) in SEVERITY" :key="key" :value="key" :color="meta.color" variant="tonal" size="small">{{ meta.label }}</v-chip>
        </v-chip-group>
        <v-spacer />
        <v-switch v-if="canManage" v-model="mine" label="Assigned to me" color="primary" hide-details inset density="compact" @update:model-value="page = 1" />
      </div>
      <v-progress-linear :active="isFetching" indeterminate color="primary" height="2" />
      <div class="d-flex flex-column ga-3 pa-4 pt-0">
        <ExceptionCard v-for="e in items" :key="e.id" :exc="e" :can-manage="canManage" @changed="onChanged" />
        <EmptyState
          v-if="!items.length && !isFetching"
          :icon="mdiShieldCheckOutline"
          :title="tab === 'resolved' ? 'Nothing resolved yet' : 'All clear'"
          :text="tab === 'resolved' ? undefined : 'No shipments need attention right now.'"
        />
      </div>
      <div v-if="pages > 1" class="d-flex justify-center pb-4">
        <v-pagination v-model="page" :length="pages" density="comfortable" rounded />
      </div>
    </v-card>
  </div>
</template>
