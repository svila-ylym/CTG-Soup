import type { SoupColor, SoupGenre } from '@/types'

const badgeBase = 'inline-flex items-center rounded-md border px-2 py-1 text-xs font-semibold'

export function genreBadgeClass(genre: SoupGenre): string {
  const colors: Record<SoupGenre, string> = {
    本格: 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-800 dark:bg-sky-950/50 dark:text-sky-300',
    变格: 'border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-800 dark:bg-violet-950/50 dark:text-violet-300',
    鳖汤: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300',
    未分类: 'border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300',
  }
  return `${badgeBase} ${colors[genre] || colors['未分类']}`
}

export function soupColorBadgeClass(color: SoupColor): string {
  const colors: Record<SoupColor, string> = {
    清汤: 'border-cyan-200 bg-cyan-50 text-cyan-700 dark:border-cyan-800 dark:bg-cyan-950/50 dark:text-cyan-300',
    红汤: 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-800 dark:bg-rose-950/50 dark:text-rose-300',
    黑汤: 'border-slate-700 bg-slate-800 text-white dark:border-slate-500 dark:bg-slate-700 dark:text-slate-100',
    未分类: 'border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300',
  }
  return `${badgeBase} ${colors[color] || colors['未分类']}`
}
