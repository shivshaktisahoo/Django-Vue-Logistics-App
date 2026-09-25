<script setup lang="ts">
import type { Organization } from '@/api/types'

defineProps<{ errors: Record<string, string>; readonly?: boolean }>()
const model = defineModel<Partial<Organization>>({ required: true })

const CURRENCIES = ['USD', 'EUR', 'AED', 'INR', 'SAR', 'OMR', 'GBP', 'SGD', 'CNY']
const TIMEZONES = ['Asia/Dubai', 'Asia/Kolkata', 'Asia/Muscat', 'Asia/Riyadh', 'Europe/Rotterdam', 'Europe/London', 'Asia/Singapore', 'Asia/Shanghai', 'America/New_York', 'UTC']
</script>

<template>
  <v-row dense>
    <v-col cols="12" md="6">
      <v-text-field v-model="model.name" label="Trading name" :error-messages="errors.name" :readonly="readonly" />
    </v-col>
    <v-col cols="12" md="6">
      <v-text-field v-model="model.legal_name" label="Legal name" :error-messages="errors.legal_name" :readonly="readonly" />
    </v-col>
    <v-col cols="12" md="4">
      <v-text-field
        v-model="model.country"
        label="Country (ISO code)"
        maxlength="2"
        :error-messages="errors.country"
        :readonly="readonly"
        @update:model-value="(v: string) => (model.country = v.toUpperCase())"
      />
    </v-col>
    <v-col cols="12" md="4">
      <v-select v-model="model.base_currency" :items="CURRENCIES" label="Base currency" :error-messages="errors.base_currency" :readonly="readonly" />
    </v-col>
    <v-col cols="12" md="4">
      <v-autocomplete v-model="model.timezone" :items="TIMEZONES" label="Time zone" :error-messages="errors.timezone" :readonly="readonly" />
    </v-col>
    <v-col cols="12" md="6">
      <v-text-field v-model="model.email" label="Ops email" type="email" :error-messages="errors.email" :readonly="readonly" />
    </v-col>
    <v-col cols="12" md="6">
      <v-text-field v-model="model.phone" label="Phone" :error-messages="errors.phone" :readonly="readonly" />
    </v-col>
    <v-col cols="12">
      <v-textarea v-model="model.address" label="Address" :error-messages="errors.address" :readonly="readonly" />
    </v-col>
  </v-row>
</template>
