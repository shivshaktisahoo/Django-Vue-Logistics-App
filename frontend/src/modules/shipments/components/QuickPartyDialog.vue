<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { errorMessage, fieldErrors, http } from '@/api/http'
import type { Party } from '@/api/types'

/** Add a shipper/consignee without leaving the booking form. */
const props = defineProps<{ role: 'shipper' | 'consignee' }>()
const open = defineModel<boolean>({ required: true })
const emit = defineEmits<{ created: [party: Party] }>()

const blank = () => ({ name: '', code: '', city: '', country: '', contact_name: '', email: '' })
const form = reactive(blank())
const errors = ref<Record<string, string>>({})
const error = ref('')
const saving = ref(false)

watch(open, (v) => {
  if (v) {
    Object.assign(form, blank())
    errors.value = {}
    error.value = ''
  }
})

// Suggest a code from the name so the form stays quick.
watch(
  () => form.name,
  (name) => {
    if (!form.code || form.code === suggest(name.slice(0, -1))) form.code = suggest(name)
  },
)
function suggest(name: string) {
  return name.replace(/[^A-Za-z0-9]/g, '').slice(0, 8).toUpperCase()
}

async function save() {
  saving.value = true
  errors.value = {}
  error.value = ''
  try {
    const { data } = await http.post<Party>('/masterdata/parties/', {
      ...form,
      is_shipper: props.role === 'shipper',
      is_consignee: props.role === 'consignee',
    })
    emit('created', data)
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
    <v-card class="cp-card pa-2">
      <v-card-title class="font-weight-bold">New {{ role }}</v-card-title>
      <v-card-text>
        <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mb-3" :text="error" />
        <v-row dense>
          <v-col cols="12" sm="8"><v-text-field v-model="form.name" label="Company name" :error-messages="errors.name" autofocus /></v-col>
          <v-col cols="12" sm="4"><v-text-field v-model="form.code" label="Code" :error-messages="errors.code" /></v-col>
          <v-col cols="8"><v-text-field v-model="form.city" label="City" /></v-col>
          <v-col cols="4"><v-text-field v-model="form.country" label="Country" maxlength="2" placeholder="AE" :error-messages="errors.country" /></v-col>
          <v-col cols="12" sm="6"><v-text-field v-model="form.contact_name" label="Contact person" /></v-col>
          <v-col cols="12" sm="6"><v-text-field v-model="form.email" label="Email" type="email" :error-messages="errors.email" /></v-col>
        </v-row>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="open = false">Cancel</v-btn>
        <v-btn color="primary" variant="flat" :loading="saving" :disabled="!form.name || !form.code || form.country.length !== 2" @click="save">
          Add {{ role }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
