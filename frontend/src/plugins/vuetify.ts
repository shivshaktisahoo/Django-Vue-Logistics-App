import 'vuetify/styles'
import { createVuetify, type ThemeDefinition } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'
import { storage } from '@/utils/storage'

const light: ThemeDefinition = {
  dark: false,
  colors: {
    background: '#F3F6FB',
    surface: '#FFFFFF',
    'surface-bright': '#FFFFFF',
    'surface-variant': '#EAF0F8',
    'on-surface-variant': '#344256',
    primary: '#1D4ED8',
    'primary-darken-1': '#1E40AF',
    secondary: '#0891B2',
    accent: '#14B8A6',
    success: '#16A34A',
    warning: '#D97706',
    error: '#DC2626',
    info: '#0284C7',
  },
  variables: {
    'border-color': '#0C1F3A',
    'border-opacity': 0.09,
    'medium-emphasis-opacity': 0.64,
  },
}

const dark: ThemeDefinition = {
  dark: true,
  colors: {
    background: '#070D18',
    surface: '#0F1726',
    'surface-bright': '#162033',
    'surface-variant': '#172236',
    'on-surface-variant': '#C5D0E0',
    primary: '#60A5FA',
    'primary-darken-1': '#3B82F6',
    secondary: '#22D3EE',
    accent: '#2DD4BF',
    success: '#4ADE80',
    warning: '#FBBF24',
    error: '#F87171',
    info: '#38BDF8',
  },
  variables: {
    'border-color': '#FFFFFF',
    'border-opacity': 0.08,
  },
}

export function preferredTheme(): 'light' | 'dark' {
  const saved = storage.get('cp-theme')
  if (saved === 'light' || saved === 'dark') return saved
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export default createVuetify({
  icons: { defaultSet: 'mdi', aliases, sets: { mdi } },
  theme: { defaultTheme: preferredTheme(), themes: { light, dark } },
  defaults: {
    global: { ripple: true },
    VBtn: { rounded: 'lg', class: 'cp-btn' },
    VTextField: { variant: 'outlined', density: 'comfortable', color: 'primary', rounded: 'lg' },
    VSelect: { variant: 'outlined', density: 'comfortable', color: 'primary', rounded: 'lg' },
    VAutocomplete: { variant: 'outlined', density: 'comfortable', color: 'primary', rounded: 'lg' },
    VCombobox: { variant: 'outlined', density: 'comfortable', color: 'primary', rounded: 'lg' },
    VTextarea: { variant: 'outlined', density: 'comfortable', color: 'primary', rows: 2, rounded: 'lg' },
    VCard: { rounded: 'xl', elevation: 0 },
    VChip: { rounded: 'lg' },
    VTooltip: { location: 'bottom' },
  },
})
