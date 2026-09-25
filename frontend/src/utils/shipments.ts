import type { ShipmentListItem } from '@/api/types'

const DONE = new Set(['delivered', 'cancelled'])

/**
 * ETA health for a shipment still moving: late if the promised arrival has passed
 * without delivery, at risk if it's within 24 h and the cargo hasn't reached customs
 * or final delivery.
 */
export function etaHealth(s: Pick<ShipmentListItem, 'status' | 'eta' | 'ata'>): 'late' | 'risk' | 'ok' | null {
  if (!s.eta || DONE.has(s.status) || s.status === 'draft') return null
  const hoursLeft = (new Date(s.eta).getTime() - Date.now()) / 3_600_000
  if (hoursLeft < 0) return 'late'
  if (hoursLeft < 24 && ['booked', 'picked_up', 'in_transit', 'on_hold'].includes(s.status)) return 'risk'
  return 'ok'
}

/** Delivered after the promised ETA? Returns hours late (0 if on time). */
export function hoursLate(s: Pick<ShipmentListItem, 'eta' | 'ata'>): number {
  if (!s.eta || !s.ata) return 0
  return Math.max(0, (new Date(s.ata).getTime() - new Date(s.eta).getTime()) / 3_600_000)
}
