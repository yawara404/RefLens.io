import type { BookmarkItem, FolderItem } from '~/types'
import { folderColorByName } from '~/utils/folders'

export type BookmarkSortOrder =
  | 'newest'
  | 'oldest'
  | 'color_hue'
  | 'color_bright'
  | 'color_dark'
  | 'folder_color'
  | 'title'
  | 'author'

export const BOOKMARK_SORT_OPTIONS: { id: BookmarkSortOrder; label: string }[] = [
  { id: 'newest', label: '追加が新しい順' },
  { id: 'oldest', label: '追加が古い順' },
  { id: 'color_hue', label: 'カラー順（色相スペクトル）' },
  { id: 'color_bright', label: 'カラー順（明るい順）' },
  { id: 'color_dark', label: 'カラー順（暗い順）' },
  { id: 'folder_color', label: 'フォルダカラー順' },
  { id: 'title', label: 'タイトル順' },
  { id: 'author', label: '作者名順' },
]

/* ------------------------------------------------------------------ *
 * 色
 * ------------------------------------------------------------------ */

export function hexToRgb(hex: string): [number, number, number] | null {
  const clean = (hex || '').trim().replace(/^#/, '')
  if (/^[0-9a-f]{3}$/i.test(clean)) {
    return [
      parseInt(clean[0] + clean[0], 16),
      parseInt(clean[1] + clean[1], 16),
      parseInt(clean[2] + clean[2], 16),
    ]
  }
  if (!/^[0-9a-f]{6}$/i.test(clean)) return null
  return [
    parseInt(clean.slice(0, 2), 16),
    parseInt(clean.slice(2, 4), 16),
    parseInt(clean.slice(4, 6), 16),
  ]
}

export function rgbToHsl(r: number, g: number, b: number): { h: number; s: number; l: number } {
  const rn = r / 255
  const gn = g / 255
  const bn = b / 255
  const max = Math.max(rn, gn, bn)
  const min = Math.min(rn, gn, bn)
  const l = (max + min) / 2
  let h = 0
  let s = 0

  if (max !== min) {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    switch (max) {
      case rn:
        h = (gn - bn) / d + (gn < bn ? 6 : 0)
        break
      case gn:
        h = (bn - rn) / d + 2
        break
      default:
        h = (rn - gn) / d + 4
        break
    }
    h *= 60
  }
  return { h, s, l }
}

/** 人間の視覚特性に重み付けしたRGB色差（0〜765程度） */
export function colorDistance(hexA: string, hexB: string): number {
  const a = hexToRgb(hexA)
  const b = hexToRgb(hexB)
  if (!a || !b) return 999
  const rMean = (a[0] + b[0]) / 2
  const dr = a[0] - b[0]
  const dg = a[1] - b[1]
  const db = a[2] - b[2]
  return Math.sqrt(
    (2 + rMean / 256) * dr * dr +
      4 * dg * dg +
      (2 + (255 - rMean) / 256) * db * db
  )
}

/** ブックマークのカラーパレット（AI解析が無ければフォルダカラーで代用） */
export function bookmarkPalette(b: BookmarkItem, folders: FolderItem[]): string[] {
  const palette = b.ai_analysis?.palette?.filter(hex => !!hexToRgb(hex)) || []
  if (palette.length) return palette
  return [folderColorByName(folders, b.folder_name)]
}

/** 指定カラーとブックマークのパレット間の最小色差 */
export function bookmarkMinColorDistance(
  b: BookmarkItem,
  targetHex: string,
  folders: FolderItem[] = [],
): number {
  let min = 999
  for (const hex of bookmarkPalette(b, folders)) {
    const dist = colorDistance(hex, targetHex)
    if (dist < min) min = dist
  }
  return min
}

/** 代表色から色相・輝度・彩度を算出（色順ソート用） */
export function bookmarkColorMetrics(
  b: BookmarkItem,
  folders: FolderItem[] = [],
): { hue: number; luminance: number; saturation: number } {
  const palette = bookmarkPalette(b, folders)
  // 彩度がある色を優先して代表色にする（無彩色ばかりの場合は先頭色）
  let bestHsl = { h: 360, s: 0, l: 0.5 }
  let bestLum = 0.5
  for (let i = 0; i < palette.length; i++) {
    const rgb = hexToRgb(palette[i])
    if (!rgb) continue
    const hsl = rgbToHsl(rgb[0], rgb[1], rgb[2])
    const lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255
    if (i === 0) {
      bestHsl = hsl
      bestLum = lum
    }
    if (hsl.s > bestHsl.s + 0.12) {
      bestHsl = hsl
    }
  }
  // 彩度が極端に低い（モノクロ/グレー）は色相末尾にまとめる
  const effectiveHue = bestHsl.s < 0.08 ? 360 + bestLum * 10 : bestHsl.h
  return { hue: effectiveHue, luminance: bestLum, saturation: bestHsl.s }
}

/* ------------------------------------------------------------------ *
 * 検索
 * ------------------------------------------------------------------ */

/** 検索対象テキストを1つの文字列にまとめる（毎回のテンプレート連結を避ける） */
export function buildBookmarkCorpus(b: BookmarkItem): string {
  return [
    b.title,
    b.author_name || '',
    b.source_url || '',
    b.folder_name || '',
    (b.ai_analysis?.tags || []).join(' '),
    b.ai_analysis?.composition || '',
    b.ai_analysis?.lighting || '',
    (b.ai_analysis?.palette || []).join(' '),
  ]
    .join(' ')
    .toLowerCase()
}

/* ------------------------------------------------------------------ *
 * タグ集計
 * ------------------------------------------------------------------ */

export function countAiTags(bookmarks: BookmarkItem[]): Map<string, number> {
  const counts = new Map<string, number>()
  for (const b of bookmarks) {
    for (const tag of b.ai_analysis?.tags || []) {
      const trimmed = tag.trim()
      if (trimmed) counts.set(trimmed, (counts.get(trimmed) || 0) + 1)
    }
  }
  return counts
}

/** 頻出AIタグ（出現回数の多い順） */
export function topAiTags(
  bookmarks: BookmarkItem[],
  limit = 10,
): { tag: string; count: number }[] {
  return [...countAiTags(bookmarks).entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([tag, count]) => ({ tag, count }))
}

/* ------------------------------------------------------------------ *
 * ソート
 * ------------------------------------------------------------------ */

export interface BookmarkSortContext {
  folders?: FolderItem[]
  /** 指定色に近い順（検索画面のカラー選択時） */
  targetColor?: string | null
}

const addedAt = (b: BookmarkItem) => (b.created_at ? Date.parse(b.created_at) : 0)

/**
 * ブックマークの並び替え。
 *
 * 色順は比較のたびにパレットを解析すると O(n log n × palette) になるため、
 * 先に1回だけ指標を計算してから比較する。
 */
export function sortBookmarks(
  list: BookmarkItem[],
  order: BookmarkSortOrder,
  context: BookmarkSortContext = {},
): BookmarkItem[] {
  const folders = context.folders || []
  const result = [...list]

  if (context.targetColor) {
    const targetColor = context.targetColor
    const distances = new Map<string, number>()
    const distanceOf = (b: BookmarkItem) => {
      let distance = distances.get(b.id)
      if (distance === undefined) {
        distance = bookmarkMinColorDistance(b, targetColor, folders)
        distances.set(b.id, distance)
      }
      return distance
    }
    return result.sort((a, b) => {
      const diff = distanceOf(a) - distanceOf(b)
      return Math.abs(diff) > 0.5 ? diff : addedAt(b) - addedAt(a)
    })
  }

  const metrics = new Map<string, { hue: number; luminance: number; saturation: number }>()
  const metricOf = (b: BookmarkItem) => {
    let value = metrics.get(b.id)
    if (!value) {
      value = bookmarkColorMetrics(b, folders)
      metrics.set(b.id, value)
    }
    return value
  }

  switch (order) {
    case 'oldest':
      return result.sort((a, b) => addedAt(a) - addedAt(b))
    case 'color_hue':
      return result.sort((a, b) => {
        const ma = metricOf(a)
        const mb = metricOf(b)
        return ma.hue - mb.hue || mb.luminance - ma.luminance
      })
    case 'color_bright':
      return result.sort((a, b) => {
        const ma = metricOf(a)
        const mb = metricOf(b)
        return mb.luminance - ma.luminance || ma.hue - mb.hue
      })
    case 'color_dark':
      return result.sort((a, b) => {
        const ma = metricOf(a)
        const mb = metricOf(b)
        return ma.luminance - mb.luminance || ma.hue - mb.hue
      })
    case 'folder_color': {
      const folderHue = new Map<string, number>()
      const hueOf = (b: BookmarkItem) => {
        const name = b.folder_name || ''
        let hue = folderHue.get(name)
        if (hue === undefined) {
          const rgb = hexToRgb(folderColorByName(folders, name)) || [99, 102, 241]
          hue = rgbToHsl(rgb[0], rgb[1], rgb[2]).h
          folderHue.set(name, hue)
        }
        return hue
      }
      return result.sort(
        (a, b) =>
          hueOf(a) - hueOf(b) ||
          (a.folder_name || '').localeCompare(b.folder_name || '', 'ja'),
      )
    }
    case 'title':
      return result.sort((a, b) => a.title.localeCompare(b.title, 'ja'))
    case 'author':
      return result.sort((a, b) => (a.author_name || '').localeCompare(b.author_name || '', 'ja'))
    default:
      return result.sort((a, b) => addedAt(b) - addedAt(a))
  }
}

