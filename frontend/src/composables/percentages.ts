export function formatPercentValue(
  value: number | null | undefined,
  maximumFractionDigits = 1
): string {
  if (value == null || Number.isNaN(value)) return '--'
  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits,
    minimumFractionDigits: Number.isInteger(value) ? 0 : Math.min(maximumFractionDigits, 1)
  }).format(value)
}
