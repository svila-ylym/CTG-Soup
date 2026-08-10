export type DraftKind = 'soup' | 'post'

const DRAFT_VERSION = 1

interface DraftEnvelope<T> {
  version: number
  saved_at: string
  data: T
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function draftStorageKey(
  kind: DraftKind,
  uid: number | string | null | undefined,
): string | null {
  if (uid === null || uid === undefined) return null
  const normalizedUid = String(uid).trim()
  if (!/^[1-9]\d*$/.test(normalizedUid)) return null
  return `ctg:draft:v${DRAFT_VERSION}:${kind}:${normalizedUid}`
}

export function readDraft<T>(
  key: string | null,
  validate: (value: unknown) => value is T,
): T | null {
  if (!key) return null
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return null
    const envelope: unknown = JSON.parse(raw)
    if (
      !isRecord(envelope)
      || envelope.version !== DRAFT_VERSION
      || typeof envelope.saved_at !== 'string'
      || !validate(envelope.data)
    ) {
      removeDraft(key)
      return null
    }
    return envelope.data
  } catch {
    removeDraft(key)
    return null
  }
}

export function writeDraft<T>(key: string | null, data: T): void {
  if (!key) return
  try {
    const envelope: DraftEnvelope<T> = {
      version: DRAFT_VERSION,
      saved_at: new Date().toISOString(),
      data,
    }
    localStorage.setItem(key, JSON.stringify(envelope))
  } catch {
    // Storage availability must not affect editing or publishing.
  }
}

export function removeDraft(key: string | null): void {
  if (!key) return
  try {
    localStorage.removeItem(key)
  } catch {
    // Storage availability must not affect editing or publishing.
  }
}
