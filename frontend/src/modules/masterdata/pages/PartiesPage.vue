<script setup lang="ts">
import { mdiAccountGroupOutline } from '@mdi/js'
import type { Party } from '@/api/types'
import EntityCrud, { type Field } from '@/components/crud/EntityCrud.vue'
import NameAvatar from '@/components/ui/NameAvatar.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const headers = [
  { title: 'Company', key: 'name' },
  { title: 'Roles', key: 'roles', sortable: false },
  { title: 'Location', key: 'city', sortable: false },
  { title: 'Contact', key: 'contact_name', sortable: false },
]

const fields: Field[] = [
  { key: 'name', label: 'Company name', cols: 8 },
  { key: 'code', label: 'Account code', cols: 4, upper: true },
  { key: 'is_customer', label: 'Customer (billing account)', type: 'switch', cols: 4 },
  { key: 'is_shipper', label: 'Shipper', type: 'switch', cols: 4 },
  { key: 'is_consignee', label: 'Consignee', type: 'switch', cols: 4 },
  { key: 'contact_name', label: 'Contact person' },
  { key: 'email', label: 'Email', type: 'email' },
  { key: 'phone', label: 'Phone' },
  { key: 'tax_id', label: 'Tax ID (VAT / TRN / GSTIN)' },
  { key: 'address', label: 'Address', type: 'textarea', cols: 12 },
  { key: 'city', label: 'City', cols: 8 },
  { key: 'country', label: 'Country (ISO)', cols: 4, upper: true, maxlength: 2 },
  { key: 'is_active', label: 'Active', type: 'switch', cols: 12 },
]

const defaults = { is_customer: false, is_shipper: true, is_consignee: false, is_active: true, country: '' }
</script>

<template>
  <div>
    <PageHeader title="Parties" subtitle="Customers, shippers and consignees you move freight for." :icon="mdiAccountGroupOutline" />
    <v-card class="cp-card">
      <EntityCrud
        endpoint="/masterdata/parties/"
        entity="Party"
        :icon="mdiAccountGroupOutline"
        :headers="headers"
        :fields="fields"
        :defaults="defaults"
        lookup="parties"
        search-placeholder="Name, code, city, contact…"
      >
        <template #item.name="{ item }">
          <div class="d-flex align-center ga-3 py-2">
            <NameAvatar :name="(item as Party).name" :size="34" />
            <div>
              <div class="font-weight-medium">{{ (item as Party).name }}</div>
              <div class="text-caption text-medium-emphasis mono">{{ (item as Party).code }}</div>
            </div>
          </div>
        </template>
        <template #item.roles="{ item }">
          <div class="d-flex flex-wrap ga-1">
            <v-chip v-if="(item as Party).is_customer" size="x-small" color="primary" variant="tonal">Customer</v-chip>
            <v-chip v-if="(item as Party).is_shipper" size="x-small" variant="tonal">Shipper</v-chip>
            <v-chip v-if="(item as Party).is_consignee" size="x-small" variant="tonal">Consignee</v-chip>
            <v-chip v-if="(item as Party).owner" size="x-small" color="secondary" variant="tonal">Customer address book</v-chip>
            <v-chip v-if="!(item as Party).is_active" size="x-small" color="error" variant="tonal">Inactive</v-chip>
          </div>
        </template>
        <template #item.city="{ item }">{{ (item as Party).city }} {{ (item as Party).country }}</template>
        <template #item.contact_name="{ item }">
          <div>{{ (item as Party).contact_name || '—' }}</div>
          <div class="text-caption text-medium-emphasis">{{ (item as Party).email }}</div>
        </template>
      </EntityCrud>
    </v-card>
  </div>
</template>
