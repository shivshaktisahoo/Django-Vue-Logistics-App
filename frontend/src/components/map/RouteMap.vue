<script setup lang="ts">
import L from 'leaflet'
import { shallowRef, watch } from 'vue'
import type { EtaHealth, GeoPoint, LivePosition, Mode } from '@/api/types'
import { HEALTH_COLOR, portIcon, splitRoute, unwrap, vehicleIcon } from '@/utils/map'
import BaseMap from './BaseMap.vue'

/** One shipment's route: travelled leg solid, remaining leg dashed, vehicle at its estimated position. */
const props = withDefaults(
  defineProps<{
    route: [number, number][]
    position: LivePosition | null
    origin: GeoPoint
    destination: GeoPoint
    mode: Mode
    health: EtaHealth
    height?: string
  }>(),
  { height: '320px' },
)

const map = shallowRef<L.Map | null>(null)
let layer: L.LayerGroup | null = null

function draw() {
  if (!map.value) return
  layer?.remove()
  layer = L.layerGroup().addTo(map.value)
  const route = unwrap(props.route)
  const color = HEALTH_COLOR[props.health ?? 'ok']!
  const progress = props.position?.progress ?? 0
  const { done, todo } = splitRoute(route, progress)
  if (todo.length > 1) L.polyline(todo, { color, weight: 3, opacity: 0.55, dashArray: '6 8' }).addTo(layer)
  if (done.length > 1) L.polyline(done, { color, weight: 4, opacity: 0.95 }).addTo(layer)

  const first = route[0]!
  const last = route[route.length - 1]!
  L.marker(first, { icon: portIcon('origin') }).bindTooltip(`${props.origin.code} · ${props.origin.name}`).addTo(layer)
  L.marker(last, { icon: portIcon('destination') }).bindTooltip(`${props.destination.code} · ${props.destination.name}`).addTo(layer)
  if (props.position && props.position.phase === 'moving') {
    // Place the vehicle at the split point so it sits exactly on the drawn (unwrapped) line.
    const at = done[done.length - 1] ?? [props.position.lat, props.position.lng]
    L.marker(at, { icon: vehicleIcon(props.mode, props.health, true) })
      .bindTooltip(`${Math.round(props.position.progress * 100)}% of the way`)
      .addTo(layer)
  }
  map.value.fitBounds(L.latLngBounds(route), { padding: [36, 36], maxZoom: 7 })
}

function onReady(m: L.Map) {
  map.value = m
  draw()
}

watch(() => [props.route, props.position, props.health], draw)
</script>

<template>
  <BaseMap :height="height" @ready="onReady" />
</template>
