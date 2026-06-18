/** 小數報酬率 → 帶號百分比字串，例如 0.123 → "+12.3%" */
export function pct(x: number | null | undefined, digits = 1): string {
  if (x == null) return '—'
  return `${x >= 0 ? '+' : ''}${(x * 100).toFixed(digits)}%`
}

/** 0~1 → 百分比（不帶號），例如 0.62 → "62%" */
export function rate(x: number | null | undefined, digits = 0): string {
  if (x == null) return '—'
  return `${(x * 100).toFixed(digits)}%`
}

export function retColor(x: number | null | undefined): string {
  if (x == null) return '#718096'
  return x >= 0 ? '#68d391' : '#fc8181'
}
