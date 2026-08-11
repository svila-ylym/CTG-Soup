export interface TextLinkSegment {
  type: 'text' | 'link'
  text: string
  href?: string
}

const URL_CANDIDATE = /https?:\/\/[^\s<>"'`,，。！？；：、…]+/gi
const ASCII_BOUNDARY = /[A-Za-z0-9_@:\/]/
const TRAILING_PUNCTUATION = /[.,!?;:，。！？；：、…]+$/u
const BRACKETS: Array<[string, string]> = [
  ['(', ')'],
  ['[', ']'],
  ['{', '}'],
]

function hasUnmatchedTrailingBracket(value: string): boolean {
  const pair = BRACKETS.find(([, closing]) => value.endsWith(closing))
  if (!pair) return false
  const [opening, closing] = pair
  let balance = 0
  for (const character of value) {
    if (character === opening) balance += 1
    if (character === closing) balance -= 1
  }
  return balance < 0
}

function trimCandidate(raw: string): string {
  let candidate = raw
  let previous = ''
  while (candidate && candidate !== previous) {
    previous = candidate
    candidate = candidate.replace(TRAILING_PUNCTUATION, '')
    while (candidate && hasUnmatchedTrailingBracket(candidate)) {
      candidate = candidate.slice(0, -1)
    }
  }
  return candidate
}

function isValidHostname(hostname: string): boolean {
  if (!hostname || hostname === '.' || hostname.includes('..')) return false
  if (hostname.startsWith('[') && hostname.endsWith(']')) {
    return /^[0-9A-Fa-f:.]+$/u.test(hostname.slice(1, -1))
  }
  const normalized = hostname.endsWith('.') ? hostname.slice(0, -1) : hostname
  if (!normalized) return false
  return normalized.split('.').every((label) => (
    Boolean(label)
    && !label.startsWith('-')
    && !label.endsWith('-')
    && /^[A-Za-z0-9-]+$/u.test(label)
  ))
}

function validateCandidate(candidate: string): boolean {
  if (!candidate) return false
  try {
    const parsed = new URL(candidate)
    return (
      (parsed.protocol === 'http:' || parsed.protocol === 'https:')
      && isValidHostname(parsed.hostname)
    )
  } catch {
    return false
  }
}

function appendText(segments: TextLinkSegment[], text: string): void {
  if (!text) return
  const previous = segments[segments.length - 1]
  if (previous?.type === 'text') previous.text += text
  else segments.push({ type: 'text', text })
}

export function linkifyText(text: string): TextLinkSegment[] {
  if (!text) return []
  const segments: TextLinkSegment[] = []
  let cursor = 0
  for (const match of text.matchAll(URL_CANDIDATE)) {
    const raw = match[0]
    const start = match.index ?? 0
    const previousCharacter = start > 0 ? text[start - 1] : ''
    if (previousCharacter && ASCII_BOUNDARY.test(previousCharacter)) continue

    const candidate = trimCandidate(raw)
    if (!validateCandidate(candidate)) continue
    appendText(segments, text.slice(cursor, start))
    segments.push({ type: 'link', text: candidate, href: candidate })
    cursor = start + candidate.length
  }
  appendText(segments, text.slice(cursor))
  return segments.length ? segments : [{ type: 'text', text }]
}
