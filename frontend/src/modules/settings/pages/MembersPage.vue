<script setup lang="ts">
import { mdiAccountMultipleOutline, mdiAccountPlusOutline, mdiDeleteOutline } from '@mdi/js'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, reactive, ref } from 'vue'
import { errorMessage, fieldErrors, http } from '@/api/http'
import type { Member, Role } from '@/api/types'
import NameAvatar from '@/components/ui/NameAvatar.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { ROLE_BY_VALUE, ROLES } from '@/constants/roles'
import { useNotify } from '@/stores/notify'
import { useOrgStore } from '@/stores/org'
import { formatDate } from '@/utils/format'

const orgStore = useOrgStore()
const notify = useNotify()
const queryClient = useQueryClient()
const canManage = computed(() => orgStore.can('members.manage'))
const key = computed(() => ['members', orgStore.currentId])

const { data: members, isLoading } = useQuery({
  queryKey: key,
  queryFn: async () => (await http.get<Member[]>('/orgs/current/members/')).data,
})

const headers = [
  { title: 'Member', key: 'full_name' },
  { title: 'Role', key: 'role', width: 220 },
  { title: 'Joined', key: 'created_at', width: 140 },
  { title: '', key: 'actions', width: 60, sortable: false },
]

const inviteOpen = ref(false)
const invite = reactive<{ email: string; role: Role }>({ email: '', role: 'ops' })
const inviteErrors = ref<Record<string, string>>({})

const inviteMutation = useMutation({
  mutationFn: async () => (await http.post<Member>('/orgs/current/members/', invite)).data,
  onSuccess: (m) => {
    queryClient.invalidateQueries({ queryKey: key.value })
    notify.success(`${m.email} added as ${ROLE_BY_VALUE[m.role].label}`)
    inviteOpen.value = false
    invite.email = ''
  },
  onError: (e) => {
    inviteErrors.value = fieldErrors(e)
    if (!Object.keys(inviteErrors.value).length) notify.error(errorMessage(e))
  },
})

async function changeRole(member: Member, role: Role) {
  try {
    await http.patch(`/orgs/current/members/${member.id}/`, { role })
    queryClient.invalidateQueries({ queryKey: key.value })
    notify.success('Role updated')
  } catch (e) {
    notify.error(errorMessage(e))
  }
}

async function remove(member: Member) {
  try {
    await http.delete(`/orgs/current/members/${member.id}/`)
    queryClient.invalidateQueries({ queryKey: key.value })
    notify.success(`${member.email} removed`)
  } catch (e) {
    notify.error(errorMessage(e))
  }
}
</script>

<template>
  <div>
    <PageHeader title="Team & roles" subtitle="Who can access this workspace, and what they can do." :icon="mdiAccountMultipleOutline">
      <template #actions>
        <v-btn v-if="canManage" color="primary" :prepend-icon="mdiAccountPlusOutline" @click="inviteOpen = true">Add member</v-btn>
      </template>
    </PageHeader>

    <v-card class="cp-card">
      <v-data-table :headers="headers" :items="members ?? []" :loading="isLoading" class="cp-table" items-per-page="-1" hide-default-footer>
        <template #[`item.full_name`]="{ item }">
          <div class="d-flex align-center ga-3 py-2">
            <NameAvatar :name="item.full_name || item.email" :size="36" />
            <div style="min-width: 0">
              <div class="font-weight-medium text-truncate">{{ item.full_name || '—' }}</div>
              <div class="text-caption text-medium-emphasis text-truncate">{{ item.email }}</div>
            </div>
          </div>
        </template>
        <template #[`item.role`]="{ item }">
          <v-select
            v-if="canManage && item.is_active"
            :model-value="item.role"
            :items="ROLES"
            item-title="label"
            item-value="value"
            density="compact"
            hide-details
            @update:model-value="(r: Role) => changeRole(item, r)"
          />
          <v-chip v-else size="small" :color="ROLE_BY_VALUE[item.role].color" variant="tonal">
            {{ ROLE_BY_VALUE[item.role].label }}
          </v-chip>
        </template>
        <template #[`item.created_at`]="{ item }">
          <span class="text-medium-emphasis">{{ formatDate(item.created_at) }}</span>
          <v-chip v-if="!item.is_active" size="x-small" class="ml-2">Removed</v-chip>
        </template>
        <template #[`item.actions`]="{ item }">
          <v-btn
            v-if="canManage && item.is_active"
            :icon="mdiDeleteOutline"
            variant="text"
            size="small"
            color="error"
            :aria-label="`Remove ${item.email}`"
            @click="remove(item)"
          />
        </template>
      </v-data-table>
    </v-card>

    <v-dialog v-model="inviteOpen" max-width="480">
      <v-card class="cp-card pa-2">
        <v-card-title class="font-weight-bold">Add a member</v-card-title>
        <v-card-text>
          <v-text-field v-model="invite.email" label="Email" type="email" :error-messages="inviteErrors.email" class="mb-2" />
          <v-select v-model="invite.role" :items="ROLES" item-title="label" item-value="value" label="Role" :error-messages="inviteErrors.role">
            <template #item="{ props, item }">
              <v-list-item v-bind="props" :subtitle="item.raw.pitch" :prepend-icon="item.raw.icon" />
            </template>
          </v-select>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="inviteOpen = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" :loading="inviteMutation.isPending.value" :disabled="!invite.email" @click="inviteMutation.mutate()">
            Add member
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
