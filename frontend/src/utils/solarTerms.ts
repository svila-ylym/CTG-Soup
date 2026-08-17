/**
 * Solar terms (二十四节气) detection and season mapping
 * API: https://api.ruseo.cn/api/lunar
 * Key: 1f845b91-caf6-4368-8217-05b93bed4b73
 */

export type Season = 'spring' | 'summer' | 'autumn' | 'winter'

export interface SolarTermInfo {
  name: string
  date: string // YYYY-MM-DD
}

export interface SolarTermResponse {
  current: string | null
  prev: string
  prev_date: string
  next: string
  next_date: string
  all_terms: SolarTermInfo[]
}

export interface LunarData {
  code: number
  msg: string
  data: {
    date: string
    solar_term: SolarTermResponse
  }
}

// Season boundaries (the 4 seasonal markers)
const SEASON_START: Record<Season, string> = {
  spring: '立春',
  summer: '立夏',
  autumn: '立秋',
  winter: '立冬',
}

// All 24 solar terms by season
const TERMS_BY_SEASON: Record<Season, string[]> = {
  spring: ['立春', '雨水', '惊蛰', '春分', '清明', '谷雨'],
  summer: ['立夏', '小满', '芒种', '夏至', '小暑', '大暑'],
  autumn: ['立秋', '处暑', '白露', '秋分', '寒露', '霜降'],
  winter: ['立冬', '小雪', '大雪', '冬至', '小寒', '大寒'],
}

// All 24 solar terms
const ALL_24_TERMS = [
  '立春', '雨水', '惊蛰', '春分', '清明', '谷雨',
  '立夏', '小满', '芒种', '夏至', '小暑', '大暑',
  '立秋', '处暑', '白露', '秋分', '寒露', '霜降',
  '立冬', '小雪', '大雪', '冬至', '小寒', '大寒',
]

// Chinese season names
const SEASON_NAMES: Record<Season, string> = {
  spring: '春季',
  summer: '夏季',
  autumn: '秋季',
  winter: '冬季',
}

// Season theme colors for CSS
const SEASON_COLORS: Record<Season, { sky: string[]; accent: string; desc: string }> = {
  spring: {
    sky: ['#c1e2e9', '#e8f2ed', '#f6f6df'],
    accent: '#f472b6',
    desc: '春 · 万物复苏',
  },
  summer: {
    sky: ['#a7e2ff', '#d9f4ff', '#fff4d6'],
    accent: '#facc15',
    desc: '夏 · 荷风送爽',
  },
  autumn: {
    sky: ['#d4a574', '#e8c49a', '#f5e0c3'],
    accent: '#f97316',
    desc: '秋 · 金风玉露',
  },
  winter: {
    sky: ['#c8d6e5', '#dfe6e9', '#f5f6fa'],
    accent: '#60a5fa',
    desc: '冬 · 瑞雪丰年',
  },
}

// Season CSS variable overrides
const SEASON_CSS_VARS: Record<Season, Record<string, string>> = {
  spring: {
    '--banner-far-mountain-0': '#9acbd2',
    '--banner-far-mountain-1': '#6b9fb4',
    '--banner-mid-mountain-0': '#68ad91',
    '--banner-mid-mountain-1': '#387b73',
    '--banner-lake-0': '#83d8df',
    '--banner-lake-1': '#3a8ec0',
    '--banner-foreground-0': '#b4d85f',
    '--banner-foreground-1': '#3c9b69',
    '--banner-lotus-leaf': '#4ade80',
    '--banner-lotus-flower': '#f9a8d4',
    '--banner-sun-color': '#ffe38b',
    '--banner-sun-glow': 'rgba(255, 227, 139, 0.13)',
  },
  summer: {
    '--banner-far-mountain-0': '#9acbd2',
    '--banner-far-mountain-1': '#6b9fb4',
    '--banner-mid-mountain-0': '#68ad91',
    '--banner-mid-mountain-1': '#387b73',
    '--banner-lake-0': '#83d8df',
    '--banner-lake-1': '#3a8ec0',
    '--banner-foreground-0': '#b4d85f',
    '--banner-foreground-1': '#3c9b69',
    '--banner-lotus-leaf': '#4ade80',
    '--banner-lotus-flower': '#f9a8d4',
    '--banner-sun-color': '#ffe38b',
    '--banner-sun-glow': 'rgba(255, 227, 139, 0.13)',
  },
  autumn: {
    '--banner-far-mountain-0': '#c4a882',
    '--banner-far-mountain-1': '#8b7355',
    '--banner-mid-mountain-0': '#b8860b',
    '--banner-mid-mountain-1': '#8b4513',
    '--banner-lake-0': '#89a8b8',
    '--banner-lake-1': '#4a6a7a',
    '--banner-foreground-0': '#d4a017',
    '--banner-foreground-1': '#8b5e3c',
    '--banner-lotus-leaf': '#d4a017',
    '--banner-lotus-flower': '#ff6b6b',
    '--banner-sun-color': '#ffb347',
    '--banner-sun-glow': 'rgba(255, 180, 70, 0.15)',
  },
  winter: {
    '--banner-far-mountain-0': '#d5dbe0',
    '--banner-far-mountain-1': '#a8b2bc',
    '--banner-mid-mountain-0': '#bcc5cd',
    '--banner-mid-mountain-1': '#88929c',
    '--banner-lake-0': '#b8c6d4',
    '--banner-lake-1': '#6a7a8a',
    '--banner-foreground-0': '#d5dbe0',
    '--banner-foreground-1': '#88929c',
    '--banner-lotus-leaf': '#88929c',
    '--banner-lotus-flower': '#d5dbe0',
    '--banner-sun-color': '#e8eef5',
    '--banner-sun-glow': 'rgba(232, 238, 245, 0.1)',
  },
}

// Constellation/star for night sky per season
const SEASON_STARS: Record<Season, string> = {
  spring: '北斗七星 · 春',
  summer: '银河 · 夏季大三角',
  autumn: '仙后座 · 秋',
  winter: '猎户座 · 冬',
}

/**
 * Fetch solar term data from the API
 */
export async function fetchSolarTerms(date?: string): Promise<LunarData> {
  const params: Record<string, string> = {
    key: '1f845b91-caf6-4368-8217-05b93bed4b73',
  }
  if (date) params.date = date

  const res = await fetch(
    `https://api.ruseo.cn/api/lunar?${new URLSearchParams(params)}`,
    { signal: AbortSignal.timeout(8000) },
  )
  if (!res.ok) throw new Error(`Solar terms API error: ${res.status}`)
  return res.json() as Promise<LunarData>
}

/**
 * Determine season from a solar term name
 */
export function seasonFromTerm(term: string): Season {
  const lower = term.toLowerCase()
  if (lower.includes('春')) return 'spring'
  if (lower.includes('夏')) return 'summer'
  if (lower.includes('秋')) return 'autumn'
  if (lower.includes('冬')) return 'winter'
  // If it's something like DA_XUE, check by position
  const idx = ALL_24_TERMS.indexOf(term)
  if (idx >= 0 && idx < 6) return 'spring'
  if (idx >= 6 && idx < 12) return 'summer'
  if (idx >= 12 && idx < 18) return 'autumn'
  if (idx >= 18) return 'winter'
  return 'summer' // default
}

/**
 * Determine season from a date by checking which seasonal marker we're past
 */
export function seasonFromDate(terms: SolarTermInfo[]): Season {
  const today = new Date()
  const todayMs = today.getTime()

  // Find the most recent seasonal marker (立春, 立夏, 立秋, 立冬)
  const markers = [
    { name: '立春', season: 'spring' as Season },
    { name: '立夏', season: 'summer' as Season },
    { name: '立秋', season: 'autumn' as Season },
    { name: '立冬', season: 'winter' as Season },
  ]

  // Get all seasonal marker dates from the terms list
  const markerDates = terms
    .filter(t => markers.some(m => m.name === t.name))
    .map(t => ({
      name: t.name,
      date: new Date(t.date),
      season: markers.find(m => m.name === t.name)!.season,
    }))
    .sort((a, b) => a.date.getTime() - b.date.getTime())

  // Find the most recent marker that's before or on today
  let currentSeason: Season = 'winter' // default to winter before 立春
  for (const marker of markerDates) {
    if (marker.date.getTime() <= todayMs) {
      currentSeason = marker.season
    }
  }

  return currentSeason
}

/**
 * Get human-readable label for a solar term
 */
export function getTermLabel(termName: string): string {
  const labels: Record<string, string> = {
    '立春': '立春 · 东风解冻',
    '雨水': '雨水 · 獭祭鱼',
    '惊蛰': '惊蛰 · 桃始华',
    '春分': '春分 · 玄鸟至',
    '清明': '清明 · 桐始华',
    '谷雨': '谷雨 · 萍始生',
    '立夏': '立夏 · 蝼蝈鸣',
    '小满': '小满 · 苦菜秀',
    '芒种': '芒种 · 螳螂生',
    '夏至': '夏至 · 鹿角解',
    '小暑': '小暑 · 温风至',
    '大暑': '大暑 · 腐草为萤',
    '立秋': '立秋 · 凉风至',
    '处暑': '处暑 · 鹰乃祭鸟',
    '白露': '白露 · 鸿雁来',
    '秋分': '秋分 · 雷始收声',
    '寒露': '寒露 · 鸿雁来宾',
    '霜降': '霜降 · 豺乃祭兽',
    '立冬': '立冬 · 水始冰',
    '小雪': '小雪 · 虹藏不见',
    '大雪': '大雪 · 鹖鴠不鸣',
    '冬至': '冬至 · 蚯蚓结',
    '小寒': '小寒 · 雁北乡',
    '大寒': '大寒 · 鸡始乳',
  }
  return labels[termName] || termName
}

export {
  SEASON_START,
  TERMS_BY_SEASON,
  ALL_24_TERMS,
  SEASON_NAMES,
  SEASON_COLORS,
  SEASON_CSS_VARS,
  SEASON_STARS,
}