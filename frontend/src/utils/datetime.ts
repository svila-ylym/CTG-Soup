const TIMEZONE_SUFFIX = /(?:Z|[+-]\d{2}:\d{2})$/i
const CHINA_TIMEZONE = 'Asia/Shanghai'

const chinaDateKeyFormatter = new Intl.DateTimeFormat('en-CA', {
  timeZone: CHINA_TIMEZONE,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})

const chinaMessageTimeFormatter = new Intl.DateTimeFormat('zh-CN', {
  timeZone: CHINA_TIMEZONE,
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
  hourCycle: 'h23',
})

const chinaMessageDateFormatter = new Intl.DateTimeFormat('zh-CN', {
  timeZone: CHINA_TIMEZONE,
  month: 'numeric',
  day: 'numeric',
})

export function parseUtcDateTime(value: string): Date {
  const normalized = TIMEZONE_SUFFIX.test(value) ? value : `${value}Z`
  return new Date(normalized)
}

export function chinaLocalDateTimeToUtcIso(value: string): string {
  const normalized = value.length === 16 ? `${value}:00` : value
  const date = new Date(`${normalized}+08:00`)
  if (Number.isNaN(date.getTime())) throw new Error('invalid datetime')
  return date.toISOString()
}

export function formatChinaDateTime(value: string): string {
  const date = parseUtcDateTime(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(date)
}

export function formatChinaMessageTime(value: string): string {
  const date = parseUtcDateTime(value)
  if (Number.isNaN(date.getTime())) return value
  const today = new Date()
  return chinaDateKeyFormatter.format(date) === chinaDateKeyFormatter.format(today)
    ? chinaMessageTimeFormatter.format(date)
    : chinaMessageDateFormatter.format(date)
}
