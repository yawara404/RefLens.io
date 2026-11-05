<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import {
  Home,
  Plus,
  Instagram,
  Compass,
  Layers,
  Bookmark,
  Check,
  Search,
  LayoutGrid,
  List,
  ExternalLink,
  Globe,
  Upload,
  ArrowUpDown,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  GripVertical,
  Lock,
  FolderOpen,
  Sparkles,
  Palette,
  RotateCcw,
  X,
} from 'lucide-vue-next'
import AppHeader from '~/components/ui/AppHeader.vue'
import MobileNavLinks from '~/components/ui/MobileNavLinks.vue'
import QuickLookModal from '~/components/browser/QuickLookModal.vue'
import BookmarkActionsMenu from '~/components/ui/BookmarkActionsMenu.vue'
import FolderActionsMenu from '~/components/ui/FolderActionsMenu.vue'
import type { BookmarkItem, FolderItem } from '~/types'
import { useBoardStore } from '~/stores/boardStore'
import { useMediaUrl } from '~/composables/useMediaUrl'
import { useToast } from '~/composables/useToast'
import { useImageProcessor } from '~/composables/useImageProcessor'
import { useMobileNav } from '~/composables/useMobileNav'

const boardStore = useBoardStore()
const toast = useToast()
const { resolveMediaUrl } = useMediaUrl()
const { copyToClipboard, extractImagesFromDataTransfer } = useImageProcessor()
const { isOpen: isMobileSidebarOpen } = useMobileNav()

/**
 * Manager の 3 構成ナビゲーション:
 * - home: ホーム（ブックマークフォルダダッシュボード）
 * - search: 検索（スマート総合検索）
 * - library: ライブラリ（ブックマーク一覧）
 */
type ManagerSection = 'home' | 'search' | 'library'
const activeSection = ref<ManagerSection>('home')

const inputDropUrl = ref('')
const isDropping = ref(false)
const isDraggingFiles = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const cardViewRef = ref<HTMLElement | null>(null)
const smartSearchInputRef = ref<HTMLInputElement | null>(null)

const searchQuery = ref('')
const selectedSource = ref<'all' | 'pixiv' | 'instagram' | 'web_bookmark' | 'local_upload'>('all')
const selectedFolder = ref<string | null>(null)
const viewMode = ref<'grid' | 'list'>('grid')

const showNewFolder = ref(false)
const newFolderName = ref('')
const newFolderColor = ref('#6366f1')
const folderQuery = ref('')
const libraryFolderQuery = ref('')
const libraryFolderScrollRef = ref<HTMLElement | null>(null)
const selectedFolderColorFilter = ref<string | null>(null)

const FOLDER_COLORS = [
  { hex: '#6366f1', label: 'インディゴ' },
  { hex: '#3b82f6', label: 'ブルー' },
  { hex: '#06b6d4', label: 'シアン' },
  { hex: '#10b981', label: 'エメラルド' },
  { hex: '#84cc16', label: 'ライム' },
  { hex: '#f59e0b', label: 'アンバー' },
  { hex: '#f97316', label: 'オレンジ' },
  { hex: '#ef4444', label: 'レッド' },
  { hex: '#ec4899', label: 'ピンク' },
  { hex: '#a855f7', label: 'パープル' },
] as const

const COLOR_SEARCH_PRESETS = [
  { hex: '#ef4444', label: 'レッド' },
  { hex: '#f97316', label: 'オレンジ' },
  { hex: '#eab308', label: 'イエロー' },
  { hex: '#10b981', label: 'グリーン' },
  { hex: '#06b6d4', label: 'シアン' },
  { hex: '#3b82f6', label: 'ブルー' },
  { hex: '#6366f1', label: 'インディゴ' },
  { hex: '#a855f7', label: 'パープル' },
  { hex: '#ec4899', label: 'ピンク' },
  { hex: '#f8fafc', label: 'ホワイト・明色' },
  { hex: '#1e293b', label: 'ダーク・暗色' },
] as const

const selectedColor = ref<string | null>(null)
const colorMode = ref<'sort' | 'filter'>('sort')
const COLOR_FILTER_THRESHOLD = 145

type SortOrder =
  | 'newest'
  | 'oldest'
  | 'color_hue'
  | 'color_bright'
  | 'color_dark'
  | 'folder_color'
  | 'title'
  | 'author'

const SORT_OPTIONS: { id: SortOrder; label: string }[] = [
  { id: 'newest', label: '追加が新しい順' },
  { id: 'oldest', label: '追加が古い順' },
  { id: 'color_hue', label: 'カラー順（色相スペクトル）' },
  { id: 'color_bright', label: 'カラー順（明るい順）' },
  { id: 'color_dark', label: 'カラー順（暗い順）' },
  { id: 'folder_color', label: 'フォルダカラー順' },
  { id: 'title', label: 'タイトル順' },
  { id: 'author', label: '作者名順' },
]
const sortOrder = ref<SortOrder>('newest')

function hexToRgb(hex: string): [number, number, number] | null {
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

function rgbToHsl(r: number, g: number, b: number): { h: number; s: number; l: number } {
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
function colorDistance(hexA: string, hexB: string): number {
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

function getFolderColorByName(folderName?: string): string {
  if (!folderName) return '#6366f1'
  const found = boardStore.folders.find(f => f.name === folderName)
  return found?.color || '#6366f1'
}

/** ブックマークのカラーパレット（未設定時はフォルダカラーにフォールバック） */
function getBookmarkPalette(b: BookmarkItem): string[] {
  const palette = b.ai_analysis?.palette?.filter(hex => !!hexToRgb(hex)) || []
  if (palette.length) return palette
  return [getFolderColorByName(b.folder_name)]
}

/** 指定カラーとブックマークのパレット間の最小色差を返す */
function getBookmarkMinColorDistance(b: BookmarkItem, targetHex: string): number {
  const palette = getBookmarkPalette(b)
  let min = 999
  for (const hex of palette) {
    const dist = colorDistance(hex, targetHex)
    if (dist < min) min = dist
  }
  return min
}

/** ブックマークの代表色から色相（Hue）・輝度（Luminance）を算出 */
function getBookmarkColorMetrics(b: BookmarkItem): { hue: number; luminance: number; saturation: number } {
  const palette = getBookmarkPalette(b)
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

const FOLDER_ORDER_KEY = 'reflens-folder-order'
const folderOrder = ref<string[]>([])

const draggingFolder = ref<string | null>(null)
const dragOverFolder = ref<string | null>(null)

const SOURCE_VIEWS = [
  { id: 'all', label: 'すべて', icon: Layers },
  { id: 'pixiv', label: 'pixiv', icon: Compass },
  { id: 'instagram', label: 'Instagram', icon: Instagram },
  { id: 'web_bookmark', label: 'Web', icon: Globe },
  { id: 'local_upload', label: 'ローカル', icon: Upload },
] as const

/** 全ブックマークから頻出AIタグを抽出（スマート総合検索用） */
const popularAiTags = computed(() => {
  const counts = new Map<string, number>()
  for (const b of boardStore.bookmarks) {
    for (const tag of b.ai_analysis?.tags || []) {
      const t = tag.trim()
      if (t) counts.set(t, (counts.get(t) || 0) + 1)
    }
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 14)
    .map(([tag, count]) => ({ tag, count }))
})

const filteredBookmarks = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()

  return boardStore.bookmarks.filter(b => {
    if (selectedSource.value !== 'all' && b.source_type !== selectedSource.value) return false
    if (selectedFolder.value && b.folder_name !== selectedFolder.value) return false

    // 検索タブでカラー絞り込みモード（filter）が有効な場合は近似色のみ抽出
    if (activeSection.value === 'search' && selectedColor.value && colorMode.value === 'filter') {
      if (getBookmarkMinColorDistance(b, selectedColor.value) > COLOR_FILTER_THRESHOLD) {
        return false
      }
    }

    // ライブラリ表示時は検索クエリを適用しない（検索タブと役割を明確に分離）
    if (activeSection.value !== 'search' || !q) return true

    const corpus = [
      b.title,
      b.author_name || '',
      b.source_url || '',
      b.folder_name || '',
      (b.ai_analysis?.tags || []).join(' '),
      b.ai_analysis?.composition || '',
      b.ai_analysis?.lighting || '',
      (b.ai_analysis?.palette || []).join(' '),
    ].join(' ')
    return corpus.toLowerCase().includes(q)
  })
})

function resolveThumbnail(path?: string) {
  return resolveMediaUrl(path)
}

const visibleBookmarks = computed(() => {
  const list = [...filteredBookmarks.value]
  const addedAt = (b: BookmarkItem) => (b.created_at ? Date.parse(b.created_at) : 0)

  // 検索画面でターゲットカラーが選択されている場合は、指定色に近い順（カラーソート）を最優先
  if (activeSection.value === 'search' && selectedColor.value) {
    const target = selectedColor.value
    return list.sort((a, b) => {
      const diff = getBookmarkMinColorDistance(a, target) - getBookmarkMinColorDistance(b, target)
      return Math.abs(diff) > 0.5 ? diff : addedAt(b) - addedAt(a)
    })
  }

  switch (sortOrder.value) {
    case 'oldest':
      return list.sort((a, b) => addedAt(a) - addedAt(b))
    case 'color_hue':
      return list.sort((a, b) => {
        const ma = getBookmarkColorMetrics(a)
        const mb = getBookmarkColorMetrics(b)
        return ma.hue - mb.hue || mb.luminance - ma.luminance
      })
    case 'color_bright':
      return list.sort((a, b) => {
        const ma = getBookmarkColorMetrics(a)
        const mb = getBookmarkColorMetrics(b)
        return mb.luminance - ma.luminance || ma.hue - mb.hue
      })
    case 'color_dark':
      return list.sort((a, b) => {
        const ma = getBookmarkColorMetrics(a)
        const mb = getBookmarkColorMetrics(b)
        return ma.luminance - mb.luminance || ma.hue - mb.hue
      })
    case 'folder_color':
      return list.sort((a, b) => {
        const ca = getFolderColorByName(a.folder_name)
        const cb = getFolderColorByName(b.folder_name)
        const rgbA = hexToRgb(ca) || [99, 102, 241]
        const rgbB = hexToRgb(cb) || [99, 102, 241]
        const hslA = rgbToHsl(rgbA[0], rgbA[1], rgbA[2])
        const hslB = rgbToHsl(rgbB[0], rgbB[1], rgbB[2])
        return hslA.h - hslB.h || (a.folder_name || '').localeCompare(b.folder_name || '', 'ja')
      })
    case 'title':
      return list.sort((a, b) => a.title.localeCompare(b.title, 'ja'))
    case 'author':
      return list.sort((a, b) => (a.author_name || '').localeCompare(b.author_name || '', 'ja'))
    default:
      return list.sort((a, b) => addedAt(b) - addedAt(a))
  }
})

/** ホーム下部に出す最近追加した資料（最新6件） */
const recentBookmarks = computed(() => {
  const addedAt = (b: BookmarkItem) => (b.created_at ? Date.parse(b.created_at) : 0)
  return [...boardStore.bookmarks].sort((a, b) => addedAt(b) - addedAt(a)).slice(0, 6)
})

const visibleFolders = computed<FolderItem[]>(() => {
  const q = folderQuery.value.toLowerCase().trim()
  const list = boardStore.folders.filter(f => {
    // 0件の組み込み英語フォルダ（!f.id）はノイズになるため除外（All References とカスタムフォルダは常に表示）
    if (!f.id && f.name !== 'All References' && getFolderBookmarks(f).length === 0 && selectedFolder.value !== f.name) {
      return false
    }
    if (
      activeSection.value === 'home' &&
      selectedFolderColorFilter.value &&
      f.name !== 'All References' &&
      (f.color || '#6366f1').toLowerCase() !== selectedFolderColorFilter.value.toLowerCase()
    ) {
      return false
    }
    if (!q) return true
    const label = f.name === 'All References' ? 'すべての資料 all references' : f.name
    return label.toLowerCase().includes(q)
  })

  const rank = (name: string) => {
    const index = folderOrder.value.indexOf(name)
    return index === -1 ? Number.MAX_SAFE_INTEGER : index
  }

  const fixed = list.filter(f => !f.id)
  const custom = list
    .filter(f => !!f.id)
    .sort((a, b) => rank(a.name) - rank(b.name) || a.name.localeCompare(b.name, 'ja'))

  return [...fixed, ...custom]
})

/** ライブラリ用のフォルダ一覧（libraryFolderQuery でリアルタイム絞り込み） */
const libraryVisibleFolders = computed<FolderItem[]>(() => {
  const q = libraryFolderQuery.value.toLowerCase().trim()
  const list = boardStore.folders.filter(f => {
    // 0件の組み込み英語フォルダ（!f.id）はノイズになるため除外（All References とカスタムフォルダは常に表示）
    if (!f.id && f.name !== 'All References' && getFolderBookmarks(f).length === 0 && selectedFolder.value !== f.name) {
      return false
    }
    if (!q) return true
    const label = f.name === 'All References' ? 'すべての資料 all references' : f.name
    return label.toLowerCase().includes(q)
  })

  const rank = (name: string) => {
    const index = folderOrder.value.indexOf(name)
    return index === -1 ? Number.MAX_SAFE_INTEGER : index
  }

  const fixed = list.filter(f => !f.id)
  const custom = list
    .filter(f => !!f.id)
    .sort((a, b) => rank(a.name) - rank(b.name) || a.name.localeCompare(b.name, 'ja'))

  return [...fixed, ...custom]
})

function selectFirstMatchingLibraryFolder() {
  const matches = libraryVisibleFolders.value
  if (!matches.length) return
  const first = matches.find(f => f.name !== 'All References') || matches[0]
  if (first.name === 'All References') {
    selectedFolder.value = null
  } else {
    selectedFolder.value = first.name
  }
}

function scrollLibraryFolders(delta: number) {
  if (libraryFolderScrollRef.value) {
    libraryFolderScrollRef.value.scrollBy({ left: delta, behavior: 'smooth' })
  }
}

/** 現在フォルダに設定されているカラー一覧（ホームのカラーフィルタ用） */
const activeFolderColors = computed(() => {
  const map = new Map<string, number>()
  for (const f of boardStore.folders) {
    if (f.name === 'All References') continue
    if (!f.id && getFolderBookmarks(f).length === 0) continue
    const c = (f.color || '#6366f1').toLowerCase()
    map.set(c, (map.get(c) || 0) + 1)
  }
  return [...map.entries()].map(([color, count]) => ({ color, count }))
})

function formatFolderLabel(name: string): string {
  return name === 'All References' ? 'すべての資料' : name
}

/** 各フォルダに属するブックマーク一覧（ダッシュボードのサムネイル・件数表示用） */
function getFolderBookmarks(folder: FolderItem): BookmarkItem[] {
  if (folder.name === 'All References') return boardStore.bookmarks
  return boardStore.bookmarks.filter(b => b.folder_name === folder.name)
}

function getFolderPreviewThumbs(folder: FolderItem): string[] {
  return getFolderBookmarks(folder)
    .slice(0, 4)
    .map(b => resolveThumbnail(b.file_path))
    .filter(Boolean)
}

function isCustomFolder(folder: FolderItem) {
  return !!folder.id
}

/** サイドナビの 3 セクション切り替え */
async function switchSection(section: ManagerSection) {
  activeSection.value = section
  isMobileSidebarOpen.value = false
  if (section === 'library') {
    selectedSource.value = 'all'
  }
  cardViewRef.value?.scrollTo({ top: 0 })
  if (section === 'search') {
    await nextTick()
    smartSearchInputRef.value?.focus()
  }
}

/** フォルダを選択してライブラリ（ブックマーク一覧）を開く */
function selectFolder(folder: FolderItem) {
  selectedFolder.value = folder.name === 'All References' ? null : folder.name
  selectedSource.value = 'all'
  activeSection.value = 'library'
  isMobileSidebarOpen.value = false
  cardViewRef.value?.scrollTo({ top: 0 })
}

function resetFilters() {
  selectedFolder.value = null
  selectedSource.value = 'all'
  searchQuery.value = ''
  selectedColor.value = null
  sortOrder.value = 'newest'
  cardViewRef.value?.scrollTo({ top: 0 })
}

function toggleTagSearch(tag: string) {
  searchQuery.value = searchQuery.value.trim() === tag ? '' : tag
}

function toggleColorSearch(hex: string) {
  if (selectedColor.value?.toLowerCase() === hex.toLowerCase()) {
    selectedColor.value = null
  } else {
    selectedColor.value = hex
  }
}

const hasActiveSearchFilters = computed(
  () =>
    selectedFolder.value !== null ||
    selectedSource.value !== 'all' ||
    !!searchQuery.value.trim() ||
    selectedColor.value !== null ||
    sortOrder.value !== 'newest'
)

function chipStyle(color?: string) {
  const hex = (color || '').replace('#', '')
  if (!/^[0-9a-f]{6}$/i.test(hex)) return { backgroundColor: 'var(--surface-hover)' }

  const r = parseInt(hex.slice(0, 2), 16)
  const g = parseInt(hex.slice(2, 4), 16)
  const b = parseInt(hex.slice(4, 6), 16)
  return { backgroundColor: `rgba(${r}, ${g}, ${b}, 0.16)` }
}

function persistFolderOrder() {
  try {
    window.localStorage.setItem(FOLDER_ORDER_KEY, JSON.stringify(folderOrder.value))
  } catch {
    /* localStorage が使えない環境ではその場の並びだけ反映する */
  }
}

function restoreFolderOrder() {
  try {
    const raw = window.localStorage.getItem(FOLDER_ORDER_KEY)
    const parsed = raw ? JSON.parse(raw) : null
    if (Array.isArray(parsed)) {
      folderOrder.value = parsed.filter((name): name is string => typeof name === 'string')
    }
  } catch {
    /* 壊れた値は無視して既定順のまま表示する */
  }
}

function resetFolderDrag() {
  draggingFolder.value = null
  dragOverFolder.value = null
}

function onFolderDragStart(folder: FolderItem, event: DragEvent) {
  if (!isCustomFolder(folder)) {
    event.preventDefault()
    return
  }

  draggingFolder.value = folder.name
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', folder.name)
  }
}

function onFolderDragOver(folder: FolderItem, event: DragEvent) {
  if (!draggingFolder.value || !isCustomFolder(folder) || draggingFolder.value === folder.name) return
  event.preventDefault()
  dragOverFolder.value = folder.name
}

function onFolderDragLeave(folder: FolderItem) {
  if (dragOverFolder.value === folder.name) dragOverFolder.value = null
}

function onFolderDrop(target: FolderItem) {
  const source = draggingFolder.value
  resetFolderDrag()
  if (!source || source === target.name || !isCustomFolder(target)) return

  // カスタムコレクションの現在の並び（保存済み順 → 未保存分は名前順）を作り、
  // ドラッグ元をドロップ先の位置へ差し込む。
  const names = boardStore.folders.filter(f => !!f.id).map(f => f.name)
  const order = [
    ...folderOrder.value.filter(name => names.includes(name)),
    ...names.filter(name => !folderOrder.value.includes(name)),
  ]

  const from = order.indexOf(source)
  const to = order.indexOf(target.name)
  if (from === -1 || to === -1) return

  order.splice(to, 0, ...order.splice(from, 1))
  folderOrder.value = order
  persistFolderOrder()
}

function moveFolderByKey(folder: FolderItem, delta: -1 | 1) {
  if (!isCustomFolder(folder)) return
  const names = boardStore.folders.filter(f => !!f.id).map(f => f.name)
  const order = [
    ...folderOrder.value.filter(name => names.includes(name)),
    ...names.filter(name => !folderOrder.value.includes(name)),
  ]
  const from = order.indexOf(folder.name)
  const to = from + delta
  if (from === -1 || to < 0 || to >= order.length) return
  order.splice(to, 0, ...order.splice(from, 1))
  folderOrder.value = order
  persistFolderOrder()
}

async function handleRenameFolder(folder: FolderItem, name: string) {
  if (!folder.id) return
  await boardStore.renameFolder(folder.id, name)
}

async function handleUpdateFolderColor(folder: FolderItem, color: string) {
  if (!folder.id) return
  await boardStore.updateFolderColor(folder.id, color)
}

async function handleDeleteFolder(folder: FolderItem) {
  if (!folder.id) return
  await boardStore.deleteFolder(folder.id)
}

async function handleDropUrl() {
  const url = inputDropUrl.value.trim()
  if (!url || isDropping.value) return

  isDropping.value = true
  inputDropUrl.value = ''

  try {
    const res = await boardStore.addBookmark(url, selectedFolder.value ?? 'All References', false)
    if (res) toast.success('ライブラリに保存しました', url)
  } finally {
    isDropping.value = false
  }
}

async function handleUploadFiles(files: File[]) {
  if (!files.length) return
  await boardStore.uploadImages(files, 150, 150)
}

async function onFileInputChange(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files?.length) {
    await handleUploadFiles(Array.from(target.files))
    target.value = ''
  }
}

async function onStashDrop(e: DragEvent) {
  isDraggingFiles.value = false
  if (!e.dataTransfer) return
  const files = extractImagesFromDataTransfer(e.dataTransfer)
  if (files.length) {
    await handleUploadFiles(files)
    return
  }
  const urlData = e.dataTransfer.getData('text/uri-list') || e.dataTransfer.getData('text/plain')
  if (urlData && /^https?:\/\//.test(urlData.trim())) {
    inputDropUrl.value = urlData.trim()
    await handleDropUrl()
  }
}

async function copyHex(hex: string) {
  if (await copyToClipboard(hex)) {
    toast.success(`カラーコード ${hex} をコピーしました`)
  } else {
    toast.error('クリップボードにコピーできませんでした')
  }
}

async function handleClickPaletteDot(hex: string) {
  if (activeSection.value === 'search') {
    toggleColorSearch(hex)
    return
  }
  await copyHex(hex)
}

async function handlePlaceOnBoard(item: BookmarkItem) {
  if (!boardStore.currentBoard) {
    const board = await boardStore.loadFirstBoard()
    if (!board) {
      toast.error('キャンバスボードがありません')
      return
    }
  }
  await boardStore.placeBookmarkOnBoard(item.id, 150, 150)
  await navigateTo(`/board/${boardStore.currentBoard!.id}`)
}

async function handleCreateFolder() {
  if (!newFolderName.value.trim()) return
  const name = newFolderName.value.trim()
  const color = newFolderColor.value || '#6366f1'
  newFolderName.value = ''
  showNewFolder.value = false
  await boardStore.createFolder(name, color)
  selectedFolder.value = name
}

async function handleMoveBookmark(item: BookmarkItem, folderName: string) {
  const moved = await boardStore.moveBookmarkFolder(item.id, folderName)
  if (moved) toast.success('フォルダを変更しました', folderName)
}

async function handleDeleteBookmark(item: BookmarkItem) {
  const deleted = await boardStore.deleteBookmark(item.id)
  if (deleted) toast.success('ライブラリから削除しました', item.title)
}

onMounted(async () => {
  restoreFolderOrder()
  await Promise.all([boardStore.fetchBookmarks(), boardStore.fetchFolders()])
  // サイドバーの「キャンバスを開く」リンク用に最初のボードをロードしておく
  await boardStore.loadFirstBoard()
})
</script>

<template>
  <div class="h-app-screen overflow-hidden bg-canvas-bg text-ink flex flex-col antialiased">
    <AppHeader class="shrink-0" />

    <div class="flex-1 min-h-0 flex max-w-[1680px] w-full mx-auto overflow-hidden">
      <!-- サイドナビゲーションバー: ホーム / 検索 / ライブラリ の 3 構成 + フォルダ一覧 -->
      <aside
        id="manager-sidebar"
        aria-label="Manager ナビゲーション"
        class="shrink-0 flex-col gap-3"
        :class="isMobileSidebarOpen
          ? 'fixed inset-x-0 top-14 bottom-0 z-40 flex w-full h-[calc(100dvh-3.5rem)] overflow-y-auto overscroll-contain bg-canvas-panel border-t border-canvas-border shadow-pop p-4 pb-safe-drawer md:static md:w-64 md:h-full md:border-t-0 md:border-r md:border-canvas-border md:bg-canvas-panel md:shadow-none md:p-3 md:overflow-hidden'
          : 'hidden md:flex md:w-64 md:h-full md:border-r md:border-canvas-border md:bg-canvas-panel md:p-3 md:overflow-hidden'"
      >
        <div class="shrink-0 space-y-3">
          <!-- モバイル時: ページ間ナビゲーション + サイト情報モーダル起動 -->
          <div class="md:hidden pb-3 border-b border-canvas-border">
            <MobileNavLinks :show-site-links="true" />
          </div>

          <!-- 3 構成メインメニュー: ホーム / 検索 / ライブラリ -->
          <nav class="space-y-1" aria-label="Manager メインメニュー">
            <button
              type="button"
              class="w-full flex items-center justify-between gap-2.5 rounded-xl px-3 py-2.5 text-xs transition-colors"
              :class="activeSection === 'home'
                ? 'bg-brand text-brand-fg font-bold shadow-sm'
                : 'text-ink hover:bg-canvas-hover font-semibold'"
              :aria-current="activeSection === 'home' ? 'page' : undefined"
              @click="switchSection('home')"
            >
              <span class="flex items-center gap-2.5 min-w-0">
                <Home class="w-4 h-4 shrink-0" :class="activeSection === 'home' ? 'text-brand-fg' : 'text-ink-muted'" />
                <span class="truncate">ホーム</span>
              </span>
              <span
                class="text-[10px] font-mono px-1.5 py-0.5 rounded-md shrink-0"
                :class="activeSection === 'home' ? 'bg-black/15 text-brand-fg' : 'text-ink-muted bg-canvas-bg'"
              >
                フォルダ
              </span>
            </button>

            <button
              type="button"
              class="w-full flex items-center justify-between gap-2.5 rounded-xl px-3 py-2.5 text-xs transition-colors"
              :class="activeSection === 'search'
                ? 'bg-brand text-brand-fg font-bold shadow-sm'
                : 'text-ink hover:bg-canvas-hover font-semibold'"
              :aria-current="activeSection === 'search' ? 'page' : undefined"
              @click="switchSection('search')"
            >
              <span class="flex items-center gap-2.5 min-w-0">
                <Search class="w-4 h-4 shrink-0" :class="activeSection === 'search' ? 'text-brand-fg' : 'text-ink-muted'" />
                <span class="truncate">検索</span>
              </span>
              <span
                class="text-[10px] font-mono px-1.5 py-0.5 rounded-md shrink-0"
                :class="activeSection === 'search' ? 'bg-black/15 text-brand-fg' : 'text-ink-muted bg-canvas-bg'"
              >
                スマート検索
              </span>
            </button>

            <button
              type="button"
              class="w-full flex items-center justify-between gap-2.5 rounded-xl px-3 py-2.5 text-xs transition-colors"
              :class="activeSection === 'library' && selectedFolder === null
                ? 'bg-brand text-brand-fg font-bold shadow-sm'
                : 'text-ink hover:bg-canvas-hover font-semibold'"
              :aria-current="activeSection === 'library' && selectedFolder === null ? 'page' : undefined"
              @click="selectedFolder = null; switchSection('library')"
            >
              <span class="flex items-center gap-2.5 min-w-0">
                <Bookmark class="w-4 h-4 shrink-0" :class="activeSection === 'library' && selectedFolder === null ? 'text-brand-fg' : 'text-ink-muted'" />
                <span class="truncate">ライブラリ</span>
              </span>
              <span
                class="text-[10px] font-mono px-1.5 py-0.5 rounded-md shrink-0"
                :class="activeSection === 'library' && selectedFolder === null ? 'bg-black/15 text-brand-fg' : 'text-ink-muted bg-canvas-bg'"
              >
                {{ boardStore.bookmarks.length }}
              </span>
            </button>
          </nav>
        </div>

        <!-- ブックマークフォルダ一覧（クリックでそのフォルダのライブラリを開く） -->
        <div class="md:flex-1 md:min-h-0 flex flex-col pt-3 border-t border-canvas-border gap-2">
          <div class="shrink-0 flex items-center justify-between px-1">
            <span class="text-[11px] font-bold text-ink-muted flex items-center gap-1.5">
              <FolderOpen class="w-3.5 h-3.5" />
              <span>フォルダ</span>
              <span class="text-[10px] font-mono">({{ visibleFolders.length }})</span>
            </span>
            <button
              type="button"
              class="px-2 py-1 rounded-lg text-[11px] font-bold text-brand hover:bg-brand-soft transition-colors flex items-center gap-1"
              @click="showNewFolder = !showNewFolder"
            >
              <Plus class="w-3.5 h-3.5" />
              <span>新規</span>
            </button>
          </div>

          <!-- 新規フォルダ作成フォーム -->
          <form
            v-if="showNewFolder"
            class="shrink-0 p-2.5 rounded-xl bg-canvas-bg border border-brand space-y-2.5"
            @submit.prevent="handleCreateFolder"
          >
            <input
              v-model="newFolderName"
              type="text"
              placeholder="新しいフォルダ名"
              class="w-full bg-canvas-panel border border-canvas-border-strong rounded-lg px-2.5 py-1.5 text-xs text-ink placeholder:text-ink-muted focus:outline-none focus:border-brand"
              autofocus
            >
            <div class="space-y-1.5">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-bold text-ink-muted flex items-center gap-1">
                  <Palette class="w-3 h-3 text-brand" />
                  <span>フォルダカラー</span>
                </span>
                <label class="flex items-center gap-1 text-[10px] font-mono text-ink-muted hover:text-ink cursor-pointer">
                  <input
                    v-model="newFolderColor"
                    type="color"
                    class="w-3.5 h-3.5 rounded border-0 bg-transparent p-0 cursor-pointer"
                    aria-label="カスタムフォルダカラー"
                  >
                  <span class="uppercase">{{ newFolderColor }}</span>
                </label>
              </div>
              <div class="flex flex-wrap items-center gap-1.5">
                <button
                  v-for="c in FOLDER_COLORS"
                  :key="c.hex"
                  type="button"
                  class="w-4 h-4 rounded-full border transition-transform hover:scale-110"
                  :class="newFolderColor.toLowerCase() === c.hex.toLowerCase()
                    ? 'border-ink ring-2 ring-brand/40 scale-110'
                    : 'border-canvas-border'"
                  :style="{ backgroundColor: c.hex }"
                  :title="c.label"
                  :aria-label="`${c.label} を選択`"
                  @click="newFolderColor = c.hex"
                />
              </div>
            </div>
            <div class="flex justify-end gap-2">
              <button
                type="button"
                class="text-[11px] font-medium text-ink-muted hover:text-ink px-2 py-0.5"
                @click="showNewFolder = false"
              >
                キャンセル
              </button>
              <button
                type="submit"
                class="text-[11px] rounded-md bg-brand text-brand-fg font-bold px-2.5 py-1"
              >
                作成
              </button>
            </div>
          </form>

          <!-- フォルダ一覧スクロール枠 -->
          <div class="md:flex-1 md:min-h-0 md:overflow-y-auto space-y-1 pr-0.5">
            <div
              v-for="folder in visibleFolders"
              :key="folder.name"
              class="group flex items-center gap-2 rounded-xl pl-1.5 pr-1.5 py-2 md:py-1.5 transition-colors"
              :class="[
                activeSection === 'library' && ((folder.name === 'All References' && selectedFolder === null) || selectedFolder === folder.name)
                  ? 'bg-brand-soft ring-1 ring-inset ring-brand/25'
                  : 'hover:bg-canvas-hover',
                dragOverFolder === folder.name ? 'ring-1 ring-brand' : '',
                draggingFolder === folder.name ? 'opacity-50' : '',
                isCustomFolder(folder) ? 'cursor-grab active:cursor-grabbing' : 'cursor-pointer',
              ]"
              role="button"
              tabindex="0"
              :draggable="isCustomFolder(folder)"
              :title="isCustomFolder(folder) ? `${folder.name}（ドラッグまたは Alt+↑↓ で並び替え）` : folder.name"
              @click="selectFolder(folder)"
              @keydown.enter.prevent="selectFolder(folder)"
              @keydown.space.prevent="selectFolder(folder)"
              @keydown.alt.up.prevent="moveFolderByKey(folder, -1)"
              @keydown.alt.down.prevent="moveFolderByKey(folder, 1)"
              @dragstart="onFolderDragStart(folder, $event)"
              @dragover="onFolderDragOver(folder, $event)"
              @dragleave="onFolderDragLeave(folder)"
              @drop.prevent="onFolderDrop(folder)"
              @dragend="resetFolderDrag"
            >
              <span class="w-4 shrink-0 flex items-center justify-center text-ink-muted">
                <GripVertical
                  v-if="isCustomFolder(folder)"
                  class="w-3.5 h-3.5 opacity-60 group-hover:opacity-100 transition-opacity"
                />
                <Lock v-else class="w-3 h-3 opacity-60" />
              </span>

              <span
                class="w-2.5 h-2.5 rounded-full shrink-0"
                :style="{ backgroundColor: folder.color || '#6366f1' }"
              />

              <span
                class="flex-1 truncate text-xs"
                :class="activeSection === 'library' && ((folder.name === 'All References' && selectedFolder === null) || selectedFolder === folder.name)
                  ? 'text-brand font-bold'
                  : 'text-ink font-semibold'"
              >
                {{ formatFolderLabel(folder.name) }}
              </span>

              <span
                class="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-mono font-semibold text-ink"
                :style="chipStyle(folder.color)"
              >
                {{ getFolderBookmarks(folder).length }}
              </span>

              <FolderActionsMenu
                v-if="isCustomFolder(folder)"
                :folder="folder"
                @rename="handleRenameFolder(folder, $event)"
                @color-change="handleUpdateFolderColor(folder, $event)"
                @delete="handleDeleteFolder(folder)"
              />
            </div>
          </div>
        </div>
      </aside>

      <!-- メインコンテンツ領域 -->
      <main
        id="main-content"
        ref="cardViewRef"
        tabindex="-1"
        class="flex-1 min-h-0 overflow-y-auto px-3 sm:px-4 md:px-6 pt-2.5 sm:pt-4 pb-safe-main space-y-4 focus:outline-none"
      >
        <!-- モバイル用 3 構成クイック切替タブ（ハンバーガーを開かなくても1タップでホーム/検索/ライブラリを移動可能） -->
        <div class="md:hidden grid grid-cols-3 gap-1 p-1 rounded-xl bg-canvas-panel border border-canvas-border">
          <button
            type="button"
            class="flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-bold transition-colors"
            :class="activeSection === 'home' ? 'bg-brand text-brand-fg' : 'text-ink-muted hover:text-ink'"
            @click="switchSection('home')"
          >
            <Home class="w-3.5 h-3.5 shrink-0" />
            <span>ホーム</span>
          </button>
          <button
            type="button"
            class="flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-bold transition-colors"
            :class="activeSection === 'search' ? 'bg-brand text-brand-fg' : 'text-ink-muted hover:text-ink'"
            @click="switchSection('search')"
          >
            <Search class="w-3.5 h-3.5 shrink-0" />
            <span>検索</span>
          </button>
          <button
            type="button"
            class="flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-bold transition-colors"
            :class="activeSection === 'library' ? 'bg-brand text-brand-fg' : 'text-ink-muted hover:text-ink'"
            @click="switchSection('library')"
          >
            <Bookmark class="w-3.5 h-3.5 shrink-0" />
            <span>ライブラリ</span>
          </button>
        </div>

        <!-- 共通クイック保存バー（ホーム・ライブラリ表示時） -->
        <section
          v-if="activeSection !== 'search'"
          class="p-2.5 sm:p-3.5 rounded-2xl bg-canvas-panel border transition-colors space-y-2 sm:space-y-2.5"
          :class="isDraggingFiles ? 'border-brand ring-2 ring-brand/30 bg-brand-soft/30' : 'border-canvas-border'"
          aria-label="資料の追加"
          @dragover.prevent="isDraggingFiles = true"
          @dragleave="isDraggingFiles = false"
          @drop.prevent="onStashDrop"
        >
          <input
            ref="fileInputRef"
            type="file"
            accept="image/*"
            multiple
            class="hidden"
            @change="onFileInputChange"
          >
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div class="min-w-0">
              <h2 class="text-xs sm:text-sm font-bold text-ink flex items-center gap-1.5 sm:gap-2">
                <Bookmark class="w-3.5 h-3.5 sm:w-4 sm:h-4 text-pixiv shrink-0" />
                <span class="truncate">Drop &amp; Stash Reference</span>
              </h2>
              <p class="text-[11px] text-ink-muted mt-0.5">
                pixiv・Instagram・Web画像URLを貼り付け、または画像ファイルをドロップして保存
              </p>
            </div>

            <div class="flex items-center gap-1.5 sm:gap-2 w-full sm:w-auto shrink-0">
              <button
                type="button"
                class="flex-1 sm:flex-initial min-w-0 px-2 sm:px-3 py-1.5 rounded-xl text-[11px] font-bold bg-canvas-bg hover:bg-canvas-hover text-ink border border-canvas-border-strong hover:border-brand transition-colors flex items-center justify-center gap-1 whitespace-nowrap"
                title="ローカルの画像ファイルを追加"
                @click="fileInputRef?.click()"
              >
                <Upload class="w-3.5 h-3.5 text-ink-muted shrink-0" />
                <span class="sm:hidden">追加</span>
                <span class="hidden sm:inline">画像追加</span>
              </button>

              <NuxtLink
                to="/view"
                class="flex-1 sm:flex-initial min-w-0 px-2 sm:px-3 py-1.5 rounded-xl text-[11px] font-bold bg-pixiv-soft text-pixiv border border-pixiv/40 hover:border-pixiv transition-colors flex items-center justify-center gap-1 whitespace-nowrap"
              >
                <Compass class="w-3.5 h-3.5 shrink-0" />
                <span class="sm:hidden">pixiv</span>
                <span class="hidden sm:inline">pixivで探す</span>
              </NuxtLink>

              <NuxtLink
                :to="boardStore.currentBoard ? `/board/${boardStore.currentBoard.id}` : '/canvas'"
                class="flex-1 sm:flex-initial min-w-0 px-2 sm:px-3 py-1.5 rounded-xl text-[11px] font-bold bg-brand text-brand-fg hover:bg-brand-hover transition-colors flex items-center justify-center gap-1 whitespace-nowrap"
              >
                <Layers class="w-3.5 h-3.5 shrink-0" />
                <span class="sm:hidden">キャンバス</span>
                <span class="hidden sm:inline">キャンバスで開く</span>
              </NuxtLink>
            </div>
          </div>

          <div class="relative flex items-center">
            <Globe class="absolute left-3 w-3.5 h-3.5 sm:w-4 sm:h-4 text-ink-subtle pointer-events-none" />
            <input
              v-model="inputDropUrl"
              type="url"
              placeholder="https://www.pixiv.net/artworks/..."
              class="w-full bg-canvas-card border border-canvas-border rounded-xl pl-9 sm:pl-10 pr-20 sm:pr-24 py-1.5 sm:py-2 text-xs text-ink placeholder:text-ink-subtle focus:outline-none focus:border-pixiv font-mono transition-colors"
              aria-label="URLをライブラリへ保存"
              @keydown.enter="handleDropUrl"
            >
            <button
              type="button"
              class="absolute right-1.5 px-2.5 sm:px-3.5 py-1 bg-brand text-brand-fg hover:bg-brand-hover rounded-lg text-[11px] font-bold transition-colors disabled:opacity-50 flex items-center gap-1"
              :disabled="!inputDropUrl.trim() || isDropping"
              @click="handleDropUrl"
            >
              <Check class="w-3.5 h-3.5" />
              {{ isDropping ? '保存中...' : '保存' }}
            </button>
          </div>
        </section>

        <!-- =========================================================
             1. ホーム（ブックマークフォルダダッシュボード）
             ========================================================= -->
        <div v-if="activeSection === 'home'" class="space-y-6 pb-6">
          <!-- フォルダダッシュボード -->
          <section class="space-y-3" aria-label="ブックマークフォルダダッシュボード">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div class="flex items-center gap-2">
                <FolderOpen class="w-4 h-4 text-brand shrink-0" />
                <h1 class="text-sm sm:text-base font-bold text-ink">ブックマークフォルダ</h1>
                <span class="text-xs font-mono text-ink-muted">({{ visibleFolders.length }})</span>
              </div>

              <div class="flex items-center gap-2">
                <div class="relative flex items-center">
                  <Search class="absolute left-2.5 w-3.5 h-3.5 text-ink-muted pointer-events-none" />
                  <input
                    v-model="folderQuery"
                    type="search"
                    placeholder="フォルダを検索..."
                    class="w-36 sm:w-48 bg-canvas-panel border border-canvas-border rounded-xl pl-8 pr-2.5 py-1.5 text-xs text-ink placeholder:text-ink-subtle focus:outline-none focus:border-brand"
                    aria-label="フォルダを検索"
                  >
                </div>

                <button
                  type="button"
                  class="px-3 py-1.5 rounded-xl bg-brand text-brand-fg hover:bg-brand-hover text-xs font-bold transition-colors flex items-center gap-1 shrink-0"
                  @click="showNewFolder = !showNewFolder"
                >
                  <Plus class="w-3.5 h-3.5" />
                  <span>新規フォルダ</span>
                </button>
              </div>
            </div>

            <!-- ホーム内: 新規フォルダ作成フォーム（カラー選択付き） -->
            <form
              v-if="showNewFolder"
              class="p-3.5 rounded-2xl bg-canvas-panel border border-brand space-y-3 shadow-panel"
              @submit.prevent="handleCreateFolder"
            >
              <div class="flex flex-col sm:flex-row sm:items-center gap-2.5">
                <div class="flex items-center gap-2 flex-1">
                  <span
                    class="w-4 h-4 rounded-full shrink-0 border border-canvas-border"
                    :style="{ backgroundColor: newFolderColor }"
                  />
                  <input
                    v-model="newFolderName"
                    type="text"
                    placeholder="新しいフォルダ名を入力..."
                    class="flex-1 bg-canvas-bg border border-canvas-border-strong rounded-xl px-3 py-2 text-xs font-medium text-ink placeholder:text-ink-muted focus:outline-none focus:border-brand"
                    autofocus
                  >
                </div>
                <div class="flex items-center justify-end gap-2 shrink-0">
                  <button
                    type="button"
                    class="px-3 py-1.5 rounded-xl text-xs font-semibold text-ink-muted hover:text-ink bg-canvas-bg border border-canvas-border transition-colors"
                    @click="showNewFolder = false"
                  >
                    キャンセル
                  </button>
                  <button
                    type="submit"
                    class="px-3.5 py-1.5 rounded-xl bg-brand text-brand-fg hover:bg-brand-hover text-xs font-bold transition-colors disabled:opacity-50"
                    :disabled="!newFolderName.trim()"
                  >
                    フォルダを作成
                  </button>
                </div>
              </div>

              <div class="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-canvas-border">
                <div class="flex flex-wrap items-center gap-1.5">
                  <span class="text-xs font-bold text-ink-muted flex items-center gap-1 mr-1">
                    <Palette class="w-3.5 h-3.5 text-brand" />
                    <span>カラー:</span>
                  </span>
                  <button
                    v-for="c in FOLDER_COLORS"
                    :key="c.hex"
                    type="button"
                    class="w-5 h-5 rounded-full border transition-transform hover:scale-110"
                    :class="newFolderColor.toLowerCase() === c.hex.toLowerCase()
                      ? 'border-ink ring-2 ring-brand/40 scale-110'
                      : 'border-canvas-border'"
                    :style="{ backgroundColor: c.hex }"
                    :title="c.label"
                    :aria-label="`${c.label} を選択`"
                    @click="newFolderColor = c.hex"
                  />
                </div>
                <label class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-canvas-bg border border-canvas-border-strong hover:border-brand text-[11px] font-semibold text-ink cursor-pointer transition-colors">
                  <input
                    v-model="newFolderColor"
                    type="color"
                    class="w-3.5 h-3.5 rounded border-0 bg-transparent p-0 cursor-pointer"
                    aria-label="カスタムカラーを選択"
                  >
                  <span class="font-mono uppercase">{{ newFolderColor }}</span>
                </label>
              </div>
            </form>

            <!-- フォルダカラーによるクイック絞り込みバー -->
            <div
              v-if="activeFolderColors.length > 1"
              class="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-0.5"
              role="group"
              aria-label="フォルダカラーで絞り込み"
            >
              <span class="text-[11px] font-bold text-ink-muted flex items-center gap-1 mr-1 shrink-0">
                <Palette class="w-3.5 h-3.5 text-brand" />
                <span>カラー別:</span>
              </span>
              <button
                type="button"
                class="px-2.5 py-1 rounded-full text-[11px] font-semibold border transition-colors shrink-0"
                :class="selectedFolderColorFilter === null
                  ? 'bg-brand text-brand-fg border-brand font-bold'
                  : 'bg-canvas-panel text-ink border-canvas-border-strong hover:bg-canvas-hover'"
                @click="selectedFolderColorFilter = null"
              >
                すべて
              </button>
              <button
                v-for="item in activeFolderColors"
                :key="item.color"
                type="button"
                class="px-2.5 py-1 rounded-full text-[11px] font-semibold border transition-colors flex items-center gap-1.5 shrink-0"
                :class="selectedFolderColorFilter === item.color
                  ? 'bg-brand text-brand-fg border-brand font-bold'
                  : 'bg-canvas-panel text-ink border-canvas-border-strong hover:bg-canvas-hover'"
                @click="selectedFolderColorFilter = selectedFolderColorFilter === item.color ? null : item.color"
              >
                <span class="w-2.5 h-2.5 rounded-full shrink-0 border border-black/15" :style="{ backgroundColor: item.color }" />
                <span class="font-mono text-[10px]">{{ item.count }}</span>
              </button>
            </div>

            <!-- フォルダカードグリッド -->
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3.5">
              <div
                v-for="folder in visibleFolders"
                :key="folder.name"
                tabindex="0"
                role="button"
                :aria-label="`${folder.name} フォルダを開く（${getFolderBookmarks(folder).length}件）`"
                class="group relative flex flex-col rounded-2xl bg-canvas-panel border border-canvas-border hover:border-brand focus-visible:border-brand transition-colors overflow-hidden cursor-pointer shadow-panel"
                @click="selectFolder(folder)"
                @keydown.enter.self.prevent="selectFolder(folder)"
                @keydown.space.self.prevent="selectFolder(folder)"
              >
                <!-- フォルダカラーアクセントバー -->
                <div
                  class="h-1.5 w-full shrink-0"
                  :style="{ backgroundColor: folder.color || '#6366f1' }"
                />

                <!-- サムネイルコラージュプレビュー -->
                <div class="relative aspect-[16/9] bg-canvas-sunken overflow-hidden">
                  <div
                    v-if="getFolderPreviewThumbs(folder).length >= 3"
                    class="w-full h-full grid grid-cols-3 grid-rows-2 gap-0.5"
                  >
                    <img
                      :src="getFolderPreviewThumbs(folder)[0]"
                      :alt="folder.name"
                      class="col-span-2 row-span-2 w-full h-full object-cover"
                      loading="lazy"
                    >
                    <img
                      :src="getFolderPreviewThumbs(folder)[1]"
                      :alt="folder.name"
                      class="w-full h-full object-cover"
                      loading="lazy"
                    >
                    <img
                      :src="getFolderPreviewThumbs(folder)[2]"
                      :alt="folder.name"
                      class="w-full h-full object-cover"
                      loading="lazy"
                    >
                  </div>

                  <div
                    v-else-if="getFolderPreviewThumbs(folder).length === 2"
                    class="w-full h-full grid grid-cols-2 gap-0.5"
                  >
                    <img
                      v-for="(thumb, idx) in getFolderPreviewThumbs(folder)"
                      :key="idx"
                      :src="thumb"
                      :alt="folder.name"
                      class="w-full h-full object-cover"
                      loading="lazy"
                    >
                  </div>

                  <img
                    v-else-if="getFolderPreviewThumbs(folder).length === 1"
                    :src="getFolderPreviewThumbs(folder)[0]"
                    :alt="folder.name"
                    class="w-full h-full object-cover"
                    loading="lazy"
                  >

                  <div
                    v-else
                    class="w-full h-full flex flex-col items-center justify-center gap-1.5 text-ink-subtle"
                  >
                    <FolderOpen class="w-7 h-7 opacity-50" :style="{ color: folder.color || '#6366f1' }" />
                    <span class="text-[11px]">資料なし</span>
                  </div>
                </div>

                <!-- フォルダ情報フッター -->
                <div class="p-3 flex items-center justify-between gap-2 bg-canvas-panel">
                  <div class="flex items-center gap-2 min-w-0">
                    <span
                      class="w-3 h-3 rounded-full shrink-0"
                      :style="{ backgroundColor: folder.color || '#6366f1' }"
                    />
                    <span class="text-xs sm:text-sm font-bold text-ink truncate group-hover:text-brand transition-colors">
                      {{ formatFolderLabel(folder.name) }}
                    </span>
                  </div>

                  <div class="flex items-center gap-1.5 shrink-0">
                    <span
                      class="rounded-full px-2 py-0.5 text-[11px] font-mono font-bold text-ink"
                      :style="chipStyle(folder.color)"
                    >
                      {{ getFolderBookmarks(folder).length }} 件
                    </span>

                    <FolderActionsMenu
                      v-if="isCustomFolder(folder)"
                      :folder="folder"
                      @rename="handleRenameFolder(folder, $event)"
                      @color-change="handleUpdateFolderColor(folder, $event)"
                      @delete="handleDeleteFolder(folder)"
                    />
                  </div>
                </div>
              </div>
            </div>
          </section>

          <!-- 最近追加した資料（プレビュー） -->
          <section v-if="recentBookmarks.length" class="space-y-3 pt-2 border-t border-canvas-border" aria-label="最近追加した資料">
            <div class="flex items-center justify-between gap-2">
              <h2 class="text-sm font-bold text-ink flex items-center gap-2">
                <Bookmark class="w-4 h-4 text-brand" />
                <span>最近追加した資料</span>
              </h2>
              <button
                type="button"
                class="text-xs font-bold text-brand hover:underline flex items-center gap-1"
                @click="selectedFolder = null; switchSection('library')"
              >
                <span>ライブラリですべて見る ({{ boardStore.bookmarks.length }}件)</span>
                <ChevronRight class="w-3.5 h-3.5" />
              </button>
            </div>

            <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 sm:gap-3">
              <figure
                v-for="b in recentBookmarks"
                :key="b.id"
                tabindex="0"
                role="button"
                :aria-label="`${b.title} の詳細プレビューを開く`"
                class="group relative flex flex-col rounded-xl bg-canvas-card border border-canvas-border hover:border-brand transition-colors cursor-pointer overflow-hidden"
                @click="boardStore.openQuickLook(b)"
                @keydown.enter.self.prevent="boardStore.openQuickLook(b)"
                @keydown.space.self.prevent="boardStore.openQuickLook(b)"
              >
                <div class="aspect-square bg-canvas-sunken overflow-hidden">
                  <img
                    :src="resolveThumbnail(b.file_path)"
                    :alt="b.title"
                    class="w-full h-full object-cover"
                    loading="lazy"
                  >
                </div>
                <figcaption class="p-2 bg-canvas-card">
                  <p class="text-[11px] font-semibold text-ink truncate">{{ b.title }}</p>
                  <p class="text-[10px] text-ink-muted truncate">{{ b.folder_name }}</p>
                </figcaption>
              </figure>
            </div>
          </section>
        </div>

        <!-- =========================================================
             2. 検索（スマート総合検索）& 3. ライブラリ（ブックマーク一覧）
             ========================================================= -->
        <div v-else class="space-y-3.5 pb-6">
          <!-- 検索モード用: スマート総合検索パネル -->
          <section
            v-if="activeSection === 'search'"
            class="p-3 sm:p-4 rounded-2xl bg-canvas-panel border border-canvas-border space-y-3"
            aria-label="スマート総合検索"
          >
            <div class="flex items-center justify-between gap-2">
              <h1 class="text-sm sm:text-base font-bold text-ink flex items-center gap-2">
                <Search class="w-4 h-4 text-brand shrink-0" />
                <span>スマート総合検索</span>
              </h1>
              <button
                v-if="hasActiveSearchFilters"
                type="button"
                class="px-2.5 py-1 rounded-lg text-xs font-semibold text-ink-muted hover:text-ink bg-canvas-bg hover:bg-canvas-hover border border-canvas-border transition-colors flex items-center gap-1"
                @click="resetFilters"
              >
                <RotateCcw class="w-3 h-3" />
                <span>条件をクリア</span>
              </button>
            </div>

            <!-- キーワード横断検索入力 -->
            <div class="relative flex items-center">
              <Search class="absolute left-3.5 w-4 h-4 text-ink-muted pointer-events-none" />
              <input
                ref="smartSearchInputRef"
                v-model="searchQuery"
                type="search"
                placeholder="タイトル・作者名・フォルダ・AIタグ・構図・ライティングで横断検索..."
                class="w-full bg-canvas-bg border border-canvas-border-strong rounded-xl pl-10 pr-9 py-2.5 text-xs sm:text-sm text-ink placeholder:text-ink-muted focus:outline-none focus:border-brand transition-colors"
                aria-label="スマート総合検索キーワード"
              >
              <button
                v-if="searchQuery"
                type="button"
                class="absolute right-3 p-1 rounded-full text-ink-muted hover:text-ink transition-colors"
                aria-label="検索キーワードをクリア"
                @click="searchQuery = ''"
              >
                <X class="w-4 h-4" />
              </button>
            </div>

            <!-- ソース別・フォルダ別・並び順フィルタ -->
            <div class="flex flex-wrap items-center justify-between gap-2 pt-1">
              <!-- ソース別ピル -->
              <div class="flex flex-wrap items-center gap-1.5">
                <button
                  v-for="src in SOURCE_VIEWS"
                  :key="src.id"
                  type="button"
                  class="px-2.5 py-1.5 rounded-xl text-xs font-semibold transition-colors flex items-center gap-1.5 border"
                  :class="selectedSource === src.id
                    ? 'bg-brand text-brand-fg border-brand'
                    : 'bg-canvas-bg text-ink border-canvas-border-strong hover:bg-canvas-hover'"
                  @click="selectedSource = src.id"
                >
                  <component :is="src.icon" class="w-3.5 h-3.5 shrink-0" />
                  <span>{{ src.label }}</span>
                </button>
              </div>

              <!-- フォルダ絞り込み + 並び順 -->
              <div class="flex items-center gap-2">
                <select
                  :value="selectedFolder ?? ''"
                  class="bg-canvas-bg border border-canvas-border-strong rounded-xl px-2.5 py-1.5 text-xs font-medium text-ink focus:outline-none focus:border-brand"
                  aria-label="フォルダで絞り込み"
                  @change="selectedFolder = ($event.target as HTMLSelectElement).value || null"
                >
                  <option value="">すべてのフォルダ</option>
                  <option
                    v-for="f in boardStore.folders.filter(item => item.name !== 'All References')"
                    :key="f.name"
                    :value="f.name"
                  >
                    {{ f.name }}
                  </option>
                </select>

                <select
                  v-model="sortOrder"
                  class="bg-canvas-bg border border-canvas-border-strong rounded-xl px-2.5 py-1.5 text-xs font-medium text-ink focus:outline-none focus:border-brand"
                  aria-label="並び順"
                >
                  <option v-for="opt in SORT_OPTIONS" :key="opt.id" :value="opt.id">
                    {{ opt.label }}
                  </option>
                </select>
              </div>
            </div>

            <!-- カラーソート & 色相フィルタ（Color Sort & Filter） -->
            <div class="pt-2.5 border-t border-canvas-border space-y-2">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <p class="text-[11px] font-bold text-ink flex items-center gap-1.5">
                  <Palette class="w-3.5 h-3.5 text-brand shrink-0" />
                  <span>カラーソート・色相検索</span>
                  <span v-if="selectedColor" class="font-mono text-[10px] px-1.5 py-0.5 rounded bg-brand-soft text-brand">
                    {{ selectedColor }} ({{ colorMode === 'sort' ? '近い色順でソート' : '近似色のみ表示' }})
                  </span>
                </p>

                <div class="flex flex-wrap items-center gap-1.5">
                  <!-- クイックカラーソート切替 -->
                  <button
                    type="button"
                    class="px-2 py-1 rounded-lg text-[11px] font-semibold border transition-colors"
                    :class="!selectedColor && sortOrder === 'color_hue'
                      ? 'bg-brand text-brand-fg border-brand font-bold'
                      : 'bg-canvas-bg text-ink border-canvas-border-strong hover:border-brand'"
                    @click="selectedColor = null; sortOrder = sortOrder === 'color_hue' ? 'newest' : 'color_hue'"
                  >
                    🌈 色相スペクトル順
                  </button>
                  <button
                    type="button"
                    class="px-2 py-1 rounded-lg text-[11px] font-semibold border transition-colors"
                    :class="!selectedColor && sortOrder === 'folder_color'
                      ? 'bg-brand text-brand-fg border-brand font-bold'
                      : 'bg-canvas-bg text-ink border-canvas-border-strong hover:border-brand'"
                    @click="selectedColor = null; sortOrder = sortOrder === 'folder_color' ? 'newest' : 'folder_color'"
                  >
                    📁 フォルダカラー順
                  </button>

                  <!-- 特定カラー選択時のソート / 絞り込みモード切替 -->
                  <template v-if="selectedColor">
                    <div class="flex items-center p-0.5 rounded-lg bg-canvas-bg border border-canvas-border-strong">
                      <button
                        type="button"
                        class="px-2 py-0.5 rounded-md text-[10px] font-bold transition-colors"
                        :class="colorMode === 'sort' ? 'bg-brand text-brand-fg' : 'text-ink-muted hover:text-ink'"
                        @click="colorMode = 'sort'"
                      >
                        近い色順ソート
                      </button>
                      <button
                        type="button"
                        class="px-2 py-0.5 rounded-md text-[10px] font-bold transition-colors"
                        :class="colorMode === 'filter' ? 'bg-brand text-brand-fg' : 'text-ink-muted hover:text-ink'"
                        @click="colorMode = 'filter'"
                      >
                        近似色のみ
                      </button>
                    </div>
                    <button
                      type="button"
                      class="px-2 py-1 rounded-lg text-[11px] font-semibold text-ink-muted hover:text-ink bg-canvas-bg border border-canvas-border transition-colors"
                      @click="selectedColor = null"
                    >
                      色解除
                    </button>
                  </template>
                </div>
              </div>

              <!-- プリセットカラースウォッチ + カスタムカラーピッカー -->
              <div class="flex flex-wrap items-center gap-2">
                <button
                  v-for="preset in COLOR_SEARCH_PRESETS"
                  :key="preset.hex"
                  type="button"
                  class="group relative w-6 h-6 rounded-full border transition-transform hover:scale-110 flex items-center justify-center"
                  :class="selectedColor?.toLowerCase() === preset.hex.toLowerCase()
                    ? 'border-ink ring-2 ring-brand scale-110'
                    : 'border-canvas-border-strong'"
                  :style="{ backgroundColor: preset.hex }"
                  :title="`${preset.label} (${preset.hex}) に近い色順でソート`"
                  :aria-label="`${preset.label} (${preset.hex}) でカラーソート`"
                  @click="toggleColorSearch(preset.hex)"
                >
                  <Check
                    v-if="selectedColor?.toLowerCase() === preset.hex.toLowerCase()"
                    class="w-3 h-3 drop-shadow"
                    :class="preset.hex === '#f8fafc' || preset.hex === '#eab308' ? 'text-slate-900' : 'text-white'"
                  />
                </button>

                <!-- 自由な色を指定できるカラーピッカー -->
                <label
                  class="px-2.5 py-1 rounded-full bg-canvas-bg border border-canvas-border-strong hover:border-brand text-[11px] font-semibold text-ink cursor-pointer transition-colors flex items-center gap-1.5"
                  title="任意のカラーを指定してソート"
                >
                  <input
                    type="color"
                    :value="selectedColor || '#6366f1'"
                    class="w-3.5 h-3.5 rounded border-0 bg-transparent p-0 cursor-pointer"
                    aria-label="カスタムカラーでソート"
                    @input="selectedColor = ($event.target as HTMLInputElement).value"
                  >
                  <span>カスタム色</span>
                </label>
              </div>
            </div>

            <!-- AI解析タグのクイックサジェスト -->
            <div v-if="popularAiTags.length" class="pt-2 border-t border-canvas-border space-y-1.5">
              <p class="text-[11px] font-semibold text-ink-muted flex items-center gap-1">
                <Sparkles class="w-3 h-3 text-brand" />
                <span>AI解析タグでクイック検索</span>
              </p>
              <div class="flex flex-wrap gap-1.5">
                <button
                  v-for="item in popularAiTags"
                  :key="item.tag"
                  type="button"
                  class="px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors"
                  :class="searchQuery.trim() === item.tag
                    ? 'bg-brand text-brand-fg border-brand font-bold'
                    : 'bg-canvas-bg text-ink border-canvas-border hover:border-brand'"
                  @click="toggleTagSearch(item.tag)"
                >
                  #{{ item.tag }}
                  <span class="text-[10px] opacity-70 ml-0.5">({{ item.count }})</span>
                </button>
              </div>
            </div>
          </section>

          <!-- ライブラリモード用: シンプルなフォルダ見出し & 切替バー -->
          <section
            v-else
            class="p-3 rounded-2xl bg-canvas-panel border border-canvas-border space-y-2.5"
            aria-label="ライブラリ表示設定"
          >
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div class="flex items-center gap-2 min-w-0">
                <Bookmark class="w-4 h-4 text-brand shrink-0" />
                <h1 class="text-sm sm:text-base font-bold text-ink truncate">
                  {{ selectedFolder || 'すべてのブックマーク' }}
                </h1>
                <span class="text-xs font-mono text-ink-muted shrink-0">
                  ({{ visibleBookmarks.length }} 件)
                </span>
                <button
                  v-if="selectedFolder"
                  type="button"
                  class="px-2 py-0.5 rounded-lg text-[11px] font-semibold bg-canvas-bg hover:bg-canvas-hover text-ink-muted hover:text-ink border border-canvas-border transition-colors"
                  @click="selectedFolder = null"
                >
                  すべて表示に戻す
                </button>
              </div>

              <div class="flex items-center gap-2 shrink-0">
                <div class="relative flex items-center">
                  <ArrowUpDown class="absolute left-2.5 w-3.5 h-3.5 text-ink-muted pointer-events-none" />
                  <select
                    v-model="sortOrder"
                    class="appearance-none bg-canvas-bg border border-canvas-border-strong rounded-xl pl-7 pr-6 py-1.5 text-xs font-medium text-ink focus:outline-none focus:border-brand cursor-pointer"
                    aria-label="資料の並び順"
                  >
                    <option v-for="opt in SORT_OPTIONS" :key="opt.id" :value="opt.id">
                      {{ opt.label }}
                    </option>
                  </select>
                  <ChevronDown class="absolute right-2 w-3.5 h-3.5 text-ink-muted pointer-events-none" />
                </div>

                <div class="flex items-center gap-0.5 p-0.5 rounded-xl border border-canvas-border-strong bg-canvas-bg" role="group" aria-label="表示形式の切り替え">
                  <button
                    type="button"
                    class="p-1.5 rounded-lg transition-colors"
                    :class="viewMode === 'grid' ? 'bg-brand text-brand-fg' : 'text-ink-muted hover:text-ink'"
                    title="グリッド表示"
                    aria-label="グリッド表示"
                    :aria-pressed="viewMode === 'grid'"
                    @click="viewMode = 'grid'"
                  >
                    <LayoutGrid class="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    class="p-1.5 rounded-lg transition-colors"
                    :class="viewMode === 'list' ? 'bg-brand text-brand-fg' : 'text-ink-muted hover:text-ink'"
                    title="リスト表示"
                    aria-label="リスト表示"
                    :aria-pressed="viewMode === 'list'"
                    @click="viewMode = 'list'"
                  >
                    <List class="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>

            <!-- フォルダ検索 ＆ 横スクロールクイック切替バー -->
            <div class="flex items-center gap-2 pt-1">
              <!-- フォルダ内インライン検索 -->
              <div class="relative shrink-0 w-40 sm:w-48">
                <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-ink-muted pointer-events-none" />
                <input
                  v-model="libraryFolderQuery"
                  type="text"
                  placeholder="フォルダ検索..."
                  class="w-full pl-8 pr-7 py-1 text-xs bg-canvas-bg border border-canvas-border-strong rounded-xl text-ink placeholder:text-ink-muted focus:outline-none focus:border-brand transition-colors"
                  @keydown.enter.prevent="selectFirstMatchingLibraryFolder"
                />
                <button
                  v-if="libraryFolderQuery"
                  type="button"
                  class="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 text-ink-muted hover:text-ink transition-colors"
                  title="検索をクリア"
                  aria-label="フォルダ検索をクリア"
                  @click="libraryFolderQuery = ''"
                >
                  <X class="w-3 h-3" />
                </button>
              </div>

              <!-- スクロール左ボタン -->
              <button
                type="button"
                class="hidden sm:flex items-center justify-center w-7 h-7 rounded-lg border border-canvas-border bg-canvas-bg hover:bg-canvas-hover text-ink-muted hover:text-ink shrink-0 transition-colors"
                title="左にスクロール"
                aria-label="フォルダ一覧を左にスクロール"
                @click="scrollLibraryFolders(-160)"
              >
                <ChevronLeft class="w-3.5 h-3.5" />
              </button>

              <!-- 横スクロールコンテナ -->
              <div
                ref="libraryFolderScrollRef"
                class="flex items-center gap-1.5 overflow-x-auto no-scrollbar scroll-smooth flex-1 min-w-0 py-0.5"
              >
                <!-- すべて (All) -->
                <button
                  type="button"
                  class="px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap border transition-colors shrink-0 flex items-center gap-1.5"
                  :class="selectedFolder === null
                    ? 'bg-brand text-brand-fg border-brand shadow-sm'
                    : 'bg-canvas-bg text-ink border-canvas-border hover:bg-canvas-hover'"
                  @click="selectedFolder = null"
                >
                  <span>すべて</span>
                  <span class="text-[10px] font-mono opacity-80">({{ boardStore.bookmarks.length }})</span>
                </button>

                <!-- 各フォルダ -->
                <button
                  v-for="folder in libraryVisibleFolders.filter(f => f.name !== 'All References')"
                  :key="folder.name"
                  type="button"
                  class="px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap border transition-colors flex items-center gap-1.5 shrink-0"
                  :class="selectedFolder === folder.name
                    ? 'bg-brand text-brand-fg border-brand shadow-sm'
                    : 'bg-canvas-bg text-ink border-canvas-border hover:bg-canvas-hover'"
                  @click="selectedFolder = folder.name"
                >
                  <span
                    class="w-2 h-2 rounded-full shrink-0"
                    :style="{ backgroundColor: folder.color || '#6366f1' }"
                  />
                  <span>{{ folder.name }}</span>
                  <span class="text-[10px] font-mono opacity-75">
                    {{ getFolderBookmarks(folder).length }}
                  </span>
                </button>

                <!-- 検索結果が空の場合 -->
                <div
                  v-if="libraryFolderQuery && libraryVisibleFolders.filter(f => f.name !== 'All References').length === 0"
                  class="text-xs text-ink-muted whitespace-nowrap px-2 py-1 flex items-center gap-1.5"
                >
                  <span>一致するフォルダがありません</span>
                  <button
                    type="button"
                    class="text-brand hover:underline font-semibold"
                    @click="libraryFolderQuery = ''"
                  >
                    リセット
                  </button>
                </div>
              </div>

              <!-- スクロール右ボタン -->
              <button
                type="button"
                class="hidden sm:flex items-center justify-center w-7 h-7 rounded-lg border border-canvas-border bg-canvas-bg hover:bg-canvas-hover text-ink-muted hover:text-ink shrink-0 transition-colors"
                title="右にスクロール"
                aria-label="フォルダ一覧を右にスクロール"
                @click="scrollLibraryFolders(160)"
              >
                <ChevronRight class="w-3.5 h-3.5" />
              </button>
            </div>
          </section>

          <!-- 検索モード時の件数・表示切替バー -->
          <div v-if="activeSection === 'search'" class="flex items-center justify-between gap-2 px-1">
            <span class="text-xs font-semibold text-ink-muted" aria-live="polite">
              検索結果: <strong class="text-ink font-mono">{{ visibleBookmarks.length }}</strong> 件
            </span>
            <div class="flex items-center gap-0.5 p-0.5 rounded-xl border border-canvas-border-strong bg-canvas-panel" role="group" aria-label="表示形式の切り替え">
              <button
                type="button"
                class="p-1.5 rounded-lg transition-colors"
                :class="viewMode === 'grid' ? 'bg-brand text-brand-fg' : 'text-ink-muted hover:text-ink'"
                aria-label="グリッド表示"
                :aria-pressed="viewMode === 'grid'"
                @click="viewMode = 'grid'"
              >
                <LayoutGrid class="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                class="p-1.5 rounded-lg transition-colors"
                :class="viewMode === 'list' ? 'bg-brand text-brand-fg' : 'text-ink-muted hover:text-ink'"
                aria-label="リスト表示"
                :aria-pressed="viewMode === 'list'"
                @click="viewMode = 'list'"
              >
                <List class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <!-- ブックマークカード一覧 -->
          <div role="region" aria-label="資料カード一覧">
            <!-- グリッド表示 -->
            <div v-if="viewMode === 'grid'" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2.5 sm:gap-3.5">
              <figure
                v-for="b in visibleBookmarks"
                :key="b.id"
                tabindex="0"
                role="button"
                :aria-label="`${b.title} の詳細プレビューを開く`"
                class="group relative flex flex-col rounded-xl bg-canvas-card border border-canvas-border transition-colors cursor-pointer hover:border-brand/50 focus-visible:border-brand"
                @click="boardStore.openQuickLook(b)"
                @keydown.enter.self.prevent="boardStore.openQuickLook(b)"
                @keydown.space.self.prevent="boardStore.openQuickLook(b)"
              >
                <div class="relative aspect-square bg-canvas-sunken rounded-t-xl overflow-hidden">
                  <img
                    :src="resolveThumbnail(b.file_path)"
                    :alt="b.title"
                    class="w-full h-full object-cover pointer-events-none"
                    loading="lazy"
                  >

                  <!-- ソースバッジ -->
                  <span
                    v-if="b.source_type === 'pixiv'"
                    class="absolute top-2 left-2 px-2 py-0.5 rounded text-[10px] font-bold bg-pixiv text-white"
                  >
                    pixiv
                  </span>
                  <span
                    v-else-if="b.source_type === 'instagram'"
                    class="absolute top-2 left-2 px-2 py-0.5 rounded text-[10px] font-bold bg-instagram text-white flex items-center gap-0.5"
                  >
                    <Instagram class="w-3 h-3" />
                    IG
                  </span>
                  <span
                    v-else
                    class="absolute top-2 left-2 px-2 py-0.5 rounded text-[10px] font-medium bg-canvas-panel/90 text-ink-muted border border-canvas-border"
                  >
                    Web
                  </span>

                  <!-- ホバー・キーボードフォーカス時アクション -->
                  <div
                    class="hidden sm:flex absolute inset-0 bg-canvas-panel/75 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity p-2 flex-col justify-between"
                  >
                    <div class="flex justify-end pr-8">
                      <a
                        v-if="b.source_url"
                        :href="b.source_url"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="p-1.5 rounded-lg bg-canvas-raised text-ink hover:text-pixiv transition-colors"
                        title="元のページを開く"
                        :aria-label="`${b.title} の元のページを開く`"
                        @click.stop
                      >
                        <ExternalLink class="w-3.5 h-3.5" />
                      </a>
                    </div>
                    <button
                      type="button"
                      class="w-full py-1.5 rounded-lg bg-brand text-brand-fg text-[11px] font-bold hover:bg-brand-hover transition-colors flex items-center justify-center gap-1"
                      @click.stop="handlePlaceOnBoard(b)"
                    >
                      <Layers class="w-3 h-3" />
                      キャンバスへ
                    </button>
                  </div>
                </div>

                <div class="absolute top-2 right-2 z-20">
                  <BookmarkActionsMenu
                    :item="b"
                    :folders="boardStore.folders"
                    @place="handlePlaceOnBoard(b)"
                    @move="handleMoveBookmark(b, $event)"
                    @delete="handleDeleteBookmark(b)"
                  />
                </div>

                <figcaption class="p-2.5 rounded-b-xl bg-canvas-card space-y-1.5 flex-1 flex flex-col">
                  <p class="text-[11px] font-bold text-ink truncate" :title="b.title">{{ b.title }}</p>
                  <p class="text-[10px] font-medium text-ink-muted truncate flex items-center gap-1.5">
                    <span
                      class="w-2 h-2 rounded-full shrink-0"
                      :style="{ backgroundColor: getFolderColorByName(b.folder_name) }"
                    />
                    <span class="truncate">{{ b.author_name || b.folder_name }}</span>
                  </p>

                  <div v-if="b.ai_analysis?.palette?.length" class="flex items-center gap-1 mt-auto pt-1">
                    <button
                      v-for="(hex, idx) in b.ai_analysis.palette.slice(0, 5)"
                      :key="idx"
                      type="button"
                      class="w-3 h-3 rounded-full border border-canvas-border hover:scale-125 transition-transform"
                      :class="activeSection === 'search' && selectedColor?.toLowerCase() === hex.toLowerCase() ? 'ring-2 ring-brand scale-125' : ''"
                      :style="{ backgroundColor: hex }"
                      :title="activeSection === 'search' ? `${hex} に近い色順でソート` : `${hex} をコピー`"
                      :aria-label="activeSection === 'search' ? `カラー ${hex} でソート` : `カラーコード ${hex} をコピー`"
                      @click.stop="handleClickPaletteDot(hex)"
                    />
                  </div>
                </figcaption>
              </figure>
            </div>

            <!-- リスト表示 -->
            <div v-else class="space-y-1.5">
              <div
                v-for="b in visibleBookmarks"
                :key="b.id"
                tabindex="0"
                role="button"
                :aria-label="`${b.title} の詳細プレビューを開く`"
                class="group relative flex items-center gap-3 p-2.5 rounded-xl bg-canvas-card border border-canvas-border hover:border-brand focus-visible:border-brand cursor-pointer transition-colors"
                @click="boardStore.openQuickLook(b)"
                @keydown.enter.self.prevent="boardStore.openQuickLook(b)"
                @keydown.space.self.prevent="boardStore.openQuickLook(b)"
              >
                <img
                  :src="resolveThumbnail(b.file_path)"
                  :alt="b.title"
                  class="w-12 h-12 rounded-lg object-cover shrink-0 bg-canvas-sunken"
                  loading="lazy"
                >
                <div class="flex-1 min-w-0">
                  <p class="text-xs font-semibold text-ink truncate">{{ b.title }}</p>
                  <p class="text-[11px] text-ink-subtle truncate flex items-center gap-1.5">
                    <span
                      class="w-2 h-2 rounded-full shrink-0"
                      :style="{ backgroundColor: getFolderColorByName(b.folder_name) }"
                    />
                    <span class="capitalize">{{ b.source_type }}</span> ·
                    <span class="truncate">{{ b.author_name || b.folder_name }}</span>
                  </p>
                </div>

                <div v-if="b.ai_analysis?.palette?.length" class="hidden sm:flex items-center gap-1 shrink-0">
                  <button
                    v-for="(hex, idx) in b.ai_analysis.palette.slice(0, 5)"
                    :key="idx"
                    type="button"
                    class="w-3 h-3 rounded-full border border-canvas-border hover:scale-125 transition-transform"
                    :style="{ backgroundColor: hex }"
                    :title="activeSection === 'search' ? `${hex} に近い色順でソート` : `${hex} をコピー`"
                    @click.stop="handleClickPaletteDot(hex)"
                  />
                </div>

                <a
                  v-if="b.source_url"
                  :href="b.source_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="p-1.5 rounded-lg text-ink-subtle hover:text-pixiv transition-colors shrink-0"
                  aria-label="元のページを開く"
                  @click.stop
                >
                  <ExternalLink class="w-3.5 h-3.5" />
                </a>
                <BookmarkActionsMenu
                  :item="b"
                  :folders="boardStore.folders"
                  @place="handlePlaceOnBoard(b)"
                  @move="handleMoveBookmark(b, $event)"
                  @delete="handleDeleteBookmark(b)"
                />
                <button
                  type="button"
                  class="px-3 py-1.5 rounded-lg bg-brand text-brand-fg text-[11px] font-bold hover:bg-brand-hover transition-colors shrink-0"
                  @click.stop="handlePlaceOnBoard(b)"
                >
                  キャンバスへ
                </button>
              </div>
            </div>

            <!-- 空状態 -->
            <div
              v-if="!visibleBookmarks.length"
              class="py-16 text-center space-y-3 bg-canvas-panel rounded-2xl border border-canvas-border"
            >
              <Bookmark class="w-8 h-8 text-ink-subtle mx-auto" />
              <p class="text-sm font-semibold text-ink">
                {{ boardStore.bookmarks.length ? '条件に一致する資料がありません' : 'ライブラリは空です' }}
              </p>
              <p class="text-xs text-ink-muted">
                {{ boardStore.bookmarks.length ? '検索キーワードやフィルタ条件を変更してください' : '上の入力欄にURLを貼り付けるか、pixivから取り込んでください' }}
              </p>
              <button
                v-if="boardStore.bookmarks.length"
                type="button"
                class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-brand text-brand-fg text-xs font-bold hover:bg-brand-hover transition-colors"
                @click="resetFilters"
              >
                <RotateCcw class="w-3.5 h-3.5" />
                絞り込みをリセット
              </button>
              <NuxtLink
                v-else
                to="/view"
                class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-pixiv text-white text-xs font-bold hover:bg-pixiv-hover transition-colors"
              >
                <Compass class="w-3.5 h-3.5" />
                pixivで作品を探す
              </NuxtLink>
            </div>
          </div>
        </div>
      </main>
    </div>

    <QuickLookModal />
  </div>
</template>
