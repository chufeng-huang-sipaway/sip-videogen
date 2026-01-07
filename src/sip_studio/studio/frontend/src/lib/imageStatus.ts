import type { ImageStatusEntry } from './bridge'

function normalizeSlashes(path: string): string {
  return path.replaceAll('\\', '/')
}

export function normalizeAssetPath(path: string): string {
  if (!path) return ''
  const normalized = normalizeSlashes(path)

  const lower = normalized.toLowerCase()
  const assetsPrefix = 'assets/'
  if (lower.startsWith(assetsPrefix)) {
    return normalized.slice(assetsPrefix.length)
  }

  const marker = '/assets/'
  const index = lower.lastIndexOf(marker)
  if (index >= 0) {
    return normalized.slice(index + marker.length)
  }

  return normalized
}

export function buildStatusByAssetPath(entries: ImageStatusEntry[]): Map<string, ImageStatusEntry> {
  const map = new Map<string, ImageStatusEntry>()

  for (const entry of entries) {
    const currentKey = normalizeAssetPath(entry.currentPath)
    if (currentKey && !map.has(currentKey)) map.set(currentKey, entry)

    const originalKey = normalizeAssetPath(entry.originalPath)
    if (originalKey && !map.has(originalKey)) map.set(originalKey, entry)
  }

  return map
}

