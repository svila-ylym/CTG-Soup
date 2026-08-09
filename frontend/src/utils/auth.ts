export function extractApiError(error: unknown, fallback: string): string {
  const detail = (error as any)?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (detail && typeof detail.message === 'string') return detail.message

  const message = (error as any)?.response?.data?.message
  return typeof message === 'string' && message.trim() ? message : fallback
}

export function safeRedirect(value: unknown): string {
  if (typeof value !== 'string') return '/'
  if (!value.startsWith('/') || value.startsWith('//')) return '/'
  return value
}
