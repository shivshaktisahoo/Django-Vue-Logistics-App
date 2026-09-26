import { http } from '@/api/http'

/**
 * Documents are served by an authenticated endpoint, so a plain <a href> won't do:
 * fetch the bytes with the session, then hand the browser an object URL.
 */
export async function openDocument(id: string, fileName: string, inline = true) {
  const { data } = await http.get<Blob>(`/documents/${id}/download/`, { responseType: 'blob', params: inline ? { inline: 1 } : {} })
  const url = URL.createObjectURL(data)
  if (inline) {
    window.open(url, '_blank', 'noopener')
  } else {
    const a = document.createElement('a')
    a.href = url
    a.download = fileName
    a.click()
  }
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

/** "in 3 h 20 m" / "2 h ago": for bidding deadlines. */
export function countdown(iso: string, now = Date.now()): string {
  const diff = new Date(iso).getTime() - now
  const abs = Math.abs(diff)
  const d = Math.floor(abs / 86_400_000)
  const h = Math.floor((abs % 86_400_000) / 3_600_000)
  const m = Math.floor((abs % 3_600_000) / 60_000)
  const text = d ? `${d} d ${h} h` : h ? `${h} h ${m} m` : `${m} m`
  return diff >= 0 ? `in ${text}` : `${text} ago`
}
