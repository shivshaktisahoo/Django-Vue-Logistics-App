<script setup lang="ts">
import { mdiAirplane, mdiCheckCircle, mdiFerry, mdiGavel, mdiMapMarkerPath, mdiDatabaseSyncOutline } from '@mdi/js'
import LoadingOverlay from '@/components/ui/LoadingOverlay.vue'
import { BRAND } from '@/config/brand'

withDefaults(defineProps<{ title: string; subtitle?: string; busy?: boolean; busyMessage?: string }>(), {
  subtitle: '',
  busy: false,
  busyMessage: 'Please wait…',
})

const features = [
  { icon: mdiMapMarkerPath, title: 'End-to-end visibility', text: 'Milestones, live positions and ETA risk in one timeline.' },
  { icon: mdiGavel, title: 'Carrier tendering', text: 'Spot RFQs, sealed bids and one-click award to trip.' },
  { icon: mdiDatabaseSyncOutline, title: 'Built to integrate', text: 'CargoWise-style XML imports and signed webhooks.' },
]

const milestones = [
  { code: 'BKD', label: 'Booked', done: true },
  { code: 'DEP', label: 'Departed JEA', done: true },
  { code: 'ARR', label: 'Arrived RTM', done: false },
]
</script>

<template>
  <v-main class="cp-auth">
    <div class="cp-auth__grid">
      <!-- Brand panel -->
      <section class="cp-auth__brand d-none d-md-flex">
        <div class="cp-auth__glow" />
        <div class="d-flex align-center ga-3 mb-12" style="position: relative">
          <img src="/favicon.svg" width="42" height="42" alt="" class="cp-auth__logo" />
          <span class="text-h5 font-weight-bold">{{ BRAND.name }}</span>
        </div>

        <div style="position: relative; max-width: 480px">
          <h2 class="cp-auth__headline">Every shipment, every milestone, one control tower.</h2>
          <p class="text-body-1 mt-4 mb-10" style="opacity: 0.8">
            A multi-tenant platform for freight forwarders: bookings, carrier bidding, trip execution and customer
            visibility across air, ocean and road.
          </p>

          <div class="d-flex flex-column ga-5">
            <div v-for="f in features" :key="f.title" class="d-flex ga-4 align-start">
              <div class="cp-auth__feature-icon"><v-icon :icon="f.icon" size="22" /></div>
              <div>
                <div class="font-weight-bold">{{ f.title }}</div>
                <div class="text-body-2" style="opacity: 0.72">{{ f.text }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Shipment preview card -->
        <div class="cp-auth__shipment" aria-hidden="true">
          <div class="d-flex justify-space-between align-center mb-3">
            <div>
              <div class="text-caption" style="opacity: 0.6">OCEAN · FCL · 2 × 40HC</div>
              <div class="font-weight-bold">SHP-2026-000142</div>
            </div>
            <span class="cp-auth__status">IN TRANSIT</span>
          </div>
          <div class="d-flex align-center ga-2 mb-3 text-body-2">
            <strong>AEJEA</strong>
            <div class="cp-auth__lane"><v-icon :icon="mdiFerry" size="16" class="cp-auth__ship" /></div>
            <strong>NLRTM</strong>
          </div>
          <div v-for="m in milestones" :key="m.code" class="cp-auth__row" :class="{ muted: !m.done }">
            <span class="d-flex align-center ga-2">
              <v-icon :icon="m.done ? mdiCheckCircle : mdiAirplane" size="14" :color="m.done ? 'teal-lighten-2' : undefined" />
              {{ m.label }}
            </span>
            <span class="mono">{{ m.code }}</span>
          </div>
        </div>

        <div class="text-body-2 mt-auto" style="position: relative; opacity: 0.7">
          Portfolio project · Django REST Framework · Celery · PostgreSQL · Vue 3 · Vuetify
        </div>
      </section>

      <!-- Form panel -->
      <section class="cp-auth__form">
        <div class="cp-auth__card">
          <div class="d-flex d-md-none align-center ga-2 mb-8">
            <img src="/favicon.svg" width="34" height="34" alt="" />
            <span class="text-h6 font-weight-bold">{{ BRAND.name }}</span>
          </div>
          <h1 class="text-h4 font-weight-bold mb-2" style="letter-spacing: -0.03em">{{ title }}</h1>
          <p v-if="subtitle" class="text-body-1 text-medium-emphasis mb-6">{{ subtitle }}</p>
          <div style="position: relative">
            <slot />
            <LoadingOverlay :active="busy" :message="busyMessage" />
          </div>
        </div>
      </section>
    </div>
  </v-main>
</template>

<style scoped>
.cp-auth__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  min-height: 100vh;
}
@media (min-width: 960px) {
  .cp-auth__grid {
    grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
  }
}
.cp-auth__brand {
  position: relative;
  overflow: hidden;
  flex-direction: column;
  padding: 48px 56px;
  color: #fff;
  background: var(--cp-sidebar-gradient);
}
.cp-auth__glow {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(600px circle at 85% 15%, rgba(20, 184, 166, 0.4), transparent 60%),
    radial-gradient(500px circle at 10% 90%, rgba(29, 78, 216, 0.55), transparent 60%);
  animation: drift 14s ease-in-out infinite alternate;
}
@keyframes drift {
  to {
    transform: translate3d(-20px, 12px, 0) scale(1.05);
  }
}
.cp-auth__logo {
  filter: drop-shadow(0 8px 20px rgba(0, 0, 0, 0.35));
}
.cp-auth__headline {
  font-size: clamp(2rem, 3vw, 2.75rem);
  line-height: 1.12;
  font-weight: 800;
  letter-spacing: -0.035em;
}
.cp-auth__feature-icon {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.14);
}
.cp-auth__shipment {
  position: relative;
  align-self: flex-end;
  width: 330px;
  margin: 40px 0 32px;
  padding: 18px 20px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(14px);
  box-shadow: 0 30px 60px -20px rgba(0, 0, 0, 0.45);
  transform: rotate(-2deg);
  animation: float 6s ease-in-out infinite;
}
@keyframes float {
  50% {
    transform: rotate(-2deg) translateY(-8px);
  }
}
.cp-auth__lane {
  position: relative;
  flex: 1;
  height: 2px;
  background: repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.5) 0 6px, transparent 6px 10px);
}
.cp-auth__ship {
  position: absolute;
  top: -8px;
  left: 0;
  animation: sail 5s ease-in-out infinite alternate;
}
@keyframes sail {
  to {
    left: calc(100% - 16px);
  }
}
.cp-auth__row {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  padding: 6px 0;
  border-top: 1px dashed rgba(255, 255, 255, 0.15);
}
.cp-auth__row.muted {
  opacity: 0.55;
}
.cp-auth__status {
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(34, 211, 238, 0.2);
  color: #a5f3fc;
}
.cp-auth__form {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 20px;
}
.cp-auth__card {
  width: 100%;
  max-width: 460px;
}
</style>
