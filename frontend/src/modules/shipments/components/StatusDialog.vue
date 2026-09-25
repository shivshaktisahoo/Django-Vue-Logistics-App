<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { errorMessage, fieldErrors, http } from '@/api/http'
import type { Shipment, ShipmentStatus } from '@/api/types'
import { useLookups } from '@/composables/useLookups'
import { TRANSITION_ACTION } from '@/constants/logistics'

const props = defineProps<{ shipment: Shipment; target: ShipmentStatus | 'resume' | null }>()
const open = defineModel<boolean>({ required: true })
const emit = defineEmits<{ done: [shipment: Shipment] }>()
const { locations } = useLookups()

const nowLocal = () => {
  const d = new Date(Date.now() - new Date().getTimezoneOffset() * 60_000)
  return d.toISOString().slice(0, 16)
}

const occurredAt = ref(nowLocal())
const location = ref<string | null>(null)
const note = ref('')
const saving = ref(false)
const error = ref('')
const errors = ref<Record<string, string>>({})

const action = computed(() => (props.target ? TRANSITION_ACTION[props.target] : null))
const needsNote = computed(() => props.target === 'on_hold' || props.target === 'cancelled')
const notePlaceholder = computed(() =>
  props.target === 'on_hold'
    ? 'e.g. Awaiting corrected commercial invoice'
    : props.target === 'cancelled'
      ? 'e.g. Customer postponed the order'
      : 'Optional note shown on the timeline',
)

watch(open, (v) => {
  if (v) {
    occurredAt.value = nowLocal()
    location.value = null
    note.value = ''
    error.value = ''
    errors.value = {}
  }
})

async function confirm() {
  saving.value = true
  error.value = ''
  try {
    const { data } = await http.post<Shipment>(`/shipments/${props.shipment.id}/status/`, {
      target: props.target,
      occurred_at: new Date(occurredAt.value).toISOString(),
      location: location.value,
      note: note.value,
    })
    emit('done', data)
    open.value = false
  } catch (e) {
    errors.value = fieldErrors(e)
    error.value = Object.keys(errors.value).length ? '' : errorMessage(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <v-dialog v-model="open" max-width="520">
    <v-card v-if="action" class="cp-card pa-2">
      <v-card-title class="d-flex align-center ga-3 font-weight-bold">
        <v-avatar :color="action.color" variant="tonal" rounded="lg" size="38"><v-icon :icon="action.icon" /></v-avatar>
        {{ action.label }}
      </v-card-title>
      <v-card-text>
        <div class="text-body-2 text-medium-emphasis mb-4">
          {{ shipment.reference }} · a milestone is added to the timeline and the change is recorded in the audit log.
        </div>
        <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mb-3" :text="error" />
        <v-row dense>
          <v-col cols="12" sm="6">
            <v-text-field v-model="occurredAt" type="datetime-local" label="When did it happen?" :max="nowLocal()" :error-messages="errors.occurred_at" />
          </v-col>
          <v-col cols="12" sm="6">
            <v-autocomplete
              v-model="location"
              :items="locations.data.value ?? []"
              :item-title="(l) => `${l.code} · ${l.name}`"
              item-value="id"
              label="Location"
              placeholder="Default for this step"
              clearable
            />
          </v-col>
          <v-col cols="12">
            <v-textarea
              v-model="note"
              :label="needsNote ? 'Reason (required)' : 'Note'"
              :placeholder="notePlaceholder"
              rows="2"
              auto-grow
              :error-messages="errors.note"
            />
          </v-col>
        </v-row>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="open = false">Cancel</v-btn>
        <v-btn :color="action.color" variant="flat" :loading="saving" :disabled="needsNote && !note.trim()" @click="confirm">
          {{ action.label }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
