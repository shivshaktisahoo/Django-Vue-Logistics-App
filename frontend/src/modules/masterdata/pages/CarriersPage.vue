<script setup lang="ts">
import { mdiAccountHardHatOutline, mdiTruckOutline, mdiWarehouse } from '@mdi/js'
import { computed, ref } from 'vue'
import type { Carrier, Driver, Vehicle } from '@/api/types'
import EntityCrud, { type Field } from '@/components/crud/EntityCrud.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useLookups } from '@/composables/useLookups'
import { MODE_BY_VALUE, MODES, VEHICLE_TYPES } from '@/constants/logistics'
import { formatNumber } from '@/utils/format'

const tab = ref('carriers')
const { carriers } = useLookups()
const carrierItems = computed(() => (carriers.data.value ?? []).map((c) => ({ value: c.id, title: `${c.name} (${c.code})` })))
const roadCarrierItems = computed(() =>
  (carriers.data.value ?? []).filter((c) => c.mode === 'road').map((c) => ({ value: c.id, title: `${c.name} (${c.code})` })),
)

const carrierFields: Field[] = [
  { key: 'name', label: 'Name', cols: 8 },
  { key: 'code', label: 'Code (SCAC / IATA)', cols: 4, upper: true },
  { key: 'mode', label: 'Mode', type: 'select', items: MODES.map((m) => ({ value: m.value, title: m.label })), cols: 4 },
  { key: 'country', label: 'Country (ISO)', cols: 4, upper: true, maxlength: 2 },
  { key: 'phone', label: 'Phone', cols: 4 },
  { key: 'email', label: 'Bookings email', type: 'email', cols: 12 },
  { key: 'is_active', label: 'Active', type: 'switch', cols: 12 },
]
const vehicleFields = computed<Field[]>(() => [
  { key: 'carrier', label: 'Carrier', type: 'select', items: roadCarrierItems.value, cols: 12 },
  { key: 'plate_number', label: 'Plate number', upper: true },
  { key: 'vehicle_type', label: 'Type', type: 'select', items: VEHICLE_TYPES },
  { key: 'capacity_kg', label: 'Payload (kg)', type: 'number' },
  { key: 'is_active', label: 'Active', type: 'switch' },
])
const driverFields = computed<Field[]>(() => [
  { key: 'carrier', label: 'Carrier', type: 'select', items: carrierItems.value, cols: 12 },
  { key: 'name', label: 'Full name' },
  { key: 'phone', label: 'Mobile' },
  { key: 'license_number', label: 'Licence number' },
  { key: 'is_active', label: 'Active', type: 'switch' },
])
const vehicleType = (v: string) => VEHICLE_TYPES.find((t) => t.value === v)?.title ?? v
</script>

<template>
  <div>
    <PageHeader title="Carriers & fleet" subtitle="Shipping lines, airlines and haulage partners, with their trucks and drivers." :icon="mdiWarehouse" />
    <v-card class="cp-card">
      <v-tabs v-model="tab" color="primary" class="px-2">
        <v-tab value="carriers" class="text-none" :prepend-icon="mdiWarehouse">Carriers</v-tab>
        <v-tab value="vehicles" class="text-none" :prepend-icon="mdiTruckOutline">Vehicles</v-tab>
        <v-tab value="drivers" class="text-none" :prepend-icon="mdiAccountHardHatOutline">Drivers</v-tab>
      </v-tabs>
      <v-divider />
      <v-window v-model="tab">
        <v-window-item value="carriers">
          <EntityCrud
            endpoint="/masterdata/carriers/"
            entity="Carrier"
            :icon="mdiWarehouse"
            :headers="[
              { title: 'Carrier', key: 'name' },
              { title: 'Mode', key: 'mode', sortable: false },
              { title: 'Fleet', key: 'vehicle_count', sortable: false },
              { title: 'Contact', key: 'email', sortable: false },
            ]"
            :fields="carrierFields"
            :defaults="{ mode: 'road', is_active: true, country: 'AE' }"
            lookup="carriers"
            search-placeholder="Name or code…"
          >
            <template #item.name="{ item }">
              <div class="font-weight-medium">{{ (item as Carrier).name }}</div>
              <div class="text-caption text-medium-emphasis mono">{{ (item as Carrier).code }}</div>
            </template>
            <template #item.mode="{ item }">
              <v-chip size="small" variant="tonal" :prepend-icon="MODE_BY_VALUE[(item as Carrier).mode].icon">{{ MODE_BY_VALUE[(item as Carrier).mode].label }}</v-chip>
            </template>
            <template #item.vehicle_count="{ item }">
              <span v-if="(item as Carrier).mode === 'road'">{{ (item as Carrier).vehicle_count }} trucks · {{ (item as Carrier).driver_count }} drivers</span>
              <span v-else class="text-medium-emphasis">—</span>
            </template>
          </EntityCrud>
        </v-window-item>
        <v-window-item value="vehicles">
          <EntityCrud
            endpoint="/masterdata/vehicles/"
            entity="Vehicle"
            :icon="mdiTruckOutline"
            :headers="[
              { title: 'Plate', key: 'plate_number' },
              { title: 'Type', key: 'vehicle_type', sortable: false },
              { title: 'Payload', key: 'capacity_kg' },
              { title: 'Carrier', key: 'carrier_name', sortable: false },
            ]"
            :fields="vehicleFields"
            :defaults="{ vehicle_type: 'tractor_trailer', capacity_kg: 25000, is_active: true }"
            search-placeholder="Plate or carrier…"
          >
            <template #item.plate_number="{ item }"><span class="mono font-weight-bold">{{ (item as Vehicle).plate_number }}</span></template>
            <template #item.vehicle_type="{ item }">{{ vehicleType((item as Vehicle).vehicle_type) }}</template>
            <template #item.capacity_kg="{ item }"><span class="num">{{ formatNumber((item as Vehicle).capacity_kg, 'kg') }}</span></template>
          </EntityCrud>
        </v-window-item>
        <v-window-item value="drivers">
          <EntityCrud
            endpoint="/masterdata/drivers/"
            entity="Driver"
            :icon="mdiAccountHardHatOutline"
            :headers="[
              { title: 'Driver', key: 'name' },
              { title: 'Mobile', key: 'phone', sortable: false },
              { title: 'Licence', key: 'license_number', sortable: false },
              { title: 'Carrier', key: 'carrier_name', sortable: false },
            ]"
            :fields="driverFields"
            :defaults="{ is_active: true }"
            search-placeholder="Name, phone or licence…"
          >
            <template #item.license_number="{ item }"><span class="mono">{{ (item as Driver).license_number }}</span></template>
          </EntityCrud>
        </v-window-item>
      </v-window>
    </v-card>
  </div>
</template>
