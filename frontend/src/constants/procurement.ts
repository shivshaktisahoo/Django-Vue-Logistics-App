import {
  mdiCancel,
  mdiCheckDecagram,
  mdiClipboardTextClockOutline,
  mdiGavel,
  mdiTimerLockOutline,
  mdiRoadVariant,
  mdiTruckCheckOutline,
  mdiTruckFastOutline,
} from '@mdi/js'
import type { BidStatus, TenderStatus, TripStatus } from '@/api/types'

export const TENDER_STATUS: Record<TenderStatus, { label: string; color: string; icon: string }> = {
  open: { label: 'Open for bids', color: 'primary', icon: mdiGavel },
  closed: { label: 'Awaiting award', color: 'warning', icon: mdiTimerLockOutline },
  awarded: { label: 'Awarded', color: 'success', icon: mdiCheckDecagram },
  cancelled: { label: 'Cancelled', color: 'error', icon: mdiCancel },
}

export const BID_STATUS: Record<BidStatus, { label: string; color: string }> = {
  submitted: { label: 'Submitted', color: 'primary' },
  withdrawn: { label: 'Withdrawn', color: 'grey' },
  won: { label: 'Won', color: 'success' },
  lost: { label: 'Not selected', color: 'grey' },
}

export const TRIP_STATUS: Record<TripStatus, { label: string; color: string; icon: string }> = {
  planned: { label: 'Planned', color: 'grey', icon: mdiClipboardTextClockOutline },
  dispatched: { label: 'Dispatched', color: 'indigo', icon: mdiTruckFastOutline },
  in_progress: { label: 'On the road', color: 'cyan-darken-1', icon: mdiRoadVariant },
  completed: { label: 'Completed', color: 'success', icon: mdiTruckCheckOutline },
  cancelled: { label: 'Cancelled', color: 'error', icon: mdiCancel },
}

export const DOC_TYPES = [
  { value: 'commercial_invoice', title: 'Commercial invoice' },
  { value: 'packing_list', title: 'Packing list' },
  { value: 'bill_of_lading', title: 'Bill of lading' },
  { value: 'air_waybill', title: 'Air waybill' },
  { value: 'cmr', title: 'CMR consignment note' },
  { value: 'customs', title: 'Customs declaration' },
  { value: 'certificate', title: 'Certificate (origin, phyto, DG)' },
  { value: 'pod', title: 'Proof of delivery' },
  { value: 'other', title: 'Other' },
]
