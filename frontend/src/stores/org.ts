import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { http, setOrgId } from '@/api/http'
import type { MyOrg, Organization } from '@/api/types'
import { storage } from '@/utils/storage'

const STORAGE_KEY = 'cp-org'

/** The active organization (tenant) and the current user's role/permissions in it. */
export const useOrgStore = defineStore('org', () => {
  const memberships = ref<MyOrg[]>([])
  const currentId = ref<string | null>(storage.get(STORAGE_KEY))
  const loaded = ref(false)

  const current = computed(() => memberships.value.find((m) => m.org.id === currentId.value) ?? null)
  const org = computed(() => current.value?.org ?? null)
  const role = computed(() => current.value?.role ?? null)

  function can(permission: string): boolean {
    const perms = current.value?.permissions ?? []
    return perms.includes('*') || perms.includes(permission)
  }

  function select(id: string | null) {
    currentId.value = id
    setOrgId(id)
    storage.set(STORAGE_KEY, id)
  }

  async function load(force = false) {
    if (loaded.value && !force) return
    const { data } = await http.get<MyOrg[]>('/orgs/')
    memberships.value = data
    loaded.value = true
    // Keep the remembered org if still accessible, otherwise pick the first.
    const stillValid = data.some((m) => m.org.id === currentId.value)
    select(stillValid ? currentId.value : (data[0]?.org.id ?? null))
  }

  async function create(payload: Partial<Organization>) {
    const { data } = await http.post<MyOrg>('/orgs/', payload)
    memberships.value = [...memberships.value, data].sort((a, b) => a.org.name.localeCompare(b.org.name))
    select(data.org.id)
    return data
  }

  async function update(payload: Partial<Organization>) {
    const { data } = await http.patch<Organization>('/orgs/current/', payload)
    const m = memberships.value.find((x) => x.org.id === data.id)
    if (m) m.org = data
    return data
  }

  function reset() {
    memberships.value = []
    loaded.value = false
    select(null)
  }

  return { memberships, currentId, current, org, role, loaded, can, select, load, create, update, reset }
})
