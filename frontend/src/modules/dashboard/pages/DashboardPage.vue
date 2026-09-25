<script setup lang="ts">
import { mdiAirplane, mdiFerry, mdiTruckOutline } from '@mdi/js'
import { computed } from 'vue'
import { ROLE_BY_VALUE } from '@/constants/roles'
import { useAuthStore } from '@/stores/auth'
import { useOrgStore } from '@/stores/org'

const auth = useAuthStore()
const orgStore = useOrgStore()

const role = computed(() => (orgStore.role ? ROLE_BY_VALUE[orgStore.role] : null))
const firstName = computed(() => auth.user?.full_name.split(' ')[0] || 'there')
const greeting = computed(() => {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'
})

const modes = [
  { icon: mdiFerry, label: 'Ocean', text: 'FCL / LCL, container-level tracking' },
  { icon: mdiAirplane, label: 'Air', text: 'MAWB / HAWB, chargeable weight' },
  { icon: mdiTruckOutline, label: 'Road', text: 'FTL / LTL trips, live positions, POD' },
]
</script>

<template>
  <div>
    <v-card class="cp-hero pa-6 pa-md-8 mb-6">
      <div class="cp-hero__glow" />
      <div style="position: relative">
        <div class="text-overline" style="opacity: 0.8">{{ orgStore.org?.name }}</div>
        <h1 class="text-h4 font-weight-bold mb-2" style="letter-spacing: -0.03em">{{ greeting }}, {{ firstName }}.</h1>
        <p class="text-body-1 mb-0" style="opacity: 0.85; max-width: 640px">
          You're signed in as <strong>{{ role?.label }}</strong> — {{ role?.pitch.toLowerCase() }}
        </p>
      </div>
    </v-card>

    <div class="cp-section-title mb-3">Modes supported</div>
    <v-row>
      <v-col v-for="m in modes" :key="m.label" cols="12" md="4">
        <v-card class="cp-card pa-5 h-100">
          <div class="d-flex align-center ga-4">
            <v-avatar color="primary" variant="tonal" rounded="lg" size="48"><v-icon :icon="m.icon" /></v-avatar>
            <div>
              <div class="font-weight-bold">{{ m.label }}</div>
              <div class="text-body-2 text-medium-emphasis">{{ m.text }}</div>
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<style scoped>
.cp-hero {
  position: relative;
  overflow: hidden;
  color: #fff;
  background: var(--cp-sidebar-gradient) !important;
  border-radius: 20px !important;
}
.cp-hero__glow {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(500px circle at 90% 0%, rgba(20, 184, 166, 0.45), transparent 60%),
    radial-gradient(400px circle at 0% 100%, rgba(29, 78, 216, 0.5), transparent 60%);
}
</style>
