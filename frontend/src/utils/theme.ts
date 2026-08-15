import type { ThemePreference } from '@/types'

const STORAGE_KEY = 'app-theme'
const LEGACY_STORAGE_KEY = 'theme_preference'
const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)')
let activePreference: ThemePreference = 'system'
let listening = false
let renderedDark: boolean | null = null
let transitionId = 0
let fallbackTimer: number | null = null

type ThemeTransitionDocument = Document & {
  startViewTransition?: (callback: () => void) => { finished: Promise<void> }
}

function isThemePreference(value: string | null): value is ThemePreference {
  return value === 'light' || value === 'dark' || value === 'system'
}

function resolvedDark(preference: ThemePreference): boolean {
  return preference === 'dark' || (preference === 'system' && darkModeQuery.matches)
}

function renderTheme() {
  const dark = resolvedDark(activePreference)
  const currentTransitionId = ++transitionId
  const shouldAnimate = renderedDark !== null
    && renderedDark !== dark
    && !window.matchMedia('(prefers-reduced-motion: reduce)').matches

  const clearFallbackTransition = () => {
    if (fallbackTimer !== null) {
      window.clearTimeout(fallbackTimer)
      fallbackTimer = null
    }
    document.documentElement.classList.remove('theme-transitioning', 'is-animating')
  }

  const commitTheme = () => {
    if (currentTransitionId !== transitionId) return
    document.documentElement.classList.toggle('dark', dark)
    window.dispatchEvent(new CustomEvent('themechange', {
      detail: { preference: activePreference, dark },
    }))
    renderedDark = dark
  }

  if (!shouldAnimate) {
    clearFallbackTransition()
    commitTheme()
    return
  }

  const transitionDocument = document as ThemeTransitionDocument
  if (transitionDocument.startViewTransition) {
    clearFallbackTransition()
    try {
      const transition = transitionDocument.startViewTransition(commitTheme)
      void transition.finished.catch(() => undefined)
      return
    } catch (error) {
      console.warn('View transition failed; using the CSS fallback.', error)
    }
  }

  clearFallbackTransition()
  document.documentElement.classList.add('theme-transitioning')
  commitTheme()
  fallbackTimer = window.setTimeout(() => {
    if (currentTransitionId === transitionId) {
      document.documentElement.classList.remove('theme-transitioning')
      fallbackTimer = null
    }
  }, 340)
}

export function storedTheme(fallback: ThemePreference = 'system'): ThemePreference {
  try {
    const appTheme = localStorage.getItem(STORAGE_KEY)
    if (appTheme === 'light' || appTheme === 'dark') return appTheme
    const legacyTheme = localStorage.getItem(LEGACY_STORAGE_KEY)
    return isThemePreference(legacyTheme) ? legacyTheme : fallback
  } catch (error) {
    console.warn('Could not access localStorage for theme setting.', error)
    return fallback
  }
}

export function applyTheme(preference: ThemePreference) {
  activePreference = preference
  try {
    localStorage.setItem(LEGACY_STORAGE_KEY, preference)
    if (preference === 'system') localStorage.removeItem(STORAGE_KEY)
    else localStorage.setItem(STORAGE_KEY, preference)
  } catch (error) {
    console.warn('Could not save theme to localStorage.', error)
  }
  renderTheme()
  if (!listening) {
    darkModeQuery.addEventListener('change', renderTheme)
    listening = true
  }
}
