<script setup lang="ts">
import { mdiDeleteOutline, mdiEyeOffOutline, mdiFileDocumentOutline, mdiFileImageOutline, mdiFilePdfBox, mdiTrayArrowDown, mdiUpload } from '@mdi/js'
import { useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, reactive, ref } from 'vue'
import { errorMessage, fieldErrors, http } from '@/api/http'
import type { ShipmentDocument } from '@/api/types'
import EmptyState from '@/components/ui/EmptyState.vue'
import { DOC_TYPES } from '@/constants/procurement'
import { useAuthStore } from '@/stores/auth'
import { useNotify } from '@/stores/notify'
import { useOrgStore } from '@/stores/org'
import { formatBytes, openDocument } from '@/utils/download'
import { formatDateTime } from '@/utils/format'

const props = defineProps<{ shipmentId: string }>()
const orgStore = useOrgStore()
const auth = useAuthStore()
const notify = useNotify()
const queryClient = useQueryClient()
const key = computed(() => ['documents', orgStore.currentId, props.shipmentId])
const internal = computed(() => orgStore.role === 'admin' || orgStore.role === 'ops')

const { data: docs, isLoading } = useQuery({
  queryKey: key,
  queryFn: async () => (await http.get<ShipmentDocument[]>('/documents/', { params: { shipment: props.shipmentId } })).data,
})

const open = ref(false)
const form = reactive({ doc_type: 'commercial_invoice', file: null as File | null, notes: '', visible_to_customer: true })
const errors = ref<Record<string, string>>({})
const saving = ref(false)

async function upload() {
  if (!form.file) return
  saving.value = true
  errors.value = {}
  try {
    const body = new FormData()
    body.append('shipment', props.shipmentId)
    body.append('doc_type', form.doc_type)
    body.append('file', form.file)
    body.append('notes', form.notes)
    body.append('visible_to_customer', String(form.visible_to_customer))
    await http.post('/documents/', body)
    queryClient.invalidateQueries({ queryKey: key.value })
    queryClient.invalidateQueries({ queryKey: ['shipment', orgStore.currentId, props.shipmentId, 'audit'] })
    notify.success('Document uploaded')
    open.value = false
    form.file = null
    form.notes = ''
  } catch (e) {
    errors.value = fieldErrors(e)
    if (!Object.keys(errors.value).length) notify.error(errorMessage(e))
  } finally {
    saving.value = false
  }
}

async function remove(d: ShipmentDocument) {
  try {
    await http.delete(`/documents/${d.id}/`)
    queryClient.invalidateQueries({ queryKey: key.value })
    notify.success(`${d.file_name} deleted`)
  } catch (e) {
    notify.error(errorMessage(e))
  }
}

async function view(d: ShipmentDocument, inline = true) {
  try {
    await openDocument(d.id, d.file_name, inline)
  } catch (e) {
    notify.error(errorMessage(e))
  }
}

const icon = (d: ShipmentDocument) => (d.content_type === 'application/pdf' ? mdiFilePdfBox : d.content_type.startsWith('image/') ? mdiFileImageOutline : mdiFileDocumentOutline)
const canDelete = (d: ShipmentDocument) => internal.value || d.uploaded_by === auth.user?.id
</script>

<template>
  <div>
    <div class="d-flex align-center mb-3">
      <div class="cp-section-title">Documents</div>
      <v-spacer />
      <v-btn v-if="orgStore.can('documents.manage')" size="small" variant="tonal" color="primary" :prepend-icon="mdiUpload" @click="open = true">Upload</v-btn>
    </div>
    <v-skeleton-loader v-if="isLoading" type="list-item-avatar-two-line@2" class="bg-transparent" />
    <EmptyState v-else-if="!docs?.length" :icon="mdiFileDocumentOutline" title="No documents yet" text="Invoices, packing lists, bills and PODs attached to this shipment show up here." />
    <v-list v-else density="comfortable" class="pa-0 bg-transparent">
      <v-list-item v-for="d in docs" :key="d.id" class="px-0" @click="view(d)">
        <template #prepend>
          <v-avatar :color="d.doc_type === 'pod' ? 'success' : 'primary'" variant="tonal" rounded="lg"><v-icon :icon="icon(d)" /></v-avatar>
        </template>
        <v-list-item-title class="font-weight-medium">
          {{ d.doc_type_label }}
          <v-icon v-if="!d.visible_to_customer" :icon="mdiEyeOffOutline" size="14" class="ml-1" title="Internal only" />
        </v-list-item-title>
        <v-list-item-subtitle>{{ d.file_name }} · {{ formatBytes(d.size) }} · {{ d.uploaded_by_name }} · {{ formatDateTime(d.created_at) }}</v-list-item-subtitle>
        <v-list-item-subtitle v-if="d.notes">{{ d.notes }}</v-list-item-subtitle>
        <template #append>
          <v-btn :icon="mdiTrayArrowDown" size="small" variant="text" :aria-label="`Download ${d.file_name}`" @click.stop="view(d, false)" />
          <v-btn v-if="orgStore.can('documents.manage') && canDelete(d)" :icon="mdiDeleteOutline" size="small" variant="text" color="error" :aria-label="`Delete ${d.file_name}`" @click.stop="remove(d)" />
        </template>
      </v-list-item>
    </v-list>

    <v-dialog v-model="open" max-width="480">
      <v-card class="cp-card pa-2">
        <v-card-title class="font-weight-bold">Upload document</v-card-title>
        <v-card-text>
          <v-select v-model="form.doc_type" :items="DOC_TYPES" label="Type" />
          <v-file-input v-model="form.file" label="File (PDF, JPEG, PNG, WebP · max 5 MB)" accept="application/pdf,image/*" show-size :error-messages="errors.file" />
          <v-text-field v-model="form.notes" label="Note (optional)" />
          <v-switch v-if="internal" v-model="form.visible_to_customer" label="Visible to the customer" color="primary" inset hide-details />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="open = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" :loading="saving" :disabled="!form.file" @click="upload">Upload</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
