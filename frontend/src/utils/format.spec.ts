import { describe, expect, it } from 'vitest'
import { formatMoney, formatNumber, initials } from './format'

describe('format', () => {
  it('builds initials from up to two words', () => {
    expect(initials('Gulfstream Freight Forwarders')).toBe('GF')
    expect(initials('  ')).toBe('?')
  })

  it('formats API decimal strings as currency', () => {
    expect(formatMoney('1250.5', 'USD')).toBe('$1,250.50')
    expect(formatMoney(null)).toBe('—')
  })

  it('formats quantities with units', () => {
    expect(formatNumber('12000.125', 'kg')).toBe('12,000.13 kg')
    expect(formatNumber('')).toBe('—')
  })
})
