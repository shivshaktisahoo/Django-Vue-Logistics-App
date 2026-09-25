export function initials(name: string): string {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((w) => w[0]!.toUpperCase())
      .join('') || '?'
  )
}

const money = new Map<string, Intl.NumberFormat>()

/** Amounts arrive from the API as decimal strings. */
export function formatMoney(value: string | number | null | undefined, currency = 'USD'): string {
  if (value === null || value === undefined || value === '') return '—'
  if (!money.has(currency)) money.set(currency, new Intl.NumberFormat('en-US', { style: 'currency', currency }))
  return money.get(currency)!.format(Number(value))
}

const num = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 })
export function formatNumber(value: string | number | null | undefined, unit = ''): string {
  if (value === null || value === undefined || value === '') return '—'
  return `${num.format(Number(value))}${unit ? ` ${unit}` : ''}`
}

const dateFmt = new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
const dateTimeFmt = new Intl.DateTimeFormat('en-GB', {
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
})

/** Timestamps are UTC ISO strings; shown in the viewer's local time. */
export function formatDate(iso: string | null | undefined): string {
  return iso ? dateFmt.format(new Date(iso)) : '—'
}
export function formatDateTime(iso: string | null | undefined): string {
  return iso ? dateTimeFmt.format(new Date(iso)) : '—'
}

const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return '—'
  const seconds = (new Date(iso).getTime() - Date.now()) / 1000
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
  ]
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return rtf.format(Math.round(seconds / size), unit)
  }
  return 'just now'
}
