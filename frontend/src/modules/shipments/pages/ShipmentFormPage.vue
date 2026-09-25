<script setup lang="ts">
import { mdiAccountPlusOutline, mdiArrowLeft, mdiFire, mdiInformationOutline, mdiScaleBalance, mdiSnowflake } from '@mdi/js'
import { useQueryClient } from '@tanstack/vue-query'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage, fieldErrors, http } from '@/api/http'
import type { Mode, PackageLine, Party, Shipment } from '@/api/types'
import RouteLabel from '@/components/logistics/RouteLabel.vue'
import LoadingOverlay from '@/components/ui/LoadingOverlay.vue'
import { useLookups } from '@/composables/useLookups'
import { INCOTERMS, MODES, SERVICE_TYPES } from '@/constants/logistics'
import { useNotify } from '@/stores/notify'
import { useOrgStore } from '@/stores/org'
import { formatNumber } from '@/utils/format'
import { cargoTotals, defaultDims, KG_PER_CBM } from '@/utils/freight'
import PackageEditor from '../components/PackageEditor.vue'
import QuickPartyDialog from '../components/QuickPartyDialog.vue'

const route = useRoute()
const router = useRouter()
const orgStore = useOrgStore()
const notify = useNotify()
const queryClient = useQueryClient()
const { parties, locations, carriers, invalidate } = useLookups()

const editId = computed(() => (route.params.id as string | undefined) ?? null)
const isCustomer = computed(() => orgStore.role === 'customer')
const canConfirm = computed(() => orgStore.can('shipments.manage'))

const form = reactive({
  mode: 'ocean' as Mode,
  service_type: 'fcl',
  incoterm: 'FOB',
  customer: null as string | null,
  shipper: null as string | null,
  consignee: null as string | null,
  origin: null as string | null,
  destination: null as string | null,
  carrier: null as string | null,
  etd: '',
  eta: '',
  commodity: '',
  hs_code: '',
  declared_value: '',
  currency: orgStore.org?.base_currency ?? 'USD',
  customer_reference: '',
  house_bill: '',
  master_bill: '',
  voyage_number: '',
  is_hazardous: false,
  is_temperature_controlled: false,
  special_instructions: '',
})
const packages = ref<PackageLine[]>([])
const status = ref<string>('draft')
const loading = ref(false)
const saving = ref(false)
const errors = ref<Record<string, string>>({})
const error = ref('')
const partyDialog = ref<{ open: boolean; role: 'shipper' | 'consignee' }>({ open: false, role: 'shipper' })

const locked = computed(() => !!editId.value && !['draft', 'booked'].includes(status.value))
const services = computed(() => SERVICE_TYPES.filter((s) => s.mode === form.mode))
const customers = computed(() => (parties.data.value ?? []).filter((p) => p.is_customer))
const partyItems = computed(() => parties.data.value ?? [])
const carrierItems = computed(() => (carriers.data.value ?? []).filter((c) => c.mode === form.mode))
const locationItems = computed(() => locations.data.value ?? [])
const originLoc = computed(() => locationItems.value.find((l) => l.id === form.origin))
const destLoc = computed(() => locationItems.value.find((l) => l.id === form.destination))
const totals = computed(() => cargoTotals(form.mode, packages.value))
const volumetricWins = computed(() => totals.value.volumetric > totals.value.gross)

watch(
  () => form.mode,
  (mode, prev) => {
    if (!services.value.some((s) => s.value === form.service_type)) form.service_type = services.value[0]!.value
    if (prev && form.carrier && !carrierItems.value.some((c) => c.id === form.carrier)) form.carrier = null
    if (mode !== 'ocean')
      packages.value = packages.value.map((p) =>
        p.kind === 'container' ? { ...p, kind: mode === 'air' ? 'carton' : 'pallet', container_type: '', container_number: '', ...defaultDims(mode) } : p,
      )
  },
)

const toLocal = (iso: string | null) => {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
const toIso = (local: string) => (local ? new Date(local).toISOString() : null)

onMounted(async () => {
  if (!editId.value) {
    packages.value = [editorBlank()]
    return
  }
  loading.value = true
  try {
    const { data: s } = await http.get<Shipment>(`/shipments/${editId.value}/`)
    Object.assign(form, {
      mode: s.mode,
      service_type: s.service_type,
      incoterm: s.incoterm,
      customer: s.customer.id,
      shipper: s.shipper.id,
      consignee: s.consignee.id,
      origin: s.origin.id,
      destination: s.destination.id,
      carrier: s.carrier?.id ?? null,
      etd: toLocal(s.etd),
      eta: toLocal(s.eta),
      commodity: s.commodity,
      hs_code: s.hs_code,
      declared_value: s.declared_value ?? '',
      currency: s.currency,
      customer_reference: s.customer_reference,
      house_bill: s.house_bill,
      master_bill: s.master_bill,
      voyage_number: s.voyage_number,
      is_hazardous: s.is_hazardous,
      is_temperature_controlled: s.is_temperature_controlled,
      special_instructions: s.special_instructions,
    })
    packages.value = s.packages.map((p) => ({ ...p }))
    status.value = s.status
  } catch (e) {
    notify.error(errorMessage(e))
    router.replace({ name: 'shipments' })
  } finally {
    loading.value = false
  }
})

function editorBlank(): PackageLine {
  return {
    kind: 'container',
    container_type: '40HC',
    container_number: '',
    seal_number: '',
    quantity: 1,
    description: '',
    weight_kg: '',
    length_cm: null,
    width_cm: null,
    height_cm: null,
  }
}

function payload(book: boolean) {
  const clean = (v: string | null) => (v === '' ? null : v)
  const body: Record<string, unknown> = {
    ...form,
    etd: toIso(form.etd),
    eta: toIso(form.eta),
    declared_value: clean(form.declared_value),
    book,
  }
  if (isCustomer.value) delete body.customer
  if (locked.value) {
    // Once cargo moves only schedule and references can change.
    return { eta: body.eta, house_bill: form.house_bill, master_bill: form.master_bill, voyage_number: form.voyage_number, special_instructions: form.special_instructions }
  }
  body.packages = packages.value.map((p) => ({
    ...p,
    id: undefined,
    volume_cbm: undefined,
    length_cm: clean(p.length_cm),
    width_cm: clean(p.width_cm),
    height_cm: clean(p.height_cm),
    container_number: p.kind === 'container' ? p.container_number.replace(/\s/g, '') : '',
    container_type: p.kind === 'container' ? p.container_type : '',
  }))
  return body
}

async function submit(book = false) {
  saving.value = true
  errors.value = {}
  error.value = ''
  try {
    const { data } = editId.value
      ? await http.patch<Shipment>(`/shipments/${editId.value}/`, payload(false))
      : await http.post<Shipment>('/shipments/', payload(book))
    queryClient.invalidateQueries({ queryKey: ['shipments', orgStore.currentId] })
    notify.success(
      editId.value ? `${data.reference} updated` : book ? `${data.reference} booked` : isCustomer.value ? `Booking request ${data.reference} sent` : `${data.reference} saved as draft`,
    )
    router.push({ name: 'shipment-detail', params: { id: data.id } })
  } catch (e) {
    errors.value = fieldErrors(e)
    error.value = errorMessage(e)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } finally {
    saving.value = false
  }
}

function openPartyDialog(role: 'shipper' | 'consignee') {
  partyDialog.value = { open: true, role }
}
function onPartyCreated(p: Party) {
  invalidate('parties')
  queryClient.setQueryData<Party[]>(['lookups', orgStore.currentId, 'parties'], (old) => [...(old ?? []), p])
  form[partyDialog.value.role] = p.id
}

const partyTitle = (p: Party) => `${p.name} · ${p.city || p.country}`
const locationTitle = (l: { code: string; name: string }) => `${l.code} · ${l.name}`
</script>

<template>
  <div>
    <div class="d-flex flex-wrap align-center ga-3 mb-6">
      <v-btn :icon="mdiArrowLeft" variant="text" aria-label="Back" @click="router.back()" />
      <div>
        <h1 class="text-h5 font-weight-bold">
          {{ editId ? 'Edit shipment' : isCustomer ? 'Request a booking' : 'New shipment' }}
        </h1>
        <div class="text-body-2 text-medium-emphasis">
          {{ isCustomer ? 'Our operations team confirms your request, usually within a few hours.' : 'Book freight across ocean, air or road.' }}
        </div>
      </div>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" class="mb-4" :text="error" />
    <v-alert v-if="locked" type="info" variant="tonal" class="mb-4" :icon="mdiInformationOutline">
      The cargo has been picked up, so route, parties and cargo are locked. You can still update the ETA and references.
    </v-alert>

    <v-row style="position: relative">
      <LoadingOverlay :active="loading" message="Loading shipment…" />
      <v-col cols="12" lg="8">
        <!-- 1. Service & route -->
        <v-card class="cp-card pa-5 mb-4">
          <div class="cp-section-title mb-4">1 · Service & route</div>
          <v-btn-toggle v-model="form.mode" mandatory class="cp-segmented mb-4" :disabled="locked">
            <v-btn v-for="m in MODES" :key="m.value" :value="m.value" :prepend-icon="m.icon" class="text-none px-5">{{ m.label }}</v-btn>
          </v-btn-toggle>
          <v-row dense>
            <v-col cols="12" md="6">
              <v-select v-model="form.service_type" :items="services" item-title="label" item-value="value" label="Service" :error-messages="errors.service_type" :disabled="locked" />
            </v-col>
            <v-col cols="12" md="6">
              <v-select v-model="form.incoterm" :items="INCOTERMS" label="Incoterm" :disabled="locked" />
            </v-col>
            <v-col cols="12" md="6">
              <v-autocomplete
                v-model="form.origin"
                :items="locationItems"
                :item-title="locationTitle"
                item-value="id"
                label="Origin (port / airport / depot)"
                :loading="locations.isLoading.value"
                :error-messages="errors.origin"
                :disabled="locked"
              />
            </v-col>
            <v-col cols="12" md="6">
              <v-autocomplete
                v-model="form.destination"
                :items="locationItems"
                :item-title="locationTitle"
                item-value="id"
                label="Destination"
                :error-messages="errors.destination"
                :disabled="locked"
              />
            </v-col>
          </v-row>
        </v-card>

        <!-- 2. Parties -->
        <v-card class="cp-card pa-5 mb-4">
          <div class="cp-section-title mb-4">2 · Parties</div>
          <v-row dense>
            <v-col v-if="!isCustomer" cols="12">
              <v-autocomplete
                v-model="form.customer"
                :items="customers"
                :item-title="partyTitle"
                item-value="id"
                label="Billing customer"
                :loading="parties.isLoading.value"
                :error-messages="errors.customer"
                :disabled="locked"
              />
            </v-col>
            <v-col cols="12" md="6">
              <v-autocomplete v-model="form.shipper" :items="partyItems" :item-title="partyTitle" item-value="id" label="Shipper (consignor)" :error-messages="errors.shipper" :disabled="locked">
                <template #append>
                  <v-btn :icon="mdiAccountPlusOutline" variant="text" size="small" :disabled="locked" aria-label="New shipper" @click="openPartyDialog('shipper')" />
                </template>
              </v-autocomplete>
            </v-col>
            <v-col cols="12" md="6">
              <v-autocomplete v-model="form.consignee" :items="partyItems" :item-title="partyTitle" item-value="id" label="Consignee" :error-messages="errors.consignee" :disabled="locked">
                <template #append>
                  <v-btn :icon="mdiAccountPlusOutline" variant="text" size="small" :disabled="locked" aria-label="New consignee" @click="openPartyDialog('consignee')" />
                </template>
              </v-autocomplete>
            </v-col>
          </v-row>
        </v-card>

        <!-- 3. Cargo -->
        <v-card class="cp-card pa-5 mb-4">
          <div class="cp-section-title mb-4">3 · Cargo</div>
          <v-row dense>
            <v-col cols="12" md="8"><v-text-field v-model="form.commodity" label="Commodity" :error-messages="errors.commodity" :disabled="locked" /></v-col>
            <v-col cols="12" md="4"><v-text-field v-model="form.hs_code" label="HS code" placeholder="940360" :disabled="locked" /></v-col>
            <v-col cols="8" md="3"><v-text-field v-model="form.declared_value" label="Declared value" type="number" :disabled="locked" /></v-col>
            <v-col cols="4" md="3"><v-text-field v-model="form.currency" label="Currency" maxlength="3" :disabled="locked" /></v-col>
            <v-col cols="12" md="6" class="d-flex flex-wrap ga-4">
              <v-switch v-model="form.is_hazardous" color="error" :prepend-icon="mdiFire" label="Dangerous goods" hide-details inset :disabled="locked" />
              <v-switch v-model="form.is_temperature_controlled" color="info" :prepend-icon="mdiSnowflake" label="Temp. controlled" hide-details inset :disabled="locked" />
            </v-col>
          </v-row>
          <v-alert v-if="errors.packages" type="error" variant="tonal" density="compact" class="my-3" :text="errors.packages" />
          <v-divider class="my-4" />
          <fieldset :disabled="locked" style="border: 0">
            <PackageEditor v-model="packages" :mode="form.mode" :service-type="form.service_type" />
          </fieldset>
        </v-card>

        <!-- 4. Schedule & references -->
        <v-card class="cp-card pa-5 mb-4">
          <div class="cp-section-title mb-4">4 · Schedule & references</div>
          <v-row dense>
            <v-col v-if="!isCustomer" cols="12">
              <v-autocomplete
                v-model="form.carrier"
                :items="carrierItems"
                :item-title="(c) => `${c.name} (${c.code})`"
                item-value="id"
                label="Carrier"
                clearable
                :error-messages="errors.carrier"
                :disabled="locked"
              />
            </v-col>
            <v-col cols="12" md="6"><v-text-field v-model="form.etd" type="datetime-local" label="Estimated departure (ETD)" :disabled="locked" /></v-col>
            <v-col cols="12" md="6"><v-text-field v-model="form.eta" type="datetime-local" label="Estimated arrival (ETA)" :error-messages="errors.eta" /></v-col>
            <v-col cols="12" md="6"><v-text-field v-model="form.customer_reference" label="Customer ref / PO" :disabled="locked" /></v-col>
            <template v-if="!isCustomer">
              <v-col cols="12" md="6"><v-text-field v-model="form.voyage_number" :label="form.mode === 'air' ? 'Flight' : form.mode === 'ocean' ? 'Vessel / voyage' : 'Trip ref'" /></v-col>
              <v-col cols="12" md="6"><v-text-field v-model="form.house_bill" :label="form.mode === 'air' ? 'HAWB' : form.mode === 'ocean' ? 'House B/L' : 'CMR / consignment note'" /></v-col>
              <v-col cols="12" md="6"><v-text-field v-model="form.master_bill" :label="form.mode === 'air' ? 'MAWB' : 'Master B/L'" :disabled="form.mode === 'road'" /></v-col>
            </template>
            <v-col cols="12"><v-textarea v-model="form.special_instructions" label="Special instructions" rows="2" auto-grow /></v-col>
          </v-row>
        </v-card>
      </v-col>

      <!-- Live summary -->
      <v-col cols="12" lg="4">
        <v-card class="cp-card pa-5 cp-sticky">
          <div class="cp-section-title mb-3">Summary</div>
          <RouteLabel v-if="originLoc && destLoc" :origin="originLoc" :destination="destLoc" :mode="form.mode" class="mb-4" />
          <div v-else class="text-body-2 text-medium-emphasis mb-4">Choose origin and destination.</div>

          <div class="cp-kv"><span>Pieces</span><strong class="num">{{ totals.pieces }}</strong></div>
          <div class="cp-kv"><span>Gross weight</span><strong class="num">{{ formatNumber(totals.gross, 'kg') }}</strong></div>
          <div class="cp-kv"><span>Volume</span><strong class="num">{{ formatNumber(totals.cbm.toFixed(3), 'm³') }}</strong></div>
          <div class="cp-kv"><span>Volumetric weight</span><strong class="num">{{ formatNumber(totals.volumetric, 'kg') }}</strong></div>
          <v-divider class="my-3" />
          <div class="d-flex align-center justify-space-between">
            <div class="d-flex align-center ga-2">
              <v-icon :icon="mdiScaleBalance" color="primary" />
              <span class="font-weight-bold">Chargeable</span>
            </div>
            <span class="text-h6 font-weight-bold num">{{ formatNumber(totals.chargeable, 'kg') }}</span>
          </div>
          <div class="text-caption text-medium-emphasis mt-1">
            {{ volumetricWins ? 'Volumetric' : 'Actual' }} weight applies ·
            {{ form.mode === 'ocean' ? 'W/M, 1 m³ = 1,000 kg' : `1:${Math.round(1_000_000 / KG_PER_CBM[form.mode])} cm³/kg` }}
          </div>

          <div class="d-flex flex-column ga-2 mt-6">
            <template v-if="editId">
              <v-btn color="primary" size="large" :loading="saving" @click="submit(false)">Save changes</v-btn>
            </template>
            <template v-else-if="isCustomer">
              <v-btn color="primary" size="large" :loading="saving" @click="submit(false)">Send booking request</v-btn>
            </template>
            <template v-else>
              <v-btn v-if="canConfirm" color="primary" size="large" :loading="saving" @click="submit(true)">Book shipment</v-btn>
              <v-btn variant="tonal" :disabled="saving" @click="submit(false)">Save as draft</v-btn>
            </template>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <QuickPartyDialog v-model="partyDialog.open" :role="partyDialog.role" @created="onPartyCreated" />
  </div>
</template>

<style scoped>
.cp-kv {
  display: flex;
  justify-content: space-between;
  padding: 5px 0;
  font-size: 0.9rem;
  color: rgba(var(--v-theme-on-surface), 0.72);
}
.cp-kv strong {
  color: rgb(var(--v-theme-on-surface));
}
@media (min-width: 1280px) {
  .cp-sticky {
    position: sticky;
    top: 88px;
  }
}
</style>
