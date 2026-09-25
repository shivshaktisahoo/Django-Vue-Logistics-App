<script setup lang="ts">
import { mdiMapMarkerRadiusOutline } from '@mdi/js'
import type { Location } from '@/api/types'
import EntityCrud, { type Field } from '@/components/crud/EntityCrud.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { LOCATION_KINDS } from '@/constants/logistics'

const headers = [
  { title: 'Code', key: 'code' },
  { title: 'Name', key: 'name' },
  { title: 'Type', key: 'kind', sortable: false },
  { title: 'Country', key: 'country', sortable: false },
  { title: 'Coordinates', key: 'latitude', sortable: false },
]

const fields: Field[] = [
  { key: 'code', label: 'Code (UN/LOCODE)', cols: 4, upper: true, hint: 'e.g. AEJEA, CNSHA, NLRTM' },
  { key: 'name', label: 'Name', cols: 8 },
  { key: 'kind', label: 'Type', type: 'select', items: LOCATION_KINDS, cols: 4 },
  { key: 'city', label: 'City', cols: 5 },
  { key: 'country', label: 'Country (ISO)', cols: 3, upper: true, maxlength: 2 },
  { key: 'latitude', label: 'Latitude', type: 'number', cols: 4 },
  { key: 'longitude', label: 'Longitude', type: 'number', cols: 4 },
  { key: 'timezone', label: 'Time zone', cols: 4, hint: 'IANA, e.g. Asia/Dubai' },
  { key: 'is_active', label: 'Active', type: 'switch', cols: 12 },
]

const defaults = { kind: 'seaport', timezone: 'UTC', is_active: true }
const kindTitle = (k: string) => LOCATION_KINDS.find((x) => x.value === k)?.title ?? k
</script>

<template>
  <div>
    <PageHeader title="Locations" subtitle="Ports, airports, depots and warehouses on your network." :icon="mdiMapMarkerRadiusOutline" />
    <v-card class="cp-card">
      <EntityCrud
        endpoint="/masterdata/locations/"
        entity="Location"
        :icon="mdiMapMarkerRadiusOutline"
        :headers="headers"
        :fields="fields"
        :defaults="defaults"
        lookup="locations"
        search-placeholder="Code, name or city…"
      >
        <template #item.code="{ item }"><span class="mono font-weight-bold">{{ (item as Location).code }}</span></template>
        <template #item.name="{ item }">
          <div class="font-weight-medium">{{ (item as Location).name }}</div>
          <div class="text-caption text-medium-emphasis">{{ (item as Location).city }}</div>
        </template>
        <template #item.kind="{ item }"><v-chip size="small" variant="tonal">{{ kindTitle((item as Location).kind) }}</v-chip></template>
        <template #item.latitude="{ item }">
          <span class="mono text-medium-emphasis">{{ Number((item as Location).latitude).toFixed(3) }}, {{ Number((item as Location).longitude).toFixed(3) }}</span>
        </template>
      </EntityCrud>
    </v-card>
  </div>
</template>
