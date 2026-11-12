// SkidFx Android release identifier.
// Update this when preparing each new GitHub release.
export const SKIDFX_VERSION = '2.1.5-android.3'

const parseVersion = (tag: string): number[] | null => {
  const match = /^v?(\d+)\.(\d+)\.(\d+)-android\.(\d+)$/.exec(tag)
  return match ? match.slice(1).map(Number) : null
}

export const compareSkidFxVersions = (a: string, b: string): number => {
  const left = parseVersion(a)
  const right = parseVersion(b)

  if (!left || !right) return 0

  for (let i = 0; i < 4; i++) {
    if (left[i] !== right[i]) return left[i] > right[i] ? 1 : -1
  }

  return 0
}
