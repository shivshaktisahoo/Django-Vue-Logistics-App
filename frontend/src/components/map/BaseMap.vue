<script setup lang="ts">
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useTheme } from 'vuetify'
import { tileLayer } from '@/utils/map'

/** Leaflet map with CARTO tiles that follow the app's light/dark theme. */
const props = withDefaults(defineProps<{ height?: string; interactive?: boolean }>(), { height: '100%', interactive: true })
const emit = defineEmits<{ ready: [map: L.Map] }>()

const el = ref<HTMLElement | null>(null)
const map = shallowRef<L.Map | null>(null)
const theme = useTheme()
let tiles: L.TileLayer | null = null
let observer: ResizeObserver | null = null

function applyTiles() {
  if (!map.value) return
  tiles?.remove()
  tiles = tileLayer(theme.global.current.value.dark).addTo(map.value)
}

onMounted(() => {
  map.value = L.map(el.value!, {
    zoomControl: props.interactive,
    scrollWheelZoom: props.interactive,
    dragging: props.interactive,
    worldCopyJump: true,
    attributionControl: true,
    zoomSnap: 0.25,
  }).setView([25, 55], 3)
  applyTiles()
  // Leaflet measures its container once; re-measure when the layout changes.
  observer = new ResizeObserver(() => map.value?.invalidateSize())
  observer.observe(el.value!)
  emit('ready', map.value)
})

watch(() => theme.global.current.value.dark, applyTiles)

onBeforeUnmount(() => {
  observer?.disconnect()
  map.value?.remove()
})

defineExpose({ map })
</script>

<template>
  <div ref="el" class="cp-map" :style="{ height }" />
</template>

<style>
.cp-map {
  width: 100%;
  border-radius: inherit;
  z-index: 0;
  background: rgb(var(--v-theme-surface-variant));
}
.cp-vehicle__badge {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--c);
  border: 2px solid #fff;
  box-shadow:
    0 0 0 4px color-mix(in srgb, var(--c) 25%, transparent),
    0 4px 10px rgba(0, 0, 0, 0.3);
  transition: transform 0.15s ease;
}
.cp-vehicle__badge.is-selected {
  box-shadow:
    0 0 0 6px color-mix(in srgb, var(--c) 35%, transparent),
    0 6px 14px rgba(0, 0, 0, 0.35);
}
.cp-vehicle:hover .cp-vehicle__badge {
  transform: scale(1.12);
}
.leaflet-container {
  font-family: inherit;
}
.leaflet-popup-content-wrapper,
.leaflet-popup-tip {
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
}
</style>
