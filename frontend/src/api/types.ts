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
