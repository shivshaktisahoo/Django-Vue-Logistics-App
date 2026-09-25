<script setup lang="ts">
import { mdiAlertCircleOutline, mdiCheckCircleOutline, mdiInformationOutline } from '@mdi/js'
import { storeToRefs } from 'pinia'
import { computed } from 'vue'
import FullscreenLoader from '@/components/ui/FullscreenLoader.vue'
import { useNotify } from '@/stores/notify'
import { useUiStore } from '@/stores/ui'

const notify = useNotify()
const ui = useUiStore()
const { toast, visible } = storeToRefs(notify)

const TOAST_ICONS: Record<string, string> = { success: mdiCheckCircleOutline, error: mdiAlertCircleOutline }
const toastIcon = computed(() => TOAST_ICONS[toast.value?.color ?? ''] ?? mdiInformationOutline)

function runAction() {
  toast.value?.action?.handler()
  visible.value = false
}
</script>

<template>
  <v-app>
    <v-progress-linear
      :active="ui.navigating"
      indeterminate
      color="secondary"
      height="3"
      absolute
      style="position: fixed; top: 0; z-index: 3000"
    />

    <router-view />

    <FullscreenLoader :message="ui.fullscreenMessage" />

    <v-snackbar
      v-model="visible"
      :color="toast?.color"
      location="bottom right"
      :timeout="4500"
      rounded="lg"
      elevation="8"
    >
      <div class="d-flex align-center ga-3">
        <v-icon :icon="toastIcon" />
        <span class="font-weight-medium">{{ toast?.text }}</span>
      </div>
      <template v-if="toast?.action" #actions>
        <v-btn variant="text" class="font-weight-bold" @click="runAction">{{ toast.action.label }}</v-btn>
      </template>
    </v-snackbar>
  </v-app>
</template>
