<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage, fieldErrors } from '@/api/http'
import type { Organization } from '@/api/types'
import AuthShell from '@/modules/auth/components/AuthShell.vue'
import { useOrgStore } from '@/stores/org'
import OrgForm from '../components/OrgForm.vue'

const orgStore = useOrgStore()
const router = useRouter()

const form = ref<Partial<Organization>>({ name: '', country: 'AE', base_currency: 'USD', timezone: 'Asia/Dubai' })
const errors = ref<Record<string, string>>({})
const error = ref('')
const busy = ref(false)

async function submit() {
  busy.value = true
  errors.value = {}
  error.value = ''
  try {
    await orgStore.create(form.value)
    await router.replace('/')
  } catch (e) {
    errors.value = fieldErrors(e)
    error.value = Object.keys(errors.value).length ? '' : errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthShell title="Set up your organization" subtitle="You'll be its admin and can invite your team next." :busy="busy" busy-message="Creating workspace…">
    <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mb-4" :text="error" />
    <v-form @submit.prevent="submit">
      <OrgForm v-model="form" :errors="errors" />
      <v-btn type="submit" color="primary" size="large" block class="mt-2" :disabled="!form.name">Create workspace</v-btn>
    </v-form>
  </AuthShell>
</template>
