import type { CSSProperties } from 'vue'

const HEX_COLOR = /^#[0-9A-F]{6}$/

export function competitionBorderStyle(colors?: string[]): CSSProperties {
  const normalized = [...new Set(
    (colors || [])
      .map(color => color.toUpperCase())
      .filter(color => HEX_COLOR.test(color)),
  )]
  if (!normalized.length) return {}
  if (normalized.length === 1) return { borderColor: normalized[0] }
  return {
    borderColor: 'transparent',
    backgroundImage: [
      'linear-gradient(var(--competition-card-bg), var(--competition-card-bg))',
      `linear-gradient(135deg, ${normalized.join(', ')})`,
    ].join(', '),
    backgroundOrigin: 'border-box',
    backgroundClip: 'padding-box, border-box',
  }
}
