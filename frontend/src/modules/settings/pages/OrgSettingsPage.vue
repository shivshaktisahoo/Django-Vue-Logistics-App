<script setup lang="ts">
import { mdiDomain } from '@mdi/js'
import { ref } from 'vue'
import { errorMessage, fieldErrors } from '@/api/http'
import type { Organization } from '@/api/types'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useNotify } from '@/stores/notify'
import { useOrgStore } from '@/stores/org'
import OrgForm from '../components/OrgForm.vue'

const orgStore = useOrgStore()
const notify = useNotify()

const form = ref<Partial<Organization>>({ ...orgStore.org })
const errors = ref<Record<string, string>>({})
const saving = ref(false)
const canEdit = orgStore.can('org.manage')

async function save() {
  saving.value = true
  errors.value = {}
  try {
    form.value = { ...(await orgStore.update(form.value)) }
    notify.success('Organization saved')
  } catch (e) {
    errors.value = fieldErrors(e)
    notify.error(errorMessage(e))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <PageHeader title="Organization" subtitle="Company profile used on bookings, documents and notifications." :icon="mdiDomain" />
    <v-card class="cp-card pa-5 pa-md-6" style="max-width: 900px">
      <v-form @submit.prevent="save">
        <OrgForm v-model="form" :errors="errors" :readonly="!canEdit" />
        <div v-if="canEdit" class="d-flex justify-end mt-2">
          <v-btn type="submit" color="primary" :loading="saving">Save changes</v-btn>
        </div>
      </v-form>
    </v-card>
  </div>
</template>
