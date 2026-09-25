import type { Mode, PackageLine } from '@/api/types'

/**
 * Client-side preview of the backend's chargeable-weight rules
 * (apps/shipments/domain.py). The server stays the source of truth.
 */
export const KG_PER_CBM: Record<Mode, number> = {
  air: 1_000_000 / 6000, // 1:6000
  road: 1_000_000 / 3000, // 1:3000
  ocean: 1000, // W/M: 1 m³ = 1 revenue tonne
}

export function lineVolume(p: Pick<PackageLine, 'length_cm' | 'width_cm' | 'height_cm' | 'quantity'>): number {
  const [l, w, h] = [p.length_cm, p.width_cm, p.height_cm].map(Number)
  if (!l || !w || !h) return 0
  return (l * w * h * (p.quantity || 0)) / 1_000_000
}

export function cargoTotals(mode: Mode | null, packages: PackageLine[]) {
  const pieces = packages.reduce((n, p) => n + (Number(p.quantity) || 0), 0)
  const gross = packages.reduce((n, p) => n + (Number(p.weight_kg) || 0), 0)
  const cbm = packages.reduce((n, p) => n + lineVolume(p), 0)
  const volumetric = mode ? cbm * KG_PER_CBM[mode] : 0
  return { pieces, gross, cbm, volumetric, chargeable: Math.max(gross, volumetric) }
}

// ISO 6346 container number check (mirrors the server; gives instant feedback).
const LETTERS: Record<string, number> = (() => {
  const out: Record<string, number> = {}
  let n = 10
  for (const ch of 'ABCDEFGHIJKLMNOPQRSTUVWXYZ') {
    if (n % 11 === 0) n++
    out[ch] = n++
  }
  return out
})()

export function isValidContainerNumber(raw: string): boolean {
  const n = raw.replace(/\s/g, '').toUpperCase()
  if (!/^[A-Z]{3}[UJZ]\d{7}$/.test(n)) return false
  let sum = 0
  for (let i = 0; i < 10; i++) sum += (/\d/.test(n[i]!) ? Number(n[i]) : LETTERS[n[i]!]!) * 2 ** i
  return (sum % 11) % 10 === Number(n[10])
}

/** Typical piece dimensions to prefill a new line: an air carton or a euro/ISO pallet. */
export function defaultDims(mode: Mode | null): Pick<PackageLine, 'length_cm' | 'width_cm' | 'height_cm'> {
  return mode === 'air'
    ? { length_cm: '60', width_cm: '40', height_cm: '40' }
    : { length_cm: '120', width_cm: '100', height_cm: '150' }
}
