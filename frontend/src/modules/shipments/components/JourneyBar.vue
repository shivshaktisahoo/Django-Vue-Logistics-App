<script setup lang="ts">
import { mdiCheck } from '@mdi/js'
import { computed } from 'vue'
import type { Shipment, ShipmentStatus } from '@/api/types'
import { STATUS } from '@/constants/logistics'

const props = defineProps<{ shipment: Pick<Shipment, 'status' | 'held_from_status'> }>()

const STEPS: ShipmentStatus[] = ['booked', 'picked_up', 'in_transit', 'at_customs', 'out_for_delivery', 'delivered']

// While on hold, show progress as of the status it was held from.
const effective = computed<ShipmentStatus>(() =>
  props.shipment.status === 'on_hold' ? (props.shipment.held_from_status as ShipmentStatus) : props.shipment.status,
)
const currentIndex = computed(() => STEPS.indexOf(effective.value))
</script>

<template>
  <div class="cp-journey" :class="{ 'cp-journey--muted': shipment.status === 'cancelled' || shipment.status === 'draft' }">
    <div v-for="(step, i) in STEPS" :key="step" class="cp-journey__step" :data-state="i < currentIndex ? 'done' : i === currentIndex ? 'current' : 'todo'">
      <div class="cp-journey__dot">
        <v-icon v-if="i < currentIndex || (i === currentIndex && step === 'delivered')" :icon="mdiCheck" size="14" />
        <v-icon v-else :icon="STATUS[step].icon" size="14" />
      </div>
      <div class="cp-journey__label">{{ STATUS[step].label }}</div>
    </div>
  </div>
</template>

<style scoped>
.cp-journey {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  position: relative;
}
.cp-journey__step {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 8px;
}
/* connector line to the previous step */
.cp-journey__step + .cp-journey__step::before {
  content: '';
  position: absolute;
  top: 13px;
  right: 50%;
  width: 100%;
  height: 3px;
  border-radius: 3px;
  background: rgba(var(--v-border-color), 0.12);
}
.cp-journey__step[data-state='done']::before,
.cp-journey__step[data-state='current']::before {
  background: linear-gradient(90deg, rgb(var(--v-theme-primary)), rgb(var(--v-theme-secondary)));
}
.cp-journey__dot {
  position: relative;
  z-index: 1;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: rgb(var(--v-theme-surface));
  border: 2px solid rgba(var(--v-border-color), 0.18);
  color: rgba(var(--v-theme-on-surface), 0.45);
}
.cp-journey__step[data-state='done'] .cp-journey__dot {
  background: rgb(var(--v-theme-primary));
  border-color: rgb(var(--v-theme-primary));
  color: #fff;
}
.cp-journey__step[data-state='current'] .cp-journey__dot {
  border-color: rgb(var(--v-theme-secondary));
  color: rgb(var(--v-theme-secondary));
  box-shadow: 0 0 0 5px rgba(var(--v-theme-secondary), 0.18);
}
.cp-journey__label {
  font-size: 0.75rem;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.55);
}
.cp-journey__step[data-state='current'] .cp-journey__label {
  color: rgb(var(--v-theme-on-surface));
}
.cp-journey--muted {
  opacity: 0.5;
  filter: grayscale(1);
}
@media (max-width: 600px) {
  .cp-journey__label {
    font-size: 0.62rem;
  }
}
</style>
