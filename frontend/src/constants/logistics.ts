import {
  mdiAirplane,
  mdiAlertCircleOutline,
  mdiCancel,
  mdiCheckDecagram,
  mdiClipboardCheckOutline,
  mdiFerry,
  mdiFileDocumentEditOutline,
  mdiPackageUp,
  mdiPauseCircleOutline,
  mdiPlayCircleOutline,
  mdiShieldSearch,
  mdiTransitConnectionVariant,
  mdiTruckDeliveryOutline,
  mdiTruckOutline,
} from '@mdi/js'
import type { Mode, ShipmentStatus } from '@/api/types'

export interface StatusMeta {
  label: string
  color: string
  icon: string
  /** 0–100 position on the journey bar; null for off-path states. */
  progress: number | null
}

export const STATUS: Record<ShipmentStatus, StatusMeta> = {
  draft: { label: 'Draft', color: 'grey', icon: mdiFileDocumentEditOutline, progress: 0 },
  booked: { label: 'Booked', color: 'indigo', icon: mdiClipboardCheckOutline, progress: 10 },
  picked_up: { label: 'Picked up', color: 'blue', icon: mdiPackageUp, progress: 25 },
  in_transit: { label: 'In transit', color: 'cyan-darken-1', icon: mdiTransitConnectionVariant, progress: 55 },
  at_customs: { label: 'At customs', color: 'deep-purple', icon: mdiShieldSearch, progress: 75 },
  out_for_delivery: { label: 'Out for delivery', color: 'teal', icon: mdiTruckDeliveryOutline, progress: 90 },
  delivered: { label: 'Delivered', color: 'success', icon: mdiCheckDecagram, progress: 100 },
  on_hold: { label: 'On hold', color: 'warning', icon: mdiPauseCircleOutline, progress: null },
  cancelled: { label: 'Cancelled', color: 'error', icon: mdiCancel, progress: null },
}

/** Tab order on the shipments list. */
export const STATUS_TABS: (ShipmentStatus | 'active' | 'all')[] = [
  'active',
  'draft',
  'booked',
  'in_transit',
  'at_customs',
  'on_hold',
  'delivered',
  'all',
]
export const ACTIVE_STATUSES: ShipmentStatus[] = ['booked', 'picked_up', 'in_transit', 'at_customs', 'out_for_delivery', 'on_hold']

/** How a transition is presented as an action button. */
export const TRANSITION_ACTION: Record<ShipmentStatus | 'resume', { label: string; icon: string; color: string }> = {
  draft: { label: 'Back to draft', icon: mdiFileDocumentEditOutline, color: 'grey' },
  booked: { label: 'Confirm booking', icon: mdiClipboardCheckOutline, color: 'primary' },
  picked_up: { label: 'Mark picked up', icon: mdiPackageUp, color: 'primary' },
  in_transit: { label: 'Mark departed', icon: mdiTransitConnectionVariant, color: 'primary' },
  at_customs: { label: 'Arrived · at customs', icon: mdiShieldSearch, color: 'primary' },
  out_for_delivery: { label: 'Out for delivery', icon: mdiTruckDeliveryOutline, color: 'primary' },
  delivered: { label: 'Confirm delivery (POD)', icon: mdiCheckDecagram, color: 'success' },
  on_hold: { label: 'Put on hold', icon: mdiPauseCircleOutline, color: 'warning' },
  cancelled: { label: 'Cancel shipment', icon: mdiCancel, color: 'error' },
  resume: { label: 'Release hold', icon: mdiPlayCircleOutline, color: 'primary' },
}

export const MODES: { value: Mode; label: string; icon: string }[] = [
  { value: 'ocean', label: 'Ocean', icon: mdiFerry },
  { value: 'air', label: 'Air', icon: mdiAirplane },
  { value: 'road', label: 'Road', icon: mdiTruckOutline },
]
export const MODE_BY_VALUE = Object.fromEntries(MODES.map((m) => [m.value, m])) as Record<Mode, (typeof MODES)[number]>

export const SERVICE_TYPES: { value: string; label: string; mode: Mode }[] = [
  { value: 'fcl', label: 'FCL · full container', mode: 'ocean' },
  { value: 'lcl', label: 'LCL · consolidated', mode: 'ocean' },
  { value: 'air_std', label: 'Air standard', mode: 'air' },
  { value: 'air_exp', label: 'Air express', mode: 'air' },
  { value: 'ftl', label: 'FTL · full truckload', mode: 'road' },
  { value: 'ltl', label: 'LTL · part load', mode: 'road' },
]
export const SERVICE_LABEL = Object.fromEntries(SERVICE_TYPES.map((s) => [s.value, s.label.split(' · ')[0]]))

export const INCOTERMS = [
  { value: 'EXW', title: 'EXW · Ex Works' },
  { value: 'FCA', title: 'FCA · Free Carrier' },
  { value: 'FOB', title: 'FOB · Free On Board' },
  { value: 'CFR', title: 'CFR · Cost and Freight' },
  { value: 'CIF', title: 'CIF · Cost, Insurance & Freight' },
  { value: 'CPT', title: 'CPT · Carriage Paid To' },
  { value: 'DAP', title: 'DAP · Delivered At Place' },
  { value: 'DDP', title: 'DDP · Delivered Duty Paid' },
]

export const PACKAGE_KINDS = [
  { value: 'container', title: 'Container' },
  { value: 'pallet', title: 'Pallet' },
  { value: 'carton', title: 'Carton' },
  { value: 'crate', title: 'Crate' },
  { value: 'drum', title: 'Drum' },
  { value: 'piece', title: 'Loose piece' },
]

export const CONTAINER_TYPES = [
  { value: '20GP', title: "20' General purpose" },
  { value: '40GP', title: "40' General purpose" },
  { value: '40HC', title: "40' High cube" },
  { value: '45HC', title: "45' High cube" },
  { value: '20RF', title: "20' Reefer" },
  { value: '40RF', title: "40' Reefer" },
]

/** Informational milestones that can be added by hand (status milestones come from transitions). */
export const MANUAL_EVENT_CODES = [
  { value: 'GIN', title: 'GIN · Gate in at origin' },
  { value: 'LOD', title: 'LOD · Loaded on vessel / aircraft / truck' },
  { value: 'ARR', title: 'ARR · Arrived at destination hub' },
  { value: 'DIS', title: 'DIS · Discharged / unloaded' },
  { value: 'CLR', title: 'CLR · Customs cleared' },
  { value: 'DLY', title: 'DLY · Delay reported' },
  { value: 'NTE', title: 'NTE · Update / note' },
]

export const EVENT_ICON: Record<string, string> = {
  DLY: mdiAlertCircleOutline,
  HLD: mdiPauseCircleOutline,
  CAN: mdiCancel,
}

export const LOCATION_KINDS = [
  { value: 'seaport', title: 'Seaport' },
  { value: 'airport', title: 'Airport' },
  { value: 'inland', title: 'Inland depot' },
  { value: 'warehouse', title: 'Warehouse' },
  { value: 'city', title: 'City / door' },
]

export const VEHICLE_TYPES = [
  { value: 'tractor_trailer', title: 'Tractor + trailer' },
  { value: 'box_truck', title: 'Box truck' },
  { value: 'reefer', title: 'Reefer' },
  { value: 'flatbed', title: 'Flatbed' },
  { value: 'van', title: 'Van' },
]
