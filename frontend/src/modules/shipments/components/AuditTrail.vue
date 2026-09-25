<script setup lang="ts">
import { mdiHistory } from '@mdi/js'
import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import { http } from '@/api/http'
import type { AuditEntry, CursorPage } from '@/api/types'
import EmptyState from '@/components/ui/EmptyState.vue'
import NameAvatar from '@/components/ui/NameAvatar.vue'
import { useOrgStore } from '@/stores/org'
import { formatDateTime } from '@/utils/format'

const props = defineProps<{ entityId: string }>()
const orgStore = useOrgStore()

const { data, isLoading } = useQuery({
  queryKey: computed(() => ['shipment', orgStore.currentId, props.entityId, 'audit']),
  queryFn: async () => (await http.get<CursorPage<AuditEntry>>('/audit/', { params: { entity_id: props.entityId } })).data.results,
})

function show(v: unknown) {
  if (v === null || v === '' || v === undefined) return '∅'
  return String(v).length > 40 ? `${String(v).slice(0, 40)}…` : String(v)
}
</script>

<template>
  <div>
    <div class="cp-section-title mb-4">Audit trail</div>
    <v-skeleton-loader v-if="isLoading" type="list-item-avatar-two-line@3" class="bg-transparent" />
    <EmptyState v-else-if="!data?.length" :icon="mdiHistory" title="No changes recorded" />
    <div v-for="a in data" :key="a.id" class="d-flex ga-3 py-3 cp-audit">
      <NameAvatar :name="a.actor_name" :size="32" />
      <div style="min-width: 0">
        <div class="text-body-2"><strong>{{ a.actor_name }}</strong> · {{ a.summary }}</div>
        <div v-for="(pair, field) in a.changes" :key="field" class="text-caption text-medium-emphasis mono">
          {{ field }}: {{ show(pair[0]) }} → {{ show(pair[1]) }}
        </div>
        <div class="text-caption text-medium-emphasis">{{ formatDateTime(a.created_at) }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cp-audit + .cp-audit {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
