<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage, fieldErrors, http } from '@/api/http'
import type { Carrier, Paginated, ShipmentListItem, TenderDetail } from '@/api/types'
import { VEHICLE_TYPES } from '@/constants/logistics'
import { useNotify } from '@/stores/notify'
import { useOrgStore } from '@/stores/org'

/** Spot RFQ for a road load. Optionally pre-filled from a shipment page. */
const props = defineProps<{ shipmentId?: string | null }>()
const open = defineModel<boolean>({ required: true })
const orgStore = useOrgStore()
const notify = useNotify()
const router = useRouter()

const local = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60_000).toISOString().slice(0, 16)
const hoursFromNow = (h: number) => local(new Date(Date.now() + h * 3_600_000))

const form = reactive({
  shipment: null as string | null,
  carriers: [] as string[],
  vehicle_type: 'tractor_trailer',
  closes_at: hoursFromNow(6),
  pickup_at: hoursFromNow(24),
  deliver_by: hoursFromNow(72),
  target_rate: '',
  notes: '',
})
const errors = ref<Record<string, string>>({})
const error = ref('')
const saving = ref(false)

const { data: shipments, isLoading } = useQuery({
  queryKey: computed(() => ['shipments', orgStore.currentId, 'tenderable']),
  queryFn: async () =>
    (await http.get<Paginated<ShipmentListItem>>('/shipments/', { params: { mode: 'road', status: 'draft,booked', page_size: 100 } })).data.results,
  enabled: open,
})
const { data: carriers } = useQuery({
  queryKey: computed(() => ['lookups', orgStore.currentId, 'road-carriers']),
  queryFn: async () => (await http.get<Paginated<Carrier>>('/masterdata/carriers/', { params: { mode: 'road', is_active: true } })).data.results,
  enabled: open,
})

watch(open, (v) => {
  if (!v) return
  errors.value = {}
  error.value = ''
  form.shipment = props.shipmentId ?? null
})
watch(carriers, (list) => {
  if (list && !form.carriers.length) form.carriers = list.map((c) => c.id) // invite everyone by default
})
watch(
  () => form.shipment,
  (id) => {
    const s = shipments.value?.find((x) => x.id === id)
    if (s?.is_temperature_controlled) form.vehicle_type = 'reefer'
  },
)

async function submit() {
  saving.value = true
  errors.value = {}
  error.value = ''
  try {
    const iso = (v: string) => new Date(v).toISOString()
    const { data } = await http.post<TenderDetail>('/tenders/', {
      ...form,
      closes_at: iso(form.closes_at),
      pickup_at: iso(form.pickup_at),
      deliver_by: iso(form.deliver_by),
      target_rate: form.target_rate || null,
    })
    notify.success(`${data.reference} sent to ${data.invited_count} carrier(s)`)
    open.value = false
    router.push({ name: 'tender-detail', params: { id: data.id } })
  } catch (e) {
    errors.value = fieldErrors(e)
    error.value = Object.keys(errors.value).length ? '' : errorMessage(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <v-dialog v-model="open" max-width="640" scrollable>
    <v-card class="cp-card pa-2">
      <v-card-title class="font-weight-bold">New spot tender</v-card-title>
      <v-card-text>
        <div class="text-body-2 text-medium-emphasis mb-4">Invited carriers bid blind; you'll see every bid ranked against your target.</div>
        <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mb-3" :text="error" />
        <v-row dense>
          <v-col cols="12">
            <v-autocomplete
              v-model="form.shipment"
              :items="shipments ?? []"
              :loading="isLoading"
              :item-title="(s: ShipmentListItem) => `${s.reference} · ${s.origin.code} → ${s.destination.code} · ${s.commodity}`"
              item-value="id"
              label="Road shipment"
              :error-messages="errors.shipment"
              no-data-text="No draft or booked road shipments"
            />
          </v-col>
          <v-col cols="12">
            <v-select
              v-model="form.carriers"
              :items="carriers ?? []"
              :item-title="(c: Carrier) => `${c.name} (${c.code})`"
              item-value="id"
              label="Invite carriers"
              multiple
              chips
              closable-chips
              :error-messages="errors.carriers"
            />
          </v-col>
          <v-col cols="12" sm="6"><v-select v-model="form.vehicle_type" :items="VEHICLE_TYPES" label="Equipment" /></v-col>
          <v-col cols="12" sm="6">
            <v-text-field
              v-model="form.target_rate"
              type="number"
              :label="`Target rate (${orgStore.org?.base_currency})`"
              hint="Internal only, never shown to carriers"
              persistent-hint
            />
          </v-col>
          <v-col cols="12" sm="4"><v-text-field v-model="form.closes_at" type="datetime-local" label="Bidding closes" :error-messages="errors.closes_at" /></v-col>
          <v-col cols="12" sm="4"><v-text-field v-model="form.pickup_at" type="datetime-local" label="Pickup" :error-messages="errors.pickup_at" /></v-col>
          <v-col cols="12" sm="4"><v-text-field v-model="form.deliver_by" type="datetime-local" label="Deliver by" :error-messages="errors.deliver_by" /></v-col>
          <v-col cols="12">
            <v-textarea v-model="form.notes" label="Notes for carriers" rows="2" auto-grow placeholder="Access, equipment or document requirements" />
          </v-col>
        </v-row>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="open = false">Cancel</v-btn>
        <v-btn color="primary" variant="flat" :loading="saving" :disabled="!form.shipment || !form.carriers.length" @click="submit">Send tender</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
