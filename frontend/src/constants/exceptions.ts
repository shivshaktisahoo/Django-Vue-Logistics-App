import { mdiAlertDecagramOutline, mdiAlertOctagonOutline, mdiAlertOutline, mdiInformationOutline } from '@mdi/js'
import type { ExceptionSeverity } from '@/api/types'

export const SEVERITY: Record<ExceptionSeverity, { label: string; color: string; icon: string }> = {
  critical: { label: 'Critical', color: 'error', icon: mdiAlertOctagonOutline },
  high: { label: 'High', color: 'deep-orange', icon: mdiAlertDecagramOutline },
  medium: { label: 'Medium', color: 'warning', icon: mdiAlertOutline },
  low: { label: 'Low', color: 'info', icon: mdiInformationOutline },
}
