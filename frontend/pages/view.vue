<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import {
  Search,
  Bookmark,
  ExternalLink,
  Layers,
  Compass,
  X,
  RefreshCw,
  LogOut,
  Link2,
  Check,
  ChevronLeft,
  ChevronRight,
  Info,
  Eye,
  Images,
  Sparkles,
  Trophy,
  Users,
  Menu,
  Settings2,
  SlidersHorizontal,
  Folder,
  CheckSquare,
} from 'lucide-vue-next'
import AppHeader from '~/components/ui/AppHeader.vue'
import MobileNavLinks from '~/components/ui/MobileNavLinks.vue'
import PixivImage from '~/components/ui/PixivImage.vue'
import QuickLookModal from '~/components/browser/QuickLookModal.vue'
import FolderSelectDropdown from '~/components/ui/FolderSelectDropdown.vue'
import BookmarkActionsMenu from '~/components/ui/BookmarkActionsMenu.vue'
import type { BookmarkItem } from '~/types'
import { useBoardStore } from '~/stores/boardStore'
import { usePixiv, type PixivArtwork } from '~/composables/usePixiv'
import { useBackendUrl } from '~/composables/useBackendUrl'
import { useMediaUrl } from '~/composables/useMediaUrl'
import { useToast } from '~/composables/useToast'
import { useMobileNav } from '~/composables/useMobileNav'

const boardStore = useBoardStore()
const pixiv = usePixiv()
const toast = useToast()
const { apiBase } = useBackendUrl()
const { resolveMediaUrl } = useMediaUrl()
const { isOpen: isSidebarOpen } = useMobileNav()

const searchInput = ref('')
const viewMainRef = ref<HTMLElement | null>(null)
const activeCategory = ref('recommended')
const isFilterModalOpen = ref(false)
const selectedTargetFolder = ref<string>('All References')
const selectedSavedFolderFilter = ref<string | null>(null)
const dragOverSavedFolder = ref<string | null>(null)

function formatFolderLabel(name?: string | null): string {
  if (!name || name === 'All References') return 'すべての資料'
  return name
}

const activeCategoryLabel = computed(
  () => CATEGORIES.find(c => c.id === activeCategory.value)?.label || 'おすすめ'
)
const savedBookmarks = computed(() => {
  const query = searchInput.value.trim().toLowerCase()
  let list = boardStore.bookmarks.filter(item => item.source_type === 'pixiv')
  if (selectedSavedFolderFilter.value && selectedSavedFolderFilter.value !== 'All References') {
    list = list.filter(item => item.folder_name === selectedSavedFolderFilter.value)
  }
  return query
    ? list.filter(item => [item.title, item.author_name || '', item.source_url || '', item.folder_name || ''].join(' ').toLowerCase().includes(query))
    : list
})
const savedPixivIds = computed(() => new Set(
  boardStore.bookmarks
    .filter(item => item.source_type === 'pixiv')
    .map(item => item.source_url?.match(/pixiv\.net\/artworks\/(\d+)/)?.[1])
    .filter((id): id is string => !!id)
))
const activeArtwork = ref<PixivArtwork | null>(null)
const detailPages = ref<{ image_url: string; width: number; height: number }[]>([])
const activePageIndex = ref(0)
const isDetailLoading = ref(false)
const isStashing = ref(false)
const isPlacing = ref(false)

// 検索フィルタ（pixiv API の sort / duration に対応）
const sortMode = ref<'date_desc' | 'date_asc' | 'popular_desc'>('date_desc')
const durationMode = ref<'' | 'within_last_day' | 'within_last_week' | 'within_last_month'>('')

const SORT_OPTIONS = [
  { id: 'date_desc', label: '新着順' },
  { id: 'popular_desc', label: '人気順' },
  { id: 'date_asc', label: '古い順' },
] as const

const DURATION_OPTIONS = [
  { id: '', label: '期間指定なし' },
  { id: 'within_last_day', label: '24時間以内' },
  { id: 'within_last_week', label: '1週間以内' },
  { id: 'within_last_month', label: '1ヶ月以内' },
] as const

const CATEGORIES = [
  { id: 'recommended', label: 'おすすめ', hint: 'pixivおすすめ', icon: Sparkles, requiresAuth: false },
  { id: 'ranking', label: '人気', hint: 'デイリーランキング', icon: Trophy, requiresAuth: false },
  { id: 'following', label: 'フォロー', hint: 'フォロー中の作家の作品', icon: Users, requiresAuth: true },
  { id: 'saved', label: 'ブックマーク', hint: 'RefLensに保存したpixiv作品', icon: Bookmark, requiresAuth: false },
  { id: 'bookmarks', label: 'Pixivのブクマ', hint: 'Pixivアカウントの公開ブックマーク', icon: Bookmark, requiresAuth: true },
  { id: 'search', label: '検索', hint: 'キーワード検索', icon: Search, requiresAuth: false },
]

let detailTouchStartX = 0
let detailTouchStartY = 0

function onDetailTouchStart(e: TouchEvent) {
  if (e.touches.length !== 1) return
  detailTouchStartX = e.touches[0].clientX
  detailTouchStartY = e.touches[0].clientY
}

function onDetailTouchEnd(e: TouchEvent) {
  if (e.changedTouches.length !== 1 || currentPageImages.value.length <= 1) return
  const dx = e.changedTouches[0].clientX - detailTouchStartX
  const dy = e.changedTouches[0].clientY - detailTouchStartY
  if (Math.abs(dx) > 48 && Math.abs(dx) > Math.abs(dy) * 1.4) {
    if (dx > 0 && activePageIndex.value > 0) activePageIndex.value--
    else if (dx < 0 && activePageIndex.value < currentPageImages.value.length - 1) activePageIndex.value++
  }
}

function openAccountSwitcher() {
  window.dispatchEvent(new Event('reflens:auth-switch'))
}

/** ログインが必要なカテゴリは、未接続時は押せないようにする */
function isCategoryDisabled(cat: (typeof CATEGORIES)[number]) {
  return cat.requiresAuth && !pixiv.isConnected.value
}

const currentPageImages = computed(() =>
  detailPages.value.length
    ? detailPages.value
    : activeArtwork.value
      ? [{ image_url: activeArtwork.value.original_url || activeArtwork.value.image_url, width: 0, height: 0 }]
      : []
)

const activePageImage = computed(() => currentPageImages.value[activePageIndex.value] || null)

function submitSearch() {
  if (activeCategory.value === 'saved') return
  activeCategory.value = 'search'
  pixiv.setQuery(searchInput.value)
  pixiv.loadFeed('search', 1)
}

function pickCategory(id: string) {
  const cat = CATEGORIES.find(c => c.id === id)
  if (cat && isCategoryDisabled(cat)) return

  activeCategory.value = id
  pixiv.clearSelection()
  if (id === 'saved') {
    boardStore.fetchBookmarks()
  } else if (id === 'search') {
    submitSearch()
  } else {
    pixiv.loadFeed(id, 1)
  }
  // モバイルではハンバーガーメニューを閉じて結果を全面表示させる
  if (window.matchMedia('(max-width: 767px)').matches) isSidebarOpen.value = false
}

/** ソート / 期間を変更したら再読み込み（検索カテゴリのときだけ有効） */
function applyFilters() {
  activeCategory.value = 'search'
  pixiv.sort.value = sortMode.value
  pixiv.duration.value = durationMode.value
  pixiv.loadFeed('search', 1)
}

async function openDetail(item: PixivArtwork) {
  activeArtwork.value = item
  activePageIndex.value = 0
  detailPages.value = []
  isDetailLoading.value = true

  // ログイン中は詳細APIから全ページ画像を取得する
  if (pixiv.isConnected.value) {
    try {
      const detail = await $fetch<PixivArtwork & { pages?: any[] }>(
        `${apiBase.value}/pixiv/illust/${item.id}`
      )
      detailPages.value = (detail.pages || []).map(page => ({ ...page, image_url: pixiv.proxyImage(page.image_url) }))
      if (detail.title) activeArtwork.value = {
        ...item, ...detail,
        image_url: pixiv.proxyImage(detail.image_url),
        original_url: pixiv.proxyImage(detail.original_url),
      }
    } catch {
      // 詳細取得に失敗しても一覧のサムネイルでの表示は成立させる
    }
  }
  isDetailLoading.value = false
}

function closeDetail() {
  activeArtwork.value = null
  detailPages.value = []
  activePageIndex.value = 0
}

const isMultiSelectMode = ref(false)

function toggleMultiSelectMode() {
  isMultiSelectMode.value = !isMultiSelectMode.value
  if (!isMultiSelectMode.value && pixiv.selectedIds.value.length > 0) {
    // keeping selection is okay, or user can clear from floating bar
  }
}

function handleCardClick(item: PixivArtwork) {
  if (isMultiSelectMode.value || pixiv.selectedIds.value.length > 0) {
    toggleSelect(item.id)
  } else {
    openDetail(item)
  }
}

function toggleSelect(id: string) {
  pixiv.toggleSelection(id)
}

const allSelected = computed(
  () => pixiv.items.value.length > 0 && pixiv.selectedIds.value.length === pixiv.items.value.length
)

function toggleSelectAll() {
  if (allSelected.value) {
    pixiv.clearSelection()
  } else {
    pixiv.clearSelection()
    pixiv.items.value.forEach(i => pixiv.selectedIds.value.push(i.id))
  }
}

async function ensureBoardId(): Promise<string | null> {
  if (boardStore.currentBoard?.id) return boardStore.currentBoard.id

  try {
    const boards = await $fetch<{ id: string }[]>(`${apiBase.value}/boards/`)
    if (boards?.length) {
      await boardStore.loadBoard(boards[0].id)
      return boards[0].id
    }
  } catch {
    /* fallback */
  }
  return null
}

async function handleStashDetail() {
  if (activeArtwork.value) await handleStash(activeArtwork.value)
}

async function handleStash(artwork?: PixivArtwork) {
  const ids = artwork ? [artwork.id] : [...pixiv.selectedIds.value]
  if (!ids.length) return

  isStashing.value = true
  const targetFolder = selectedTargetFolder.value || 'All References'
  const count = await pixiv.stockToLibrary(ids, targetFolder)
  isStashing.value = false

  if (!count) return

  await boardStore.fetchBookmarks()
  await boardStore.fetchFolders()
  const label = formatFolderLabel(targetFolder)
  toast.success(`${count} 作品を「${label}」に保存しました`)
  if (artwork) {
    closeDetail()
  } else {
    pixiv.clearSelection()
  }
}

async function handleMoveBookmark(item: BookmarkItem, folderName: string) {
  const moved = await boardStore.moveBookmarkFolder(item.id, folderName)
  if (moved) toast.success(`「${item.title}」を ${formatFolderLabel(folderName)} へ移動しました`)
}

async function handleDeleteBookmark(item: BookmarkItem) {
  const deleted = await boardStore.deleteBookmark(item.id)
  if (deleted) toast.success('ブックマークを削除しました')
}

function onBookmarkDragStart(event: DragEvent, item: BookmarkItem) {
  if (!event.dataTransfer) return
  event.dataTransfer.effectAllowed = 'copyMove'
  event.dataTransfer.setData('application/reflens-bookmark-id', item.id)
  event.dataTransfer.setData('text/plain', item.id)
}

async function onDropBookmarkOnSavedFolder(folderName: string, event: DragEvent) {
  dragOverSavedFolder.value = null
  if (!event.dataTransfer) return
  const bookmarkId = event.dataTransfer.getData('application/reflens-bookmark-id') || event.dataTransfer.getData('text/plain')
  if (!bookmarkId) return

  const item = boardStore.bookmarks.find(b => b.id === bookmarkId)
  if (!item) return
  if (item.folder_name === folderName) return

  await handleMoveBookmark(item, folderName)
}

async function placeSelectedOnCanvas() {
  await handlePlaceOnCanvas()
}

async function stashSelected() {
  await handleStash()
}

async function placeActiveOnCanvas() {
  if (activeArtwork.value) await handlePlaceOnCanvas(activeArtwork.value)
}

async function handlePlaceOnCanvas(artwork?: PixivArtwork) {
  const ids = artwork ? [artwork.id] : [...pixiv.selectedIds.value]
  if (!ids.length) return

  const boardId = await ensureBoardId()
  if (!boardId) {
    toast.error('キャンバスボードが見つかりません', 'Manager で先にボードを作成してください')
    return
  }

  isPlacing.value = true
  const targetFolder = selectedTargetFolder.value || 'All References'
  const count = await pixiv.stockToCanvas(ids, boardId, undefined, undefined, targetFolder)
  isPlacing.value = false

  if (!count) return

  toast.success(`${count} 作品をキャンバスへ配置しました`)
  if (artwork) closeDetail()
  else pixiv.clearSelection()

  await navigateTo(`/board/${boardId}`)
}

function copyUrl(id: string) {
  navigator.clipboard.writeText(`https://www.pixiv.net/artworks/${id}`)
  toast.success('作品URLをコピーしました')
}

function formatCount(n: number) {
  if (n >= 10000) return `${(n / 1000).toFixed(0)}k`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

async function onAuthChanged() {
  const category = activeCategory.value
  pixiv.clearSelection()
  await pixiv.fetchStatus()
  if (category === 'saved') {
    await boardStore.fetchBookmarks()
  } else {
    activeCategory.value = pixiv.isConnected.value ? category : 'recommended'
    await pixiv.loadFeed(activeCategory.value, 1)
  }
}

function onViewKeyDown(e: KeyboardEvent) {
  if (activeArtwork.value) {
    if (e.key === 'Escape') {
      e.preventDefault()
      closeDetail()
    } else if (e.key === 'ArrowLeft' && activePageIndex.value > 0) {
      e.preventDefault()
      activePageIndex.value--
    } else if (e.key === 'ArrowRight' && activePageIndex.value < currentPageImages.value.length - 1) {
      e.preventDefault()
      activePageIndex.value++
    }
  } else if (e.key === 'Escape' && isSidebarOpen.value) {
    isSidebarOpen.value = false
  }
}

onMounted(async () => {
  await pixiv.init()
  boardStore.fetchBookmarks()

  // ログイン / ログアウトでユーザーごとに変わる
  // pixiv の接続状態（トークンはユーザーごとに持つ）を取り直す
  window.addEventListener('reflens:auth-changed', onAuthChanged)
  window.addEventListener('keydown', onViewKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('reflens:auth-changed', onAuthChanged)
  window.removeEventListener('keydown', onViewKeyDown)
})
</script>

<template>
  <div class="h-app-screen overflow-hidden bg-canvas-bg text-ink flex flex-col antialiased">
    <AppHeader class="shrink-0" />

    <!-- ワークスペース: サイドバー + メイン（検索バー・作品グリッド一体スクロール） -->
    <div class="flex-1 min-h-0 flex max-w-[1600px] w-full mx-auto overflow-hidden">
      <!-- サイドバー: ナビゲーション（モバイル）+ カテゴリ + 検索フィルタ -->
      <aside
        class="shrink-0 overflow-y-auto overscroll-contain"
        :class="isSidebarOpen
          ? 'fixed inset-x-0 top-14 bottom-0 z-40 w-full h-[calc(100dvh-3.5rem)] bg-canvas-panel border-t border-canvas-border shadow-pop p-4 pb-10 md:static md:w-64 md:h-full md:border-t-0 md:border-r md:border-canvas-border md:bg-canvas-panel md:shadow-none md:p-0'
          : 'hidden md:block md:w-64 md:h-full md:border-r md:border-canvas-border md:bg-canvas-panel'"
        aria-label="pixivカテゴリ"
      >
        <div class="md:p-3.5 space-y-4">
          <div class="md:hidden pb-3 border-b border-canvas-border">
            <MobileNavLinks :show-site-links="true" />
          </div>
          <!-- カテゴリ -->
          <nav class="space-y-1">
            <p class="text-[10px] font-mono font-semibold text-ink-muted uppercase tracking-wider px-1.5 mb-1.5">
              Browse
            </p>
            <button
              v-for="cat in CATEGORIES"
              :key="cat.id"
              type="button"
              class="w-full flex items-center gap-2.5 px-3 py-2.5 md:py-2 rounded-xl text-xs transition-colors text-left"
              :class="activeCategory === cat.id
                ? 'bg-brand text-brand-fg font-bold shadow-sm'
                : 'text-ink hover:bg-canvas-hover font-semibold'"
              :disabled="isCategoryDisabled(cat)"
              :title="isCategoryDisabled(cat) ? 'Pixivに接続すると利用できます' : cat.hint"
              :aria-current="activeCategory === cat.id ? 'page' : undefined"
              @click="pickCategory(cat.id)"
            >
              <component :is="cat.icon" class="w-4 h-4 shrink-0" :class="activeCategory === cat.id ? 'text-brand-fg' : 'text-ink-muted'" />
              <span class="flex-1">{{ cat.label }}</span>
              <span
                v-if="isCategoryDisabled(cat)"
                class="text-[10px] shrink-0"
                :class="activeCategory === cat.id ? 'text-brand-fg/80' : 'text-ink-muted'"
              >要ログイン</span>
            </button>
          </nav>

          <!-- 検索フィルタ（検索カテゴリのときだけ有効） -->
          <div class="pt-3 border-t border-canvas-border space-y-3">
            <p class="text-[10px] font-mono font-semibold text-ink-muted uppercase tracking-wider px-1.5 flex items-center gap-1">
              <SlidersHorizontal class="w-3 h-3" />
              Filters
            </p>

            <fieldset :disabled="activeCategory !== 'search'" class="space-y-2.5 disabled:opacity-40">
              <legend class="sr-only">ソート順</legend>
              <div>
                <p class="text-[11px] font-medium text-ink-muted mb-1 px-1">並び順</p>
                <div class="space-y-1">
                  <label
                    v-for="opt in SORT_OPTIONS"
                    :key="opt.id"
                    class="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs md:text-[11px] cursor-pointer hover:bg-canvas-hover transition-colors"
                    :class="sortMode === opt.id ? 'text-brand font-bold bg-brand-soft/60' : 'text-ink font-medium'"
                  >
                    <input
                      v-model="sortMode"
                      type="radio"
                      :value="opt.id"
                      class="accent-[var(--accent-default)]"
                      @change="applyFilters"
                    >
                    {{ opt.label }}
                  </label>
                </div>
              </div>

              <div>
                <p class="text-[11px] font-medium text-ink-muted mb-1 px-1">投稿期間</p>
                <select
                  v-model="durationMode"
                  class="w-full bg-canvas-bg border border-canvas-border-strong rounded-xl px-2.5 py-2 text-xs md:text-[11px] font-medium text-ink focus:outline-none focus:border-pixiv transition-colors"
                  aria-label="投稿期間"
                  @change="applyFilters"
                >
                  <option v-for="opt in DURATION_OPTIONS" :key="opt.id" :value="opt.id">
                    {{ opt.label }}
                  </option>
                </select>
              </div>
            </fieldset>
          </div>

          <!-- 接続状態 -->
          <div class="pt-3 border-t border-canvas-border">
            <p class="text-[10px] font-mono font-semibold text-ink-muted uppercase tracking-wider px-1.5 mb-1.5">
              Account
            </p>
            <div v-if="pixiv.isConnected.value" class="px-3 py-2.5 rounded-xl bg-canvas-bg border border-canvas-border-strong">
              <div class="flex items-center gap-2">
                <PixivImage
                  v-if="pixiv.status.value?.account?.avatar_url"
                  :src="pixiv.proxyImage(pixiv.status.value.account.avatar_url)"
                  :alt="pixiv.accountName.value"
                  class="w-6 h-6 rounded-full shrink-0"
                />
                <div class="min-w-0">
                  <p class="text-xs font-semibold text-ink truncate">{{ pixiv.accountName.value }}</p>
                  <p v-if="pixiv.status.value?.account?.account" class="text-[10px] text-ink-muted truncate">
                    @{{ pixiv.status.value.account.account }}
                  </p>
                </div>
              </div>
            </div>
            <div v-else class="px-3 py-2.5 rounded-xl bg-canvas-bg border border-canvas-border-strong space-y-2">
              <p class="text-xs text-ink leading-relaxed">
                {{ pixiv.statusMessage.value || 'デモフィードを表示中' }}
              </p>
              <button
                v-if="pixiv.canConnect.value"
                type="button"
                class="w-full py-2 rounded-lg bg-pixiv text-white text-xs font-bold hover:bg-pixiv-hover transition-colors"
                @click="pixiv.connect()"
              >
                Pixivでログイン
              </button>
            </div>
          </div>
        </div>
      </aside>

      <!-- メイン: 接続状態・検索バー + 作品グリッド（一体でスクロール） -->
      <main id="main-content" ref="viewMainRef" tabindex="-1" class="flex-1 min-h-0 overflow-y-auto px-3 sm:px-4 md:px-6 pt-2.5 sm:pt-4 pb-8 min-w-0 space-y-3 sm:space-y-4 focus:outline-none">
        <!-- 検索・カテゴリ・フィルタパネル（モバイルでも見切れず操作しやすい2段構成） -->
        <section class="p-2.5 sm:p-3.5 rounded-2xl border border-canvas-border bg-canvas-panel space-y-2.5" aria-label="pixiv検索と絞り込み">
          <!-- 上段: ステータス + モーダル起動ボタン + 再読み込み -->
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-1.5 sm:gap-2 min-w-0">
              <span class="px-2 py-0.5 rounded-md text-[11px] font-bold bg-pixiv text-white font-mono shrink-0">
                pixiv
              </span>
              <span class="text-xs font-bold text-ink truncate">
                {{ activeCategoryLabel }}
              </span>
              <span
                v-if="pixiv.isConnected.value"
                class="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-canvas-bg border border-canvas-border text-[11px] text-ink-muted truncate max-w-[160px]"
              >
                <span class="w-1.5 h-1.5 rounded-full bg-ok shrink-0" />
                <span class="truncate">{{ pixiv.accountName.value }}</span>
              </span>
            </div>

            <div class="flex items-center gap-1.5 shrink-0">
              <button
                v-if="activeCategory !== 'saved'"
                type="button"
                class="px-2.5 py-1.5 rounded-xl text-[11px] font-semibold border transition-all flex items-center gap-1.5 whitespace-nowrap"
                :class="isMultiSelectMode || pixiv.selectedIds.value.length
                  ? 'bg-pixiv text-white border-pixiv shadow-sm font-bold'
                  : 'bg-canvas-bg hover:bg-canvas-hover text-ink border-canvas-border-strong'"
                @click="toggleMultiSelectMode"
              >
                <CheckSquare class="w-3.5 h-3.5 shrink-0" />
                <span>{{ isMultiSelectMode || pixiv.selectedIds.value.length ? '複数選択中' : '複数選択' }}</span>
              </button>

              <button
                type="button"
                class="px-2.5 py-1.5 rounded-xl text-[11px] font-semibold bg-canvas-bg hover:bg-canvas-hover text-ink border border-canvas-border-strong transition-colors flex items-center gap-1.5 whitespace-nowrap"
                @click="isFilterModalOpen = true"
              >
                <SlidersHorizontal class="w-3.5 h-3.5 text-pixiv shrink-0" />
                <span>絞り込み・連携</span>
              </button>

              <button
                type="button"
                class="p-1.5 rounded-xl bg-canvas-bg hover:bg-canvas-hover text-ink-muted hover:text-ink border border-canvas-border-strong transition-colors shrink-0"
                title="再読み込み"
                aria-label="再読み込み"
                @click="activeCategory === 'saved' ? boardStore.fetchBookmarks() : pixiv.loadFeed()"
              >
                <RefreshCw class="w-4 h-4" :class="activeCategory !== 'saved' && pixiv.isLoading.value ? 'animate-spin text-pixiv' : ''" />
              </button>
            </div>
          </div>

          <!-- 中段: フル幅検索バー（モバイルでも見切れない） -->
          <form
            class="relative flex items-center min-w-0"
            @submit.prevent="submitSearch"
          >
            <Search class="absolute left-3 w-3.5 h-3.5 text-ink-subtle pointer-events-none" />
            <input
              v-model="searchInput"
              type="search"
              :placeholder="activeCategory === 'saved' ? '保存済みpixivを検索...' : 'タグ・キーワードで検索...'"
              class="w-full bg-canvas-card border border-canvas-border rounded-xl pl-8 pr-20 py-1.5 sm:py-2 text-xs text-ink placeholder:text-ink-subtle focus:outline-none focus:border-pixiv transition-colors"
              aria-label="pixiv作品を検索"
            >
            <button
              v-if="searchInput"
              type="button"
              class="absolute right-14 p-1 text-ink-subtle hover:text-ink transition-colors"
              aria-label="検索をクリア"
              @click="searchInput = ''"
            >
              <X class="w-3.5 h-3.5" />
            </button>
            <button
              type="submit"
              class="absolute right-1.5 px-2.5 py-1 rounded-lg bg-pixiv text-white hover:bg-pixiv-hover text-[11px] font-bold transition-colors"
            >
              検索
            </button>
          </form>

          <!-- 下段（モバイル向けクイックカテゴリ切替） -->
          <div class="md:hidden flex items-center gap-1.5 overflow-x-auto no-scrollbar pt-0.5">
            <button
              v-for="cat in CATEGORIES"
              :key="cat.id"
              type="button"
              class="px-2.5 py-1 rounded-lg text-[11px] font-semibold whitespace-nowrap transition-colors flex items-center gap-1 border shrink-0 disabled:opacity-40"
              :class="activeCategory === cat.id
                ? 'bg-pixiv text-white border-pixiv'
                : 'bg-canvas-bg text-ink border-canvas-border'"
              :disabled="isCategoryDisabled(cat)"
              @click="pickCategory(cat.id)"
            >
              <component :is="cat.icon" class="w-3 h-3 shrink-0" />
              <span>{{ cat.label }}</span>
            </button>
          </div>
        </section>
      <!-- 通知バー -->
      <div
        v-if="activeCategory !== 'saved' && pixiv.notice.value"
        class="mb-4 flex items-start gap-2 p-3 rounded-xl border border-canvas-border bg-canvas-card"
      >
        <Info class="w-3.5 h-3.5 text-ink-subtle shrink-0 mt-px" />
        <p class="text-[11px] text-ink-muted leading-relaxed">{{ pixiv.notice.value }}</p>
      </div>

      <!-- RefLensに保存したブックマーク -->
      <div v-if="activeCategory === 'saved'" class="space-y-3">
        <!-- フォルダ絞り込み & ドラッグ＆ドロップ先ピル -->
        <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-1">
          <span class="text-[11px] font-bold text-ink-muted flex items-center gap-1 shrink-0 mr-1">
            <Folder class="w-3.5 h-3.5 text-brand" />
            <span>フォルダ:</span>
          </span>
          <button
            v-for="folder in boardStore.folders"
            :key="folder.name"
            type="button"
            class="px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap border transition-all flex items-center gap-1.5 shrink-0"
            :class="[
              (selectedSavedFolderFilter === folder.name || (!selectedSavedFolderFilter && folder.name === 'All References'))
                ? 'bg-brand text-brand-fg border-brand font-bold shadow-sm'
                : 'bg-canvas-card text-ink border-canvas-border hover:border-canvas-border-strong',
              dragOverSavedFolder === folder.name ? 'ring-2 ring-brand scale-105 bg-brand-soft text-brand' : ''
            ]"
            @click="selectedSavedFolderFilter = folder.name === 'All References' ? null : (selectedSavedFolderFilter === folder.name ? null : folder.name)"
            @dragover.prevent="dragOverSavedFolder = folder.name"
            @dragleave="dragOverSavedFolder = null"
            @drop.prevent="onDropBookmarkOnSavedFolder(folder.name, $event)"
          >
            <span class="w-2 h-2 rounded-full shrink-0" :style="{ backgroundColor: folder.color || '#6366f1' }" />
            <span>{{ formatFolderLabel(folder.name) }}</span>
            <span class="text-[10px] opacity-75 font-mono">
              {{ folder.name === 'All References' ? boardStore.bookmarks.filter(b => b.source_type === 'pixiv').length : (folder.count ?? 0) }}
            </span>
          </button>
        </div>

        <div v-if="!savedBookmarks.length" class="py-24 text-center space-y-3">
          <Bookmark class="w-8 h-8 text-ink-subtle mx-auto" />
          <p class="text-sm text-ink-muted">{{ searchInput ? '検索に一致するpixiv作品がありません' : 'RefLensに保存したpixiv作品はありません' }}</p>
          <p class="text-xs text-ink-subtle">{{ searchInput ? '検索語を変えてください' : 'Pixiv作品の「ライブラリへ保存」で追加できます' }}</p>
        </div>
        <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          <article
            v-for="item in savedBookmarks"
            :key="item.id"
            tabindex="0"
            role="button"
            draggable="true"
            :aria-label="`${item.title} のプレビューを開く`"
            class="group relative rounded-xl border border-canvas-border bg-canvas-card overflow-hidden cursor-grab active:cursor-grabbing hover:border-canvas-border-strong focus-visible:border-brand transition-colors"
            @dragstart="onBookmarkDragStart($event, item)"
            @click="boardStore.openQuickLook(item)"
            @keydown.enter.self.prevent="boardStore.openQuickLook(item)"
            @keydown.space.self.prevent="boardStore.openQuickLook(item)"
          >
            <div class="relative aspect-[4/3] bg-canvas-sunken overflow-hidden">
              <img :src="resolveMediaUrl(item.file_path)" :alt="item.title" class="w-full h-full object-cover pointer-events-none" loading="lazy">
              <span class="absolute top-2 left-2 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-canvas-panel/90 text-ink">pixiv</span>
              <!-- 三点メニュー（フォルダ変更・キャンバス配置・削除） -->
              <div class="absolute top-2 right-2 z-10" @click.stop>
                <BookmarkActionsMenu
                  :item="item"
                  :folders="boardStore.folders"
                  @place="handlePlaceOnCanvas(item)"
                  @move="handleMoveBookmark(item, $event)"
                  @delete="handleDeleteBookmark(item)"
                />
              </div>
            </div>
            <div class="p-2.5 space-y-1">
              <h3 class="text-[11px] font-semibold text-ink line-clamp-2" :title="item.title">{{ item.title }}</h3>
              <p class="text-[10px] text-ink-subtle truncate flex items-center gap-1">
                <span>{{ item.author_name || item.source_url }}</span>
                <span v-if="item.folder_name && item.folder_name !== 'All References'" class="px-1 py-0.2 bg-canvas-sunken rounded text-[9px] font-medium text-brand">
                  {{ item.folder_name }}
                </span>
              </p>
            </div>
          </article>
        </div>
      </div>

      <!-- Pixivフィード -->
      <div v-else-if="pixiv.isLoading.value" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <div v-for="i in 8" :key="i" class="rounded-xl bg-canvas-card animate-pulse aspect-[4/3]" />
      </div>

      <!-- 空 -->
      <div v-else-if="!pixiv.items.value.length" class="py-24 text-center space-y-3">
        <Compass class="w-8 h-8 text-ink-subtle mx-auto" />
        <p class="text-sm text-ink-muted">{{ pixiv.feedError.value ? 'pixivの取得に失敗しました' : pixiv.currentCategory.value === 'bookmarks' ? 'このPixivアカウントの公開ブックマークはありません' : '作品が見つかりませんでした' }}</p>
        <p class="text-xs text-ink-subtle">{{ pixiv.feedError.value || (pixiv.currentCategory.value === 'bookmarks' ? `連携先: ${pixiv.accountName.value || '未接続'}。別のRefLensアカウントにPixivを連携済みなら、アカウントを切り替えてください。` : 'キーワードを変えて検索してみてください') }}</p>
        <button v-if="!pixiv.feedError.value && pixiv.currentCategory.value === 'bookmarks'" type="button" class="px-3 py-1.5 rounded-lg bg-pixiv text-white text-xs font-semibold hover:bg-pixiv-hover" @click="openAccountSwitcher">RefLensアカウントを切り替える</button>
      </div>

      <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <article
          v-for="item in pixiv.items.value"
          :key="item.id"
          tabindex="0"
          role="button"
          :aria-label="`${item.title} の詳細を開く`"
          class="group flex flex-col rounded-xl border bg-canvas-card overflow-hidden transition-colors cursor-pointer"
          :class="pixiv.isSelected(item.id)
            ? 'border-pixiv ring-2 ring-pixiv/40'
            : 'border-canvas-border hover:border-canvas-border-strong focus-visible:border-pixiv'"
          @click="handleCardClick(item)"
          @keydown.enter.self.prevent="handleCardClick(item)"
          @keydown.space.self.prevent="handleCardClick(item)"
        >
          <!-- サムネイル -->
          <div class="relative aspect-[4/3] bg-canvas-sunken overflow-hidden">
            <PixivImage
              :src="item.image_url"
              :alt="item.title"
              class="w-full h-full object-cover pointer-events-none"
              loading="lazy"
            />

            <!-- 選択チェック（複数選択中や選択済みは常時表示、通常時はホバー表示） -->
            <button
              type="button"
              class="absolute top-2 right-2 z-20 w-6 h-6 sm:w-5 sm:h-5 rounded-full border flex items-center justify-center transition-all shadow-sm"
              :class="pixiv.isSelected(item.id)
                ? 'bg-pixiv border-pixiv opacity-100'
                : (isMultiSelectMode || pixiv.selectedIds.value.length
                  ? 'bg-canvas-panel/90 border-canvas-border-strong opacity-100 hover:border-pixiv'
                  : 'bg-canvas-panel/90 border-canvas-border-strong opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100')"
              :aria-label="pixiv.isSelected(item.id) ? '選択解除' : '選択'"
              :aria-pressed="pixiv.isSelected(item.id)"
              @click.stop="toggleSelect(item.id)"
            >
              <Check v-if="pixiv.isSelected(item.id)" class="w-3.5 h-3.5 sm:w-3 sm:h-3 text-white stroke-[3]" />
            </button>

            <!-- バッジ -->
            <div class="absolute top-2 left-2 flex items-center gap-1.5">
              <span
                v-if="savedPixivIds.has(item.id)"
                class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-pixiv text-white"
              >RefLens保存済み</span>
              <span
                v-if="item.page_count > 1"
                class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-canvas-panel/90 text-ink border border-canvas-border flex items-center gap-0.5"
              >
                <Images class="w-2.5 h-2.5" />
                {{ item.page_count }}
              </span>
              <span
                v-if="item.is_r18"
                class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-danger-soft text-danger border border-danger/30"
              >
                R-18
              </span>
            </div>

            <!-- ブックマーク数 -->
            <span
              v-if="item.bookmarks"
              class="absolute bottom-2 right-2 px-1.5 py-0.5 rounded text-[10px] font-mono bg-canvas-panel/90 text-ink-muted border border-canvas-border"
            >
              {{ formatCount(item.bookmarks) }}
            </span>

            <!-- ホバー: クイックアクション（PC向け、モバイルはカードタップで詳細・右上チェックで選択） -->
            <div
              class="hidden sm:flex absolute inset-0 bg-canvas-panel/70 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity p-2.5 flex-col justify-between"
            >
              <a
                :href="item.source_url"
                target="_blank"
                rel="noopener noreferrer"
                class="self-end p-1.5 rounded-lg bg-canvas-panel text-ink hover:text-pixiv transition-colors"
                title="pixivで開く"
                aria-label="pixivで開く"
                @click.stop
              >
                <ExternalLink class="w-3.5 h-3.5" />
              </a>

              <div class="flex items-center gap-1.5" @click.stop>
                <button
                  type="button"
                  class="flex-1 py-1.5 rounded-lg bg-pixiv text-white text-[11px] font-bold hover:bg-pixiv-hover transition-colors flex items-center justify-center gap-1"
                  @click="toggleSelect(item.id)"
                >
                  <Bookmark class="w-3 h-3" />
                  {{ pixiv.isSelected(item.id) ? '選択解除' : '選択' }}
                </button>
              </div>
            </div>
          </div>

          <!-- 情報 -->
          <div class="p-2.5 bg-canvas-card space-y-1.5 flex-1 flex flex-col">
            <h3 class="text-[11px] font-bold text-ink line-clamp-2 leading-snug" :title="item.title">
              {{ item.title }}
            </h3>

            <div class="flex items-center gap-1.5 text-[10px] font-medium text-ink-muted">
              <PixivImage
                v-if="item.author_avatar"
                :src="item.author_avatar"
                :alt="item.author_name"
                class="w-3.5 h-3.5 rounded-full object-cover shrink-0"
              />
              <span class="truncate">{{ item.author_name }}</span>
            </div>

            <!-- タグ -->
            <div v-if="item.tags?.length" class="flex flex-wrap gap-1 mt-auto pt-1">
              <button
                v-for="tag in item.tags.slice(0, 3)"
                :key="tag"
                type="button"
                class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-canvas-raised text-ink border border-canvas-border hover:text-pixiv hover:border-pixiv transition-colors truncate max-w-[90px]"
                @click.stop="searchInput = tag; submitSearch()"
              >
                #{{ tag }}
              </button>
            </div>
          </div>
        </article>
      </div>

      <!-- ページ送り -->
      <div v-if="activeCategory !== 'saved' && !pixiv.isLoading.value && pixiv.items.value.length" class="mt-6 flex items-center justify-center gap-2">
        <button
          type="button"
          class="p-2 rounded-lg border border-canvas-border bg-canvas-card text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors disabled:opacity-40"
          :disabled="pixiv.currentPage.value <= 1"
          aria-label="前のページ"
          @click="pixiv.prevPage()"
        >
          <ChevronLeft class="w-4 h-4" />
        </button>
        <span class="text-[11px] font-mono text-ink-muted px-2">{{ pixiv.currentPage.value }}</span>
        <button
          type="button"
          class="p-2 rounded-lg border border-canvas-border bg-canvas-card text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors disabled:opacity-40"
          :disabled="!pixiv.hasNext.value"
          aria-label="次のページ"
          @click="pixiv.nextPage()"
        >
          <ChevronRight class="w-4 h-4" />
        </button>
      </div>
      </main>
    </div>

    <!-- 一括アクションバー -->
    <div
      v-if="activeCategory !== 'saved' && pixiv.selectedIds.value.length"
      class="fixed bottom-safe inset-x-0 z-40 flex justify-center px-3 sm:px-4 pointer-events-none"
    >
      <div
        class="pointer-events-auto flex flex-wrap items-center justify-center gap-2 sm:gap-3 floating-bar px-3 sm:px-4 py-2 rounded-2xl animate-slide-up max-w-full"
      >
        <button
          type="button"
          class="text-[11px] text-ink-subtle hover:text-ink transition-colors whitespace-nowrap"
          @click="toggleSelectAll"
        >
          {{ allSelected ? '選択解除' : 'すべて選択' }}
        </button>
        <span class="text-[11px] text-ink-muted whitespace-nowrap">
          <span class="text-ink font-semibold">{{ pixiv.selectedIds.value.length }}</span> 件選択中
        </span>
        <div class="h-4 w-px bg-canvas-border hidden sm:block" />
        <div class="flex items-center gap-1">
          <span class="text-[10px] text-ink-subtle hidden sm:inline">保存先:</span>
          <FolderSelectDropdown
            v-model="selectedTargetFolder"
            compact
            align="top"
          />
        </div>
        <button
          type="button"
          class="px-2.5 sm:px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-pixiv text-white hover:bg-pixiv-hover transition-colors disabled:opacity-50 flex items-center gap-1 whitespace-nowrap shadow-sm"
          :disabled="isStashing || pixiv.isImporting.value"
          @click="stashSelected"
        >
          <RefreshCw v-if="isStashing" class="w-3 h-3 animate-spin" />
          <Bookmark v-else class="w-3 h-3" />
          {{ isStashing ? '保存中...' : 'ライブラリへ' }}
        </button>
        <button
          type="button"
          class="px-2.5 sm:px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-brand text-brand-fg hover:bg-brand-hover transition-colors disabled:opacity-50 flex items-center gap-1 whitespace-nowrap"
          :disabled="pixiv.isImporting.value"
          @click="placeSelectedOnCanvas"
        >
          <Layers class="w-3 h-3" />
          キャンバスへ
        </button>
        <button
          type="button"
          class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          title="選択をクリア"
          aria-label="選択をクリア"
          @click="pixiv.clearSelection(); isMultiSelectMode = false"
        >
          <X class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>

    <!-- 作品詳細モーダル -->
    <Teleport to="body">
      <div
        v-if="activeArtwork"
        class="fixed inset-0 z-[65] flex items-end sm:items-center justify-center p-2 sm:p-4 md:p-6 scrim animate-fade-in"
        @click.self="closeDetail"
      >
        <div
          class="w-full max-w-5xl max-h-[92dvh] sm:max-h-[90vh] rounded-2xl border border-canvas-border bg-canvas-panel shadow-pop flex flex-col md:flex-row overflow-hidden animate-scale-in"
          role="dialog"
          aria-modal="true"
          :aria-label="activeArtwork.title"
        >
          <!-- 画像 -->
          <div
            class="flex-1 bg-canvas-sunken relative flex items-center justify-center p-3 sm:p-4 min-h-[200px] max-h-[44dvh] md:max-h-none md:min-h-[320px] shrink-0 md:shrink"
            @touchstart.passive="onDetailTouchStart"
            @touchend.passive="onDetailTouchEnd"
          >
            <PixivImage
              v-if="activePageImage"
              :src="activePageImage.image_url"
              :alt="activeArtwork.title"
              class="max-w-full max-h-full object-contain rounded-lg"
            />
            <div v-else class="w-8 h-8 rounded-full border-2 border-brand border-t-transparent animate-spin" />

            <!-- モバイル用フローティング閉じるボタン -->
            <button
              type="button"
              class="md:hidden absolute top-2.5 right-2.5 z-20 p-1.5 rounded-full bg-canvas-panel/90 text-ink border border-canvas-border shadow-sm"
              aria-label="閉じる"
              @click="closeDetail"
            >
              <X class="w-4 h-4" />
            </button>

            <span
              v-if="currentPageImages.length > 1"
              class="absolute top-3 left-3 px-2 py-0.5 rounded-md text-[11px] font-mono bg-canvas-panel/90 text-ink border border-canvas-border"
            >
              {{ activePageIndex + 1 }} / {{ currentPageImages.length }}
            </span>

            <!-- ページ送り -->
            <template v-if="currentPageImages.length > 1">
              <button
                type="button"
                class="absolute left-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-canvas-panel/90 text-ink hover:bg-canvas-raised transition-colors disabled:opacity-30"
                :disabled="activePageIndex === 0"
                aria-label="前のページ"
                @click="activePageIndex--"
              >
                <ChevronLeft class="w-4 h-4" />
              </button>
              <button
                type="button"
                class="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-canvas-panel/90 text-ink hover:bg-canvas-raised transition-colors disabled:opacity-30"
                :disabled="activePageIndex >= currentPageImages.length - 1"
                aria-label="次のページ"
                @click="activePageIndex++"
              >
                <ChevronRight class="w-4 h-4" />
              </button>
            </template>
          </div>

          <!-- 情報 -->
          <div
            class="w-full md:w-96 flex-1 min-h-0 border-t md:border-t-0 md:border-l border-canvas-border p-3.5 sm:p-4 flex flex-col gap-3 sm:gap-4 overflow-y-auto"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <h3 class="text-sm font-bold text-ink leading-snug">{{ activeArtwork.title }}</h3>
                <a
                  v-if="activeArtwork.author_id"
                  :href="`https://www.pixiv.net/users/${activeArtwork.author_id}`"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="mt-1.5 flex items-center gap-1.5 text-xs hover:text-pixiv transition-colors"
                >
                  <PixivImage
                    v-if="activeArtwork.author_avatar"
                    :src="activeArtwork.author_avatar"
                    :alt="activeArtwork.author_name"
                    class="w-5 h-5 rounded-full object-cover"
                  />
                  <span class="text-pixiv font-medium truncate">{{ activeArtwork.author_name }}</span>
                </a>
                <p v-else class="mt-1.5 text-xs text-ink-muted truncate">{{ activeArtwork.author_name }}</p>
              </div>
              <button
                type="button"
                class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors shrink-0"
                aria-label="閉じる"
                @click="closeDetail"
              >
                <X class="w-4 h-4" />
              </button>
            </div>

            <!-- 統計 -->
            <div class="flex items-center gap-3 text-[11px] text-ink-muted font-mono">
              <span class="flex items-center gap-1">
                <Bookmark class="w-3 h-3" />
                {{ formatCount(activeArtwork.bookmarks) }}
              </span>
              <span class="flex items-center gap-1">
                <Eye class="w-3 h-3" />
                {{ formatCount(activeArtwork.view_likes || 0) }}
              </span>
              <span v-if="activeArtwork.create_date" class="ml-auto">{{ activeArtwork.create_date.slice(0, 10) }}</span>
            </div>

            <!-- キャプション -->
            <p
              v-if="activeArtwork.caption"
              class="text-[11px] leading-relaxed text-ink-muted whitespace-pre-wrap max-h-32 overflow-y-auto"
            >
              {{ activeArtwork.caption }}
            </p>

            <!-- タグ -->
            <div v-if="activeArtwork.tags?.length" class="flex flex-wrap gap-1">
              <button
                v-for="tag in activeArtwork.tags"
                :key="tag"
                type="button"
                class="px-2 py-0.5 rounded text-[10px] bg-canvas-raised text-ink-muted border border-canvas-border hover:text-pixiv hover:border-pixiv transition-colors"
                @click="searchInput = tag; closeDetail(); submitSearch()"
              >
                #{{ tag }}
              </button>
            </div>

            <!-- アクション -->
            <div class="mt-auto space-y-1.5 pt-3 border-t border-canvas-border">
              <button
                type="button"
                class="w-full py-2 rounded-lg bg-brand text-brand-fg text-xs font-bold hover:bg-brand-hover transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
                :disabled="isPlacing || pixiv.isImporting.value"
                @click="placeActiveOnCanvas"
              >
                <Layers class="w-3.5 h-3.5" />
                {{ isPlacing ? '配置中...' : 'キャンバスへ配置' }}
              </button>

              <!-- 保存先フォルダ選択と保存ボタン -->
              <div class="space-y-1.5 p-2 rounded-xl bg-canvas-sunken/60 border border-canvas-border">
                <div class="flex items-center justify-between gap-1 text-[11px] px-0.5">
                  <span class="font-bold text-ink-muted flex items-center gap-1">
                    <Folder class="w-3.5 h-3.5 text-brand" />
                    <span>保存先:</span>
                  </span>
                  <FolderSelectDropdown
                    v-model="selectedTargetFolder"
                    compact
                    align="right"
                  />
                </div>
                <button
                  type="button"
                  class="w-full py-2 rounded-lg bg-pixiv text-white text-xs font-bold hover:bg-pixiv-hover transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50 shadow-sm"
                  :disabled="isStashing || pixiv.isImporting.value"
                  @click="handleStashDetail"
                >
                  <Bookmark class="w-3.5 h-3.5" />
                  {{ isStashing ? '保存中...' : `${formatFolderLabel(selectedTargetFolder)} に保存` }}
                </button>
              </div>

              <div class="flex items-center gap-1.5">
                <a
                  :href="activeArtwork.source_url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex-1 py-2 rounded-lg bg-canvas-card hover:bg-canvas-hover text-ink-muted hover:text-ink text-xs font-medium text-center flex items-center justify-center gap-1.5 transition-colors border border-canvas-border"
                >
                  <ExternalLink class="w-3.5 h-3.5" />
                  pixivで開く
                </a>
                <button
                  type="button"
                  class="py-2 px-3 rounded-lg bg-canvas-card hover:bg-canvas-hover text-ink-muted hover:text-ink text-xs transition-colors border border-canvas-border"
                  title="作品URLをコピー"
                  aria-label="作品URLをコピー"
                  @click="copyUrl(activeArtwork.id)"
                >
                  <Link2 class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
    <!-- カテゴリ・検索フィルタ・Pixiv連携モーダル（モバイルでも押しやすいメイン内モーダル） -->
    <Teleport to="body">
      <div
        v-if="isFilterModalOpen"
        class="fixed inset-0 z-[65] flex items-end sm:items-center justify-center p-2 sm:p-4 scrim animate-fade-in"
        @click.self="isFilterModalOpen = false"
      >
        <div
          class="w-full max-w-md max-h-[88dvh] rounded-2xl border border-canvas-border bg-canvas-panel shadow-pop flex flex-col overflow-hidden animate-scale-in"
          role="dialog"
          aria-modal="true"
          aria-label="pixiv 絞り込み・連携設定"
        >
          <div class="px-4 py-3 border-b border-canvas-border flex items-center justify-between">
            <h2 class="text-sm font-bold text-ink flex items-center gap-2">
              <SlidersHorizontal class="w-4 h-4 text-pixiv" />
              <span>pixiv 絞り込み・連携設定</span>
            </h2>
            <button
              type="button"
              class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
              aria-label="閉じる"
              @click="isFilterModalOpen = false"
            >
              <X class="w-4 h-4" />
            </button>
          </div>

          <div class="p-4 space-y-5 overflow-y-auto">
            <!-- カテゴリ選択 -->
            <div class="space-y-2">
              <p class="text-xs font-bold text-ink">フィード切替</p>
              <div class="grid grid-cols-2 gap-2">
                <button
                  v-for="cat in CATEGORIES"
                  :key="cat.id"
                  type="button"
                  class="flex items-center gap-2 px-3 py-2.5 rounded-xl text-xs transition-colors border text-left disabled:opacity-40"
                  :class="activeCategory === cat.id
                    ? 'bg-brand-soft border-brand text-brand font-bold'
                    : 'bg-canvas-bg border-canvas-border-strong text-ink font-medium hover:bg-canvas-hover'"
                  :disabled="isCategoryDisabled(cat)"
                  @click="pickCategory(cat.id); isFilterModalOpen = false"
                >
                  <component :is="cat.icon" class="w-4 h-4 shrink-0" :class="activeCategory === cat.id ? 'text-brand' : 'text-ink-muted'" />
                  <span class="truncate">{{ cat.label }}</span>
                </button>
              </div>
            </div>

            <!-- 検索ソート・期間フィルタ -->
            <div class="pt-3 border-t border-canvas-border space-y-3">
              <p class="text-xs font-bold text-ink">検索結果の並び順・期間</p>

              <div class="space-y-1.5">
                <p class="text-[11px] font-medium text-ink-muted">並び順</p>
                <div class="grid grid-cols-3 gap-1.5">
                  <button
                    v-for="opt in SORT_OPTIONS"
                    :key="opt.id"
                    type="button"
                    class="py-2 px-2 rounded-xl text-xs border transition-colors text-center"
                    :class="sortMode === opt.id
                      ? 'bg-pixiv text-white border-pixiv font-bold'
                      : 'bg-canvas-bg text-ink border-canvas-border-strong font-medium hover:bg-canvas-hover'"
                    @click="sortMode = opt.id; applyFilters(); isFilterModalOpen = false"
                  >
                    {{ opt.label }}
                  </button>
                </div>
              </div>

              <div class="space-y-1.5">
                <p class="text-[11px] font-medium text-ink-muted">投稿期間</p>
                <div class="grid grid-cols-2 gap-1.5">
                  <button
                    v-for="opt in DURATION_OPTIONS"
                    :key="opt.id"
                    type="button"
                    class="py-2 px-2.5 rounded-xl text-xs border transition-colors text-center"
                    :class="durationMode === opt.id
                      ? 'bg-pixiv text-white border-pixiv font-bold'
                      : 'bg-canvas-bg text-ink border-canvas-border-strong font-medium hover:bg-canvas-hover'"
                    @click="durationMode = opt.id; applyFilters(); isFilterModalOpen = false"
                  >
                    {{ opt.label }}
                  </button>
                </div>
              </div>
            </div>

            <!-- Pixivアカウント連携状態 -->
            <div class="pt-3 border-t border-canvas-border space-y-2">
              <p class="text-xs font-bold text-ink">Pixiv アカウント連携</p>

              <div v-if="pixiv.isConnected.value" class="p-3 rounded-xl bg-canvas-bg border border-canvas-border-strong flex items-center justify-between gap-2">
                <div class="flex items-center gap-2.5 min-w-0">
                  <PixivImage
                    v-if="pixiv.status.value?.account?.avatar_url"
                    :src="pixiv.proxyImage(pixiv.status.value.account.avatar_url)"
                    :alt="pixiv.accountName.value"
                    class="w-8 h-8 rounded-full shrink-0"
                  />
                  <div class="min-w-0">
                    <p class="text-xs font-bold text-ink truncate">{{ pixiv.accountName.value }}</p>
                    <p v-if="pixiv.status.value?.account?.account" class="text-[11px] text-ink-muted truncate">
                      @{{ pixiv.status.value.account.account }}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-danger-soft text-danger hover:opacity-90 transition-opacity shrink-0 flex items-center gap-1"
                  @click="pixiv.disconnect(); isFilterModalOpen = false"
                >
                  <LogOut class="w-3.5 h-3.5" />
                  解除
                </button>
              </div>

              <div v-else class="p-3 rounded-xl bg-canvas-bg border border-canvas-border-strong space-y-2.5">
                <p class="text-xs text-ink-muted leading-relaxed">
                  {{ pixiv.statusMessage.value || 'Pixivアカウントを接続するとフォロー新着や公開ブックマークを取得できます。' }}
                </p>
                <button
                  v-if="pixiv.canConnect.value"
                  type="button"
                  class="w-full py-2.5 rounded-xl bg-pixiv text-white text-xs font-bold hover:bg-pixiv-hover transition-colors"
                  @click="pixiv.connect()"
                >
                  Pixivに接続する
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <QuickLookModal />
  </div>
</template>
