import L from 'leaflet'
import { mdiAirplane, mdiFerry, mdiMapMarker, mdiTruck } from '@mdi/js'
import type { EtaHealth, Mode } from '@/api/types'

// Keyless muted basemaps (Esri Gray Canvas) suit a data-first control tower. Point
// VITE_MAP_TILES_LIGHT / VITE_MAP_TILES_DARK at another provider (MapTiler, Stadia…)
// to swap them without code changes.
const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas'
const TILES = {
  light: import.meta.env.VITE_MAP_TILES_LIGHT ?? `${ESRI}/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}`,
  dark: import.meta.env.VITE_MAP_TILES_DARK ?? `${ESRI}/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}`,
}
const ATTRIBUTION =
  import.meta.env.VITE_MAP_ATTRIBUTION ??
  'Tiles &copy; <a href="https://www.esri.com">Esri</a> &mdash; Esri, HERE, Garmin, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

export function tileLayer(dark: boolean): L.TileLayer {
  return L.tileLayer(dark ? TILES.dark : TILES.light, { attribution: ATTRIBUTION, maxZoom: 16 })
}

export const HEALTH_COLOR: Record<string, string> = {
  late: '#DC2626',
  risk: '#D97706',
  ok: '#1D4ED8',
  none: '#64748B',
}

const MODE_PATH: Record<Mode, string> = { ocean: mdiFerry, air: mdiAirplane, road: mdiTruck }

/** A round badge with the transport-mode glyph, coloured by ETA health. */
export function vehicleIcon(mode: Mode, health: EtaHealth, selected = false): L.DivIcon {
  const color = HEALTH_COLOR[health ?? 'none']!
  const size = selected ? 38 : 30
  return L.divIcon({
    className: 'cp-vehicle',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    html: `<div class="cp-vehicle__badge${selected ? ' is-selected' : ''}" style="--c:${color}">
      <svg viewBox="0 0 24 24" width="${size * 0.55}" height="${size * 0.55}"><path fill="#fff" d="${MODE_PATH[mode]}"/></svg>
    </div>`,
  })
}

export function portIcon(kind: 'origin' | 'destination'): L.DivIcon {
  const color = kind === 'origin' ? '#0891B2' : '#16A34A'
  return L.divIcon({
    className: 'cp-port',
    iconSize: [26, 26],
    iconAnchor: [13, 24],
    html: `<svg viewBox="0 0 24 24" width="26" height="26"><path fill="${color}" stroke="#fff" stroke-width="1" d="${mdiMapMarker}"/></svg>`,
  })
}

/**
 * Leaflet draws a line from 170°E to -170°E the long way round. Shift longitudes so
 * consecutive points never jump more than 180° (e.g. trans-Pacific routes).
 */
export function unwrap(points: [number, number][]): [number, number][] {
  const out: [number, number][] = []
  for (const [lat, lng] of points) {
    const prev = out[out.length - 1]
    let adjusted = lng
    if (prev) {
      while (adjusted - prev[1] > 180) adjusted -= 360
      while (adjusted - prev[1] < -180) adjusted += 360
    }
    out.push([lat, adjusted])
  }
  return out
}

/** Split a route at the vehicle's progress: travelled part solid, remaining dashed. */
export function splitRoute(route: [number, number][], progress: number): { done: [number, number][]; todo: [number, number][] } {
  if (route.length < 2) return { done: [], todo: route }
  const dist = (a: [number, number], b: [number, number]) => Math.hypot(a[0] - b[0], a[1] - b[1])
  const legs = route.slice(1).map((p, i) => dist(route[i]!, p))
  let target = legs.reduce((a, b) => a + b, 0) * Math.min(Math.max(progress, 0), 1)
  for (let i = 0; i < legs.length; i++) {
    if (target <= legs[i]! || i === legs.length - 1) {
      const f = legs[i] ? Math.min(target / legs[i]!, 1) : 0
      const a = route[i]!
      const b = route[i + 1]!
      const mid: [number, number] = [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f]
      return { done: [...route.slice(0, i + 1), mid], todo: [mid, ...route.slice(i + 1)] }
    }
    target -= legs[i]!
  }
  return { done: route, todo: [] }
}
