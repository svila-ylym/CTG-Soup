import type { ThemePreference } from '@/types'

const STORAGE_KEY = 'theme_preference'
const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)')
let activePreference: ThemePreference = 'system'
let listening = false

function isThemePreference(value: string | null): value is ThemePreference {
  return value === 'light' || value === 'dark' || value === 'system'
}

function resolvedDark(preference: ThemePreference): boolean {
  return preference === 'dark' || (preference === 'system' && darkModeQuery.matches)
}

function renderTheme() {
  const dark = resolvedDark(activePreference)
  document.documentElement.classList.toggle('dark', dark)
  window.dispatchEvent(new CustomEvent('themechange', {
    detail: { preference: activePreference, dark },
  }))
}

export function storedTheme(): ThemePreference {
  const value = localStorage.getItem(STORAGE_KEY)
  return isThemePreference(value) ? value : 'system'
}

export function applyTheme(preference: ThemePreference) {
  activePreference = preference
  localStorage.setItem(STORAGE_KEY, preference)
  renderTheme()
  if (!listening) {
    darkModeQuery.addEventListener('change', renderTheme)
    listening = true
  }
}
