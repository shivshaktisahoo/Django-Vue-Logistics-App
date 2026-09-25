<script setup lang="ts">
import { mdiContentCopy, mdiDeleteOutline, mdiPlus } from '@mdi/js'
import type { Mode, PackageLine } from '@/api/types'
import { CONTAINER_TYPES, PACKAGE_KINDS } from '@/constants/logistics'
import { defaultDims, isValidContainerNumber, lineVolume } from '@/utils/freight'

const props = defineProps<{ mode: Mode | null; serviceType: string | null }>()
const lines = defineModel<PackageLine[]>({ required: true })

function blank(): PackageLine {
  const container = props.serviceType === 'fcl'
  return {
    kind: container ? 'container' : props.mode === 'air' ? 'carton' : 'pallet',
    container_type: container ? '40HC' : '',
    container_number: '',
    seal_number: '',
    quantity: 1,
    description: '',
    weight_kg: '',
    ...(container ? { length_cm: null, width_cm: null, height_cm: null } : defaultDims(props.mode)),
  }
}

function onKindChange(p: PackageLine, kind: string) {
  if (kind === 'container') {
    p.quantity = 1
    p.container_type ||= '40HC'
    p.length_cm = p.width_cm = p.height_cm = null
  } else if (!p.length_cm) {
    // Chargeable weight depends on volume, so never leave a piece line dimensionless.
    Object.assign(p, defaultDims(props.mode))
  }
}

function add() {
  lines.value = [...lines.value, blank()]
}
function duplicate(i: number) {
  const copy = { ...lines.value[i]!, id: undefined, container_number: '', seal_number: '' }
  lines.value = [...lines.value.slice(0, i + 1), copy, ...lines.value.slice(i + 1)]
}
function remove(i: number) {
  lines.value = lines.value.filter((_, j) => j !== i)
}

function kinds() {
  return props.mode === 'ocean' ? PACKAGE_KINDS : PACKAGE_KINDS.filter((k) => k.value !== 'container')
}

function containerRule(v: string) {
  return !v || isValidContainerNumber(v) || 'Invalid ISO 6346 number (check digit)'
}

defineExpose({ add })
</script>

<template>
  <div>
    <div v-for="(p, i) in lines" :key="i" class="cp-line mb-3">
      <div class="d-flex align-center mb-2">
        <span class="cp-section-title">Line {{ i + 1 }}</span>
        <v-spacer />
        <v-btn :icon="mdiContentCopy" size="small" variant="text" aria-label="Duplicate line" @click="duplicate(i)" />
        <v-btn :icon="mdiDeleteOutline" size="small" variant="text" color="error" aria-label="Remove line" :disabled="lines.length === 1" @click="remove(i)" />
      </div>
      <v-row dense>
        <v-col cols="6" md="3">
          <v-select
            v-model="p.kind"
            :items="kinds()"
            label="Type"
            hide-details="auto"
            @update:model-value="(k: string) => onKindChange(p, k)"
          />
        </v-col>
        <template v-if="p.kind === 'container'">
          <v-col cols="6" md="3"><v-select v-model="p.container_type" :items="CONTAINER_TYPES" label="Equipment" hide-details="auto" /></v-col>
          <v-col cols="6" md="3">
            <v-text-field
              v-model="p.container_number"
              label="Container no."
              placeholder="MSKU1234565"
              class="mono"
              :rules="[containerRule]"
              hide-details="auto"
              @update:model-value="(v: string) => (p.container_number = v.toUpperCase())"
            />
          </v-col>
          <v-col cols="6" md="3"><v-text-field v-model="p.seal_number" label="Seal no." hide-details="auto" /></v-col>
        </template>
        <template v-else>
          <v-col cols="6" md="2"><v-text-field v-model.number="p.quantity" label="Qty" type="number" min="1" hide-details="auto" /></v-col>
          <v-col cols="4" md="2"><v-text-field v-model="p.length_cm" label="L (cm)" type="number" hide-details="auto" /></v-col>
          <v-col cols="4" md="2"><v-text-field v-model="p.width_cm" label="W (cm)" type="number" hide-details="auto" /></v-col>
          <v-col cols="4" md="3"><v-text-field v-model="p.height_cm" label="H (cm)" type="number" hide-details="auto" /></v-col>
        </template>
        <v-col cols="12" md="8"><v-text-field v-model="p.description" label="Description / marks" hide-details="auto" /></v-col>
        <v-col cols="12" md="4">
          <v-text-field
            v-model="p.weight_kg"
            label="Gross weight (line total)"
            type="number"
            suffix="kg"
            hide-details="auto"
            :hint="p.kind !== 'container' && lineVolume(p) ? `${lineVolume(p).toFixed(3)} m³` : ''"
            persistent-hint
          />
        </v-col>
      </v-row>
    </div>
    <v-btn variant="tonal" color="primary" :prepend-icon="mdiPlus" @click="add">Add line</v-btn>
  </div>
</template>

<style scoped>
.cp-line {
  padding: 12px 14px 14px;
  border-radius: 14px;
  border: 1px dashed rgba(var(--v-border-color), 0.2);
  background: rgba(var(--v-theme-on-surface), 0.015);
}
</style>
