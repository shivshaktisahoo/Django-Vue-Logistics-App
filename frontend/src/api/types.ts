export type Role = 'admin' | 'ops' | 'customer' | 'carrier'

export interface User {
  id: string
  email: string
  full_name: string
  job_title: string
  phone: string
  is_demo: boolean
  date_joined: string
}

export interface AuthResponse {
  access: string
  user: User
}

export interface Organization {
  id: string
  name: string
  legal_name: string
  country: string
  base_currency: string
  timezone: string
  email: string
  phone: string
  address: string
  is_demo: boolean
  created_at: string
}

export interface MyOrg {
  org: Organization
  role: Role
  permissions: string[]
}

export interface Member {
  id: string
  email: string
  full_name: string
  job_title: string
  role: Role
  is_active: boolean
  created_at: string
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// ---------------------------------------------------------------- master data

export type Mode = 'air' | 'ocean' | 'road'

export interface Party {
  id: string
  name: string
  code: string
  is_customer: boolean
  is_shipper: boolean
  is_consignee: boolean
  owner: string | null
  contact_name: string
  email: string
  phone: string
  address: string
  city: string
  country: string
  tax_id: string
  is_active: boolean
  created_at: string
}

export interface Location {
  id: string
  code: string
  name: string
  kind: 'seaport' | 'airport' | 'inland' | 'warehouse' | 'city'
  city: string
  country: string
  latitude: string
  longitude: string
  timezone: string
  is_active: boolean
}

export interface Carrier {
  id: string
  name: string
  code: string
  mode: Mode
  email: string
  phone: string
  country: string
  is_active: boolean
  vehicle_count: number
  driver_count: number
}

export interface Vehicle {
  id: string
  carrier: string
  carrier_name: string
  plate_number: string
  vehicle_type: string
  capacity_kg: number
  is_active: boolean
}

export interface Driver {
  id: string
  carrier: string
  carrier_name: string
  name: string
  phone: string
  license_number: string
  is_active: boolean
}

// ---------------------------------------------------------------- shipments

export type ShipmentStatus =
  | 'draft'
  | 'booked'
  | 'picked_up'
  | 'in_transit'
  | 'at_customs'
  | 'out_for_delivery'
  | 'delivered'
  | 'on_hold'
  | 'cancelled'

export type PartyRef = Pick<Party, 'id' | 'name' | 'code' | 'city' | 'country'>
export type LocationRef = Pick<Location, 'id' | 'code' | 'name' | 'kind' | 'city' | 'country' | 'latitude' | 'longitude'>
export type CarrierRef = Pick<Carrier, 'id' | 'name' | 'code' | 'mode'>

export interface PackageLine {
  id?: string
  kind: 'container' | 'pallet' | 'carton' | 'crate' | 'drum' | 'piece'
  container_type: string
  container_number: string
  seal_number: string
  quantity: number
  description: string
  weight_kg: string
  length_cm: string | null
  width_cm: string | null
  height_cm: string | null
  volume_cbm?: string
}

export interface ShipmentListItem {
  id: string
  reference: string
  tracking_number: string
  status: ShipmentStatus
  mode: Mode
  service_type: string
  incoterm: string
  customer: PartyRef
  origin: LocationRef
  destination: LocationRef
  carrier: CarrierRef | null
  etd: string | null
  eta: string | null
  atd: string | null
  ata: string | null
  commodity: string
  customer_reference: string
  total_packages: number
  gross_weight_kg: string
  chargeable_weight_kg: string
  is_hazardous: boolean
  is_temperature_controlled: boolean
  created_at: string
  updated_at: string
}

export interface Shipment extends ShipmentListItem {
  shipper: PartyRef
  consignee: PartyRef
  held_from_status: string
  house_bill: string
  master_bill: string
  voyage_number: string
  hs_code: string
  declared_value: string | null
  currency: string
  special_instructions: string
  volume_cbm: string
  packages: PackageLine[]
  allowed_transitions: (ShipmentStatus | 'resume')[]
  can_edit: boolean
}

export interface TrackingEvent {
  id: string
  code: string
  code_label: string
  description: string
  location: LocationRef | null
  occurred_at: string
  source: string
  is_public: boolean
  created_by_name: string
  created_at: string
}

export interface AuditEntry {
  id: string
  action: string
  entity_type: string
  entity_id: string
  entity_label: string
  summary: string
  changes: Record<string, [unknown, unknown]>
  actor_name: string
  created_at: string
}

export interface CursorPage<T> {
  next: string | null
  previous: string | null
  results: T[]
}

// ---------------------------------------------------------------- tracking & exceptions

export type EtaHealth = 'late' | 'risk' | 'ok' | null

export interface GeoPoint {
  code: string
  name: string
  city: string
  country: string
  lat: number
  lng: number
}

export interface LivePosition {
  lat: number
  lng: number
  heading: number
  progress: number
  phase: 'at_origin' | 'moving' | 'at_destination'
}

export interface LiveShipment {
  id: string
  reference: string
  tracking_number: string
  status: ShipmentStatus
  mode: Mode
  customer: string
  carrier: string | null
  origin: GeoPoint
  destination: GeoPoint
  etd: string | null
  eta: string | null
  atd: string | null
  position: LivePosition | null
  eta_health: EtaHealth
  distance_km: number
  route: [number, number][]
}

export interface PublicTracking {
  tracking_number: string
  status: ShipmentStatus
  status_label: string
  mode: Mode
  service: string
  forwarder: string
  origin: GeoPoint
  destination: GeoPoint
  etd: string | null
  eta: string | null
  atd: string | null
  ata: string | null
  pieces: number
  events: { code: string; label: string; description: string; location: string | null; occurred_at: string }[]
  position: LivePosition | null
  eta_health: EtaHealth
  distance_km: number
  route: [number, number][]
}

export type ExceptionSeverity = 'low' | 'medium' | 'high' | 'critical'
export type ExceptionStatus = 'open' | 'acknowledged' | 'resolved'

export interface ShipmentExceptionItem {
  id: string
  shipment: {
    id: string
    reference: string
    status: ShipmentStatus
    mode: Mode
    customer: string
    origin: string
    destination: string
    eta: string | null
  }
  kind: string
  kind_label: string
  severity: ExceptionSeverity
  status: ExceptionStatus
  title: string
  detail: string
  detected_at: string
  assignee_id: string | null
  assignee_name: string | null
  acknowledged_at: string | null
  resolved_at: string | null
  resolved_by_name: string | null
  resolution_note: string
  auto_resolved: boolean
  updated_at: string
}

export interface ExceptionSummary {
  open: number
  acknowledged: number
  critical: number
  high: number
  mine: number
}

// ---------------------------------------------------------------- procurement, trips, documents

export type TenderStatus = 'open' | 'closed' | 'awarded' | 'cancelled'
export type BidStatus = 'submitted' | 'withdrawn' | 'won' | 'lost'
export type TripStatus = 'planned' | 'dispatched' | 'in_progress' | 'completed' | 'cancelled'

export interface PlaceRef {
  code: string
  name: string
  city: string
  country: string
}

export interface Load {
  id: string
  reference: string
  status: ShipmentStatus
  service_type: string
  commodity: string
  total_packages: number
  gross_weight_kg: string
  volume_cbm: string
  is_hazardous: boolean
  is_temperature_controlled: boolean
  origin: PlaceRef
  destination: PlaceRef
}

export interface Bid {
  id: string
  carrier: string
  carrier_name: string
  carrier_code: string
  amount: string
  currency: string
  transit_hours: number
  notes: string
  status: BidStatus
  revision: number
  updated_at: string
}

export interface Tender {
  id: string
  reference: string
  status: TenderStatus
  shipment: Load
  customer: string | null
  vehicle_type: string
  pickup_at: string
  deliver_by: string
  closes_at: string
  currency: string
  notes: string
  target_rate: string | null
  bid_count: number | null
  best_amount: string | null
  invited_count: number
  my_bid: Bid | null
  awarded_to: string | null
  cancel_reason: string
  created_at: string
}

export interface TenderDetail extends Tender {
  bids: Bid[] | null
  invited_carriers: { id: string; name: string; code: string }[] | null
  trip_id: string | null
}

export interface TripStop {
  id: number
  sequence: number
  kind: 'pickup' | 'delivery'
  location: PlaceRef
  shipment: {
    id: string
    reference: string
    status: ShipmentStatus
    commodity: string
    total_packages: number
    gross_weight_kg: string
    is_hazardous: boolean
    is_temperature_controlled: boolean
  }
  party: { name: string; contact: string; phone: string; city: string }
  planned_at: string
  arrived_at: string | null
  completed_at: string | null
  receiver_name: string
}

export interface Trip {
  id: string
  reference: string
  status: TripStatus
  carrier: { id: string; name: string; code: string }
  vehicle: { id: string; plate_number: string; vehicle_type: string; capacity_kg: number } | null
  driver: { id: string; name: string; phone: string } | null
  tender: { id: string; reference: string } | null
  agreed_rate: string | null
  currency: string
  planned_start: string
  planned_end: string
  started_at: string | null
  completed_at: string | null
  notes: string
  stops: TripStop[]
  next_stop_id: string | null
  load_kg: string
}

export interface FleetOptions {
  load_kg: string
  vehicles: { id: string; plate_number: string; vehicle_type: string; capacity_kg: number; fits: boolean; busy_on: string | null }[]
  drivers: { id: string; name: string; phone: string }[]
}

export interface ShipmentDocument {
  id: string
  shipment: string
  trip: string | null
  doc_type: string
  doc_type_label: string
  file_name: string
  content_type: string
  size: number
  notes: string
  visible_to_customer: boolean
  uploaded_by: string | null
  uploaded_by_name: string
  created_at: string
}
