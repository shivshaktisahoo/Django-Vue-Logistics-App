<script setup lang="ts" generic="T extends { id: string; is_active?: boolean }">
/**
 * Config-driven list + create/edit dialog for master data. Each page describes its
 * columns and form fields; this component handles paging, search, validation errors,
 * cache invalidation and permissions.
 */
import { mdiDeleteOutline, mdiMagnify, mdiPencilOutline, mdiPlus } from '@mdi/js'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, ref, watch } from 'vue'
import { errorMessage, fieldErrors, http } from '@/api/http'
import type { Paginated } from '@/api/types'
import EmptyState from '@/components/ui/EmptyState.vue'
import { useDebounced } from '@/composables/useDebounced'
import { useNotify } from '@/stores/notify'
import { useOrgStore } from '@/stores/org'

export interface Field {
  key: string
  label: string
  type?: 'text' | 'number' | 'select' | 'switch' | 'textarea' | 'email'
  items?: { value: unknown; title: string }[]
  cols?: number
  upper?: boolean
  maxlength?: number
  hint?: string
}

const props = withDefaults(
  defineProps<{
    endpoint: string
    entity: string
    headers: { title: string; key: string; sortable?: boolean; align?: 'start' | 'end' | 'center' }[]
    fields: Field[]
    defaults: Record<string, unknown>
    icon: string
    searchPlaceholder?: string
    lookup?: 'parties' | 'locations' | 'carriers'
    managePermission?: string
    params?: Record<string, unknown>
  }>(),
  { searchPlaceholder: 'Search…', lookup: undefined, managePermission: 'masterdata.manage', params: () => ({}) },
)

const orgStore = useOrgStore()
const notify = useNotify()
const queryClient = useQueryClient()
const canManage = computed(() => orgStore.can(props.managePermission))

const search = ref('')
const debounced = useDebounced(search, 300)
const page = ref(1)
const pageSize = ref(25)
watch(debounced, () => (page.value = 1))

const queryParams = computed(() => ({ ...props.params, search: debounced.value || undefined, page: page.value, page_size: pageSize.value }))
const baseKey = computed(() => ['masterdata', orgStore.currentId, props.endpoint])
const { data, isFetching } = useQuery({
  queryKey: computed(() => [...baseKey.value, queryParams.value]),
  queryFn: async () => (await http.get<Paginated<T>>(props.endpoint, { params: queryParams.value })).data,
  placeholderData: keepPreviousData,
})

const allHeaders = computed(() => (canManage.value ? [...props.headers, { title: '', key: '_actions', sortable: false, align: 'end' as const }] : props.headers))

// ---- dialog
const open = ref(false)
const editing = ref<T | null>(null)
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- heterogeneous form fields
const form = ref<Record<string, any>>({})
const errors = ref<Record<string, string>>({})
const error = ref('')
const saving = ref(false)

function startCreate() {
  editing.value = null
  form.value = { ...props.defaults }
  errors.value = {}
  error.value = ''
  open.value = true
}
function onRow(_: unknown, row: { item: T }) {
  if (canManage.value) startEdit(row.item)
}
function startEdit(item: T) {
  editing.value = item
  form.value = { ...(item as Record<string, unknown>) }
  errors.value = {}
  error.value = ''
  open.value = true
}

function invalidate() {
  queryClient.invalidateQueries({ queryKey: baseKey.value })
  if (props.lookup) queryClient.invalidateQueries({ queryKey: ['lookups', orgStore.currentId, props.lookup] })
}

async function save() {
  saving.value = true
  errors.value = {}
  error.value = ''
  const body = Object.fromEntries(props.fields.map((f) => [f.key, form.value[f.key]]))
  try {
    if (editing.value) await http.patch(`${props.endpoint}${editing.value.id}/`, body)
    else await http.post(props.endpoint, body)
    invalidate()
    notify.success(`${props.entity} ${editing.value ? 'updated' : 'added'}`)
    open.value = false
  } catch (e) {
    errors.value = fieldErrors(e)
    error.value = Object.keys(errors.value).length ? '' : errorMessage(e)
  } finally {
    saving.value = false
  }
}

async function remove(item: T) {
  try {
    await http.delete(`${props.endpoint}${item.id}/`)
    invalidate()
    notify.success(`${props.entity} deleted`)
  } catch (e) {
    notify.error(errorMessage(e))
  }
}
</script>

<template>
  <div>
    <div class="d-flex flex-wrap align-center ga-3 pa-4">
      <v-text-field
        v-model="search"
        :prepend-inner-icon="mdiMagnify"
        :placeholder="searchPlaceholder"
        density="compact"
        hide-details
        clearable
        style="min-width: 240px; max-width: 420px"
      />
      <v-spacer />
      <v-btn v-if="canManage" color="primary" :prepend-icon="mdiPlus" @click="startCreate">Add {{ entity.toLowerCase() }}</v-btn>
    </div>
    <v-data-table-server
      v-model:page="page"
      v-model:items-per-page="pageSize"
      :headers="allHeaders"
      :items="data?.results ?? []"
      :items-length="data?.count ?? 0"
      :loading="isFetching"
      class="cp-table"
      hover
      @click:row="onRow"
    >
      <template v-for="h in headers" #[`item.${h.key}`]="{ item }" :key="h.key">
        <slot :name="`item.${h.key}`" :item="item">{{ (item as Record<string, unknown>)[h.key] }}</slot>
      </template>
      <template #[`item._actions`]="{ item }">
        <v-btn :icon="mdiPencilOutline" size="small" variant="text" :aria-label="`Edit ${entity}`" @click.stop="startEdit(item)" />
        <v-btn :icon="mdiDeleteOutline" size="small" variant="text" color="error" :aria-label="`Delete ${entity}`" @click.stop="remove(item)" />
      </template>
      <template #no-data>
        <EmptyState :icon="icon" :title="`No ${entity.toLowerCase()} found`" :text="search ? 'Try a different search.' : undefined" />
      </template>
    </v-data-table-server>

    <v-dialog v-model="open" max-width="640" scrollable>
      <v-card class="cp-card pa-2">
        <v-card-title class="font-weight-bold">{{ editing ? 'Edit' : 'New' }} {{ entity.toLowerCase() }}</v-card-title>
        <v-card-text>
          <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mb-3" :text="error" />
          <v-row dense>
            <v-col v-for="f in fields" :key="f.key" cols="12" :sm="f.cols ?? 6">
              <v-switch v-if="f.type === 'switch'" v-model="form[f.key]" :label="f.label" color="primary" inset hide-details />
              <v-select v-else-if="f.type === 'select'" v-model="form[f.key]" :items="f.items" :label="f.label" :error-messages="errors[f.key]" />
              <v-textarea v-else-if="f.type === 'textarea'" v-model="form[f.key]" :label="f.label" rows="2" auto-grow :error-messages="errors[f.key]" />
              <v-text-field
                v-else
                v-model="form[f.key]"
                :label="f.label"
                :type="f.type === 'number' ? 'number' : f.type === 'email' ? 'email' : 'text'"
                :maxlength="f.maxlength"
                :hint="f.hint"
                :error-messages="errors[f.key]"
                @update:model-value="(v: string) => f.upper && (form[f.key] = v?.toUpperCase())"
              />
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="open = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" :loading="saving" @click="save">{{ editing ? 'Save' : 'Add' }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
