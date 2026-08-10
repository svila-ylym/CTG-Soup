import type { ThemePreference } from '@/types'

const STORAGE_KEY = 'theme_preference'
const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)')
let activePreference: ThemePreference = 'system'
let listening = false
let renderedDark: boolean | null = null
let transitionId = 0

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

  const commitTheme = () => {
    if (currentTransitionId !== transitionId) return
    document.documentElement.classList.toggle('dark', dark)
    window.dispatchEvent(new CustomEvent('themechange', {
      detail: { preference: activePreference, dark },
    }))
    renderedDark = dark
  }

  const transitionDocument = document as ThemeTransitionDocument
  if (!shouldAnimate || !transitionDocument.startViewTransition) {
    commitTheme()
    return
  }

  document.documentElement.dataset.themeTransition = dark ? 'to-dark' : 'to-light'
  const transition = transitionDocument.startViewTransition(commitTheme)
  void transition.finished.then(
    () => { if (currentTransitionId === transitionId) delete document.documentElement.dataset.themeTransition },
    () => { if (currentTransitionId === transitionId) delete document.documentElement.dataset.themeTransition },
  )
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
