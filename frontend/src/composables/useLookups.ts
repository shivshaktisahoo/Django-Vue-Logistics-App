import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed } from 'vue'
import { http } from '@/api/http'
import type { Carrier, Location, Paginated, Party } from '@/api/types'
import { useOrgStore } from '@/stores/org'

const PAGE = { page_size: 200, is_active: true }

/** Cached master data for pickers; scoped server-side (a customer sees only their address book). */
export function useLookups() {
  const org = useOrgStore()
  const queryClient = useQueryClient()
  const key = (name: string) => computed(() => ['lookups', org.currentId, name])

  const parties = useQuery({
    queryKey: key('parties'),
    queryFn: async () => (await http.get<Paginated<Party>>('/masterdata/parties/', { params: PAGE })).data.results,
    staleTime: 5 * 60_000,
  })
  const locations = useQuery({
    queryKey: key('locations'),
    queryFn: async () => (await http.get<Paginated<Location>>('/masterdata/locations/', { params: PAGE })).data.results,
    staleTime: 5 * 60_000,
  })
  const carriers = useQuery({
    queryKey: key('carriers'),
    queryFn: async () => (await http.get<Paginated<Carrier>>('/masterdata/carriers/', { params: PAGE })).data.results,
    staleTime: 5 * 60_000,
    enabled: computed(() => org.role !== 'customer'),
  })

  function invalidate(name: 'parties' | 'locations' | 'carriers') {
    queryClient.invalidateQueries({ queryKey: ['lookups', org.currentId, name] })
  }

  return { parties, locations, carriers, invalidate }
}
