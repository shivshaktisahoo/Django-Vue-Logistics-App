import { mdiAccountTieOutline, mdiHeadset, mdiShieldCrownOutline, mdiTruckFastOutline } from '@mdi/js'
import type { Role } from '@/api/types'

export interface RoleInfo {
  value: Role
  label: string
  icon: string
  color: string
  pitch: string
}

export const ROLES: RoleInfo[] = [
  {
    value: 'admin',
    label: 'Admin',
    icon: mdiShieldCrownOutline,
    color: 'primary',
    pitch: 'Full control: team, settings, every shipment and report.',
  },
  {
    value: 'ops',
    label: 'Ops Coordinator',
    icon: mdiHeadset,
    color: 'secondary',
    pitch: 'Books shipments, runs tenders, handles exceptions.',
  },
  {
    value: 'customer',
    label: 'Customer',
    icon: mdiAccountTieOutline,
    color: 'success',
    pitch: 'Shipper portal: sees only their own cargo and documents.',
  },
  {
    value: 'carrier',
    label: 'Carrier',
    icon: mdiTruckFastOutline,
    color: 'warning',
    pitch: 'Bids on loads, runs trips, uploads proof of delivery.',
  },
]

export const ROLE_BY_VALUE = Object.fromEntries(ROLES.map((r) => [r.value, r])) as Record<Role, RoleInfo>
