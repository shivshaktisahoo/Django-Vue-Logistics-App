import { describe, expect, it } from 'vitest'
import type { PackageLine } from '@/api/types'
import { cargoTotals, isValidContainerNumber } from './freight'

const line = (over: Partial<PackageLine>): PackageLine => ({
  kind: 'carton',
  container_type: '',
  container_number: '',
  seal_number: '',
  quantity: 1,
  description: '',
  weight_kg: '0',
  length_cm: null,
  width_cm: null,
  height_cm: null,
  ...over,
})

describe('freight', () => {
  it('validates ISO 6346 check digits like the server', () => {
    expect(isValidContainerNumber('CSQU3054383')).toBe(true)
    expect(isValidContainerNumber('csqu 305438 3')).toBe(true)
    expect(isValidContainerNumber('CSQU3054384')).toBe(false)
    expect(isValidContainerNumber('CSQA3054383')).toBe(false)
  })

  it('uses volumetric weight when cargo is light and bulky (air 1:6000)', () => {
    const t = cargoTotals('air', [line({ quantity: 10, weight_kg: '50', length_cm: '60', width_cm: '40', height_cm: '50' })])
    expect(t.cbm).toBeCloseTo(1.2)
    expect(t.chargeable).toBeCloseTo(200)
  })

  it('uses actual weight for dense cargo', () => {
    const t = cargoTotals('road', [line({ quantity: 2, weight_kg: '2000', length_cm: '120', width_cm: '100', height_cm: '100' })])
    expect(t.chargeable).toBe(2000)
  })
})
