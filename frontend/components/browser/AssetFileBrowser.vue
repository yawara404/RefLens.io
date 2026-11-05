<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import {
  Bookmark,
  Folder,
  FolderPlus,
  Instagram,
  Globe,
  Compass,
  Search,
  Plus,
  ExternalLink,
  Trash2,
  Eye,
  LayoutGrid,
  List,
  Check,
  RotateCcw,
  X,
} from 'lucide-vue-next'
import type { BookmarkItem, FolderItem } from '~/types'
import { useBoardStore } from '~/stores/boardStore'
import { useMediaUrl } from '~/composables/useMediaUrl'
import { useToast } from '~/composables/useToast'
import { usePixiv, type PixivArtwork } from '~/composables/usePixiv'
import PixivImage from '~/components/ui/PixivImage.vue'
import FolderSelectDropdown from '~/components/ui/FolderSelectDropdown.vue'
import BookmarkActionsMenu from '~/components/ui/BookmarkActionsMenu.vue'

const props = defineProps<{ boardId: string; insightOpen?: boolean }>()

const boardStore = useBoardStore()
const toast = useToast()
const pixiv = usePixiv()
const { resolveMediaUrl } = useMediaUrl()

/**
 * Manager と統一した 3 セクション + Pixiv連携ビュー:
 * - library: ブックマーク一覧（余計な検索行を省き、すぐ一覧が見えるシンプル構成）
 * - folders: フォルダダッシュボード（サムネイル付きフォルダカード + Pixiv公開ブクマ切替）
 * - search: スマート検索（キーワード・取得元・AIタグでの絞り込み）
 */
const activeTab = ref<'library' | 'folders' | 'search'>('library')
const isPixivFeedMode = ref(false)
const viewMode = ref<'grid' | 'list'>('grid')
const browserWidth = ref(380)
const isResizing = ref(false)
const selectedBookmarkId = ref<string | null>(null)

const showUrlInput = ref(false)
const inputUrl = ref('')
const localSearch = ref('')
const sourceFilter = ref<'all' | 'pixiv' | 'instagram' | 'web_bookmark' | 'local_upload'>('all')

const newFolderName = ref('')
const showNewFolderInput = ref(false)

/** 現在のキャンバスにすでに配置されているブックマークの判定セット */
const placedKeySet = computed(() => {
  const keys = new Set<string>()
  for (const item of boardStore.items) {
    if (item.media_item_id) keys.add(item.media_item_id)
    if (item.media?.file_path) keys.add(item.media.file_path)
    if (item.media?.source_url) keys.add(item.media.source_url)
  }
  return keys
})

function isPlacedOnBoard(item: BookmarkItem): boolean {
  if (placedKeySet.value.has(item.id)) return true
  if (item.file_path && placedKeySet.value.has(item.file_path)) return true
  if (item.source_url && placedKeySet.value.has(item.source_url)) return true
  return false
}

/** フォルダごとのブックマーク一覧 */
function getFolderBookmarks(folder: FolderItem): BookmarkItem[] {
  if (folder.name === 'All References') return boardStore.bookmarks
  return boardStore.bookmarks.filter(b => b.folder_name === folder.name)
}

/** 空の英語プリセットフォルダ（!f.id かつ 0件）を除外し、ノイズのないフォルダ一覧にする */
const visibleFolders = computed<FolderItem[]>(() =>
  boardStore.folders.filter(f => {
    if (f.name === 'All References') return true
    if (f.id) return true // ユーザー作成フォルダは0件でも表示
    return getFolderBookmarks(f).length > 0 || boardStore.selectedFolder === f.name
  })
)

function getFolderPreviewThumbs(folder: FolderItem): string[] {
  return getFolderBookmarks(folder)
    .slice(0, 3)
    .map(b => resolveImageUrl(b.file_path))
    .filter(Boolean)
}

function formatFolderLabel(name: string): string {
  return name === 'All References' ? 'すべての資料' : name
}

function selectFolderAndOpenLibrary(folderName: string) {
  isPixivFeedMode.value = false
  boardStore.selectedFolder = folderName
  activeTab.value = 'library'
}

function openPixivBookmarksFeed() {
  isPixivFeedMode.value = true
  activeTab.value = 'library'
  loadPixivBookmarks()
}

/** よく使われているAIタグ（上位10件） */
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
    .slice(0, 10)
    .map(([tag]) => tag)
})

/** ブックマーク一覧のフィルタリング（キャンバスのsearchQueryとは独立） */
const displayedBookmarks = computed(() => {
  const q = activeTab.value === 'search' ? localSearch.value.toLowerCase().trim() : ''

  return boardStore.bookmarks.filter(b => {
    if (
      activeTab.value === 'library' &&
      boardStore.selectedFolder &&
      boardStore.selectedFolder !== 'All References' &&
      b.folder_name !== boardStore.selectedFolder
    ) {
      return false
    }
    if (activeTab.value === 'search' && sourceFilter.value !== 'all' && b.source_type !== sourceFilter.value) {
      return false
    }
    if (!q) return true

    const corpus = [
      b.title,
      b.author_name || '',
      b.folder_name || '',
      b.source_url || '',
      (b.ai_analysis?.tags || []).join(' '),
      b.ai_analysis?.composition || '',
      b.ai_analysis?.lighting || '',
    ].join(' ')
    return corpus.toLowerCase().includes(q)
  })
})

const displayedPixivBookmarks = computed(() => {
  const q = localSearch.value.toLowerCase().trim()
  return q
    ? pixiv.items.value.filter(item =>
        [item.title, item.author_name, ...item.tags].join(' ').toLowerCase().includes(q)
      )
    : pixiv.items.value
})

async function loadPixivBookmarks() {
  await pixiv.fetchStatus()
  if (pixiv.isConnected.value) await pixiv.loadFeed('bookmarks', 1)
}

function openAccountSwitcher() {
  window.dispatchEvent(new Event('reflens:auth-switch'))
}

async function placePixivBookmark(item: PixivArtwork) {
  if (pixiv.isImporting.value) return
  const coords = boardStore.getNextPlacementCoords()
  if (await pixiv.stockToCanvas([item.id], props.boardId, coords.x, coords.y)) {
    await boardStore.loadBoard(props.boardId)
    await boardStore.fetchBookmarks()
    toast.success('キャンバスへ配置しました', item.title)
  }
}

function dragPixivBookmark(e: DragEvent, item: PixivArtwork) {
  if (!e.dataTransfer) return
  e.dataTransfer.effectAllowed = 'copy'
  e.dataTransfer.setData('application/reflens-pixiv-id', item.id)
  e.dataTransfer.setData('text/uri-list', item.source_url)
  e.dataTransfer.setData('text/plain', item.source_url)
}

function resolveImageUrl(path?: string) {
  return resolveMediaUrl(path)
}

// -------------------------------------------------------------
// URL 追加
// -------------------------------------------------------------
const urlTargetFolder = ref<string>('All References')
const dragOverFolderTarget = ref<string | null>(null)

async function handleAddUrl() {
  const url = inputUrl.value.trim()
  if (!url) return

  const targetFolder = urlTargetFolder.value === 'All References' ? undefined : urlTargetFolder.value
  const res = await boardStore.addBookmark(url, targetFolder, false)
  if (res) {
    inputUrl.value = ''
    showUrlInput.value = false
    toast.success('ブックマークに保存しました', url)
  }
}

// -------------------------------------------------------------
// Drag & Drop / フォルダドロップ移動 / 1クリック配置
// -------------------------------------------------------------
function onDragStart(e: DragEvent, item: BookmarkItem) {
  if (!e.dataTransfer) return
  e.dataTransfer.effectAllowed = 'copyMove'
  e.dataTransfer.setData('application/reflens-bookmark-id', item.id)
  e.dataTransfer.setData('text/plain', item.title)

  const ghost = new Image()
  ghost.src = resolveImageUrl(item.file_path)
  e.dataTransfer.setDragImage(ghost, 20, 20)
}

function onFolderBookmarkDragOver(folder: FolderItem, e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
  dragOverFolderTarget.value = folder.name
}

function onFolderBookmarkDragLeave(folder: FolderItem) {
  if (dragOverFolderTarget.value === folder.name) {
    dragOverFolderTarget.value = null
  }
}

async function onFolderBookmarkDrop(folder: FolderItem, e: DragEvent) {
  e.preventDefault()
  dragOverFolderTarget.value = null
  const bookmarkId = e.dataTransfer?.getData('application/reflens-bookmark-id')
  if (!bookmarkId) return
  const success = await boardStore.moveBookmarksFolder([bookmarkId], folder.name)
  if (success) {
    toast.success(`「${formatFolderLabel(folder.name)}」に移動しました`)
  }
}

async function handleMoveBookmark(item: BookmarkItem, folderName: string) {
  const success = await boardStore.moveBookmarkFolder(item.id, folderName)
  if (success) {
    toast.success(`「${formatFolderLabel(folderName)}」に移動しました`)
  }
}

async function handleDeleteBookmark(item: BookmarkItem) {
  const success = await boardStore.deleteBookmark(item.id)
  if (success) {
    toast.success('ブックマークを削除しました', item.title)
    if (selectedBookmarkId.value === item.id) {
      selectedBookmarkId.value = null
    }
  }
}

async function handlePlaceOnBoard(item: BookmarkItem) {
  await boardStore.placeBookmarkOnBoard(item.id)
  toast.success('キャンバスへ配置しました', item.title)
}

// -------------------------------------------------------------
// フォルダ作成
// -------------------------------------------------------------
async function handleCreateFolder() {
  const name = newFolderName.value.trim()
  if (!name) return
  newFolderName.value = ''
  showNewFolderInput.value = false
  await boardStore.createFolder(name)
}

// -------------------------------------------------------------
// サイドバーの幅リサイズ
// -------------------------------------------------------------
function startResize(e: MouseEvent) {
  e.preventDefault()
  isResizing.value = true
  const startX = e.clientX
  const startWidth = browserWidth.value

  function onMouseMove(evt: MouseEvent) {
    if (!isResizing.value) return
    browserWidth.value = Math.max(300, Math.min(640, startWidth + (evt.clientX - startX)))
  }

  function onMouseUp() {
    isResizing.value = false
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('mouseup', onMouseUp)
  }

  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

// -------------------------------------------------------------
// キーボード: 削除とクイックルック
// -------------------------------------------------------------
function onKeyDown(e: KeyboardEvent) {
  if (isPixivFeedMode.value) return
  const target = e.target as HTMLElement
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return
  if (!selectedBookmarkId.value) return

  if (e.key === 'Delete' || e.key === 'Backspace') {
    e.preventDefault()
    boardStore.deleteBookmark(selectedBookmarkId.value)
    selectedBookmarkId.value = null
  } else if (e.key === ' ') {
    e.preventDefault()
    const item = boardStore.bookmarks.find(b => b.id === selectedBookmarkId.value)
    if (item) boardStore.openQuickLook(item)
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('reflens:auth-changed', loadPixivBookmarks)
  if (!boardStore.hasLoadedBookmarks) boardStore.fetchBookmarks()
  if (!boardStore.folders.length) boardStore.fetchFolders()
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('reflens:auth-changed', loadPixivBookmarks)
})

const SOURCE_PILLS = [
  { id: 'all', label: 'すべて' },
  { id: 'pixiv', label: 'pixiv' },
  { id: 'instagram', label: 'Instagram' },
  { id: 'web_bookmark', label: 'Web' },
  { id: 'local_upload', label: 'ローカル' },
] as const
</script>

<template>
  <aside
    class="fixed inset-x-0 top-14 bottom-0 z-40 h-[calc(100dvh-3.5rem)] w-full overflow-hidden bg-canvas-panel border-t border-canvas-border md:relative md:inset-auto md:z-30 md:h-full md:w-[var(--browser-w)] md:max-w-[55vw] md:border-t-0 shrink-0 flex flex-col border-r border-canvas-border select-none shadow-pop md:shadow-none"
    :style="{
      '--browser-w': `${browserWidth}px`,
      maxWidth: props.insightOpen
        ? 'min(55vw, max(260px, calc(100vw - min(380px, 32vw) - 320px)))'
        : undefined,
    }"
    aria-label="ブックマークブラウザ"
  >
    <!-- 1. ヘッダー（文字切れを起こさない1行シンプル構成） -->
    <div class="px-3.5 py-2.5 border-b border-canvas-border flex items-center justify-between gap-2 shrink-0 whitespace-nowrap">
      <div class="flex items-center gap-2 min-w-0">
        <div class="w-7 h-7 rounded-xl bg-brand-soft text-brand flex items-center justify-center shrink-0">
          <Bookmark class="w-3.5 h-3.5" />
        </div>
        <h2 class="text-xs font-bold text-ink truncate">ブックマーク</h2>
        <span class="px-2 py-0.5 rounded-full bg-canvas-card border border-canvas-border text-[10px] font-mono font-semibold text-ink-muted shrink-0">
          {{ boardStore.bookmarks.length }}
        </span>
      </div>

      <div class="flex items-center gap-1.5 shrink-0">
        <!-- URL保存トグル -->
        <button
          type="button"
          class="px-2.5 py-1 rounded-lg text-[11px] font-bold transition-colors flex items-center gap-1 border whitespace-nowrap shrink-0"
          :class="showUrlInput
            ? 'bg-brand text-brand-fg border-brand'
            : 'bg-canvas-card text-ink hover:border-brand border-canvas-border'"
          title="URLからブックマークを保存"
          :aria-expanded="showUrlInput"
          @click="showUrlInput = !showUrlInput"
        >
          <Plus class="w-3 h-3 shrink-0" />
          <span>URL保存</span>
        </button>

        <!-- グリッド / リスト表示切替（Managerと統一した2段階切替） -->
        <div
          v-if="activeTab !== 'folders'"
          class="flex items-center gap-0.5 p-0.5 rounded-lg border border-canvas-border bg-canvas-card shrink-0"
          role="group"
          aria-label="表示形式の切り替え"
        >
          <button
            type="button"
            class="p-1 rounded-md transition-colors"
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
            class="p-1 rounded-md transition-colors"
            :class="viewMode === 'list' ? 'bg-brand text-brand-fg' : 'text-ink-muted hover:text-ink'"
            title="リスト表示"
            aria-label="リスト表示"
            :aria-pressed="viewMode === 'list'"
            @click="viewMode = 'list'"
          >
            <List class="w-3.5 h-3.5" />
          </button>
        </div>

        <button
          type="button"
          class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors shrink-0"
          title="ブックマークを閉じる [B]"
          aria-label="ブックマークを閉じる"
          @click="boardStore.isBrowserOpen = false"
        >
          <X class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- 折りたたみ式 URL保存バー -->
    <div v-if="showUrlInput" class="px-3.5 py-2.5 bg-canvas-card border-b border-canvas-border shrink-0 space-y-2">
      <form class="space-y-2" @submit.prevent="handleAddUrl">
        <div class="relative flex items-center min-w-0">
          <Globe class="absolute left-2.5 w-3.5 h-3.5 text-ink-subtle pointer-events-none" />
          <input
            v-model="inputUrl"
            type="url"
            placeholder="pixiv / Instagram / Web 画像URL..."
            class="w-full bg-canvas-bg border border-canvas-border-strong rounded-lg pl-8 pr-2.5 py-1.5 text-xs text-ink placeholder:text-ink-subtle focus:outline-none focus:border-brand transition-colors"
            aria-label="URLをライブラリに追加"
          >
        </div>
        <div class="flex items-center justify-between gap-1.5">
          <FolderSelectDropdown
            v-model="urlTargetFolder"
            button-class="text-xs h-8 flex-1 truncate"
            placeholder="保存先フォルダ"
          />
          <button
            type="submit"
            class="px-3 py-1.5 rounded-lg text-xs font-bold bg-brand text-brand-fg hover:bg-brand-hover transition-colors disabled:opacity-40 shrink-0 whitespace-nowrap h-8"
            :disabled="!inputUrl.trim() || boardStore.isAddingBookmark"
          >
            {{ boardStore.isAddingBookmark ? '保存中...' : '保存' }}
          </button>
        </div>
      </form>
    </div>

    <!-- 2. Managerと統一した 3 セクションタブ（ライブラリ / フォルダ / 検索） -->
    <div class="px-3 py-2 border-b border-canvas-border bg-canvas-panel shrink-0">
      <div class="grid grid-cols-3 gap-1 p-1 rounded-xl bg-canvas-card border border-canvas-border-strong" role="tablist">
        <button
          type="button"
          role="tab"
          :aria-selected="activeTab === 'library'"
          class="py-1.5 px-2 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-colors whitespace-nowrap"
          :class="activeTab === 'library'
            ? 'bg-brand text-brand-fg shadow-sm'
            : 'text-ink hover:text-brand hover:bg-canvas-hover'"
          @click="activeTab = 'library'"
        >
          <Bookmark class="w-3.5 h-3.5 shrink-0" />
          <span>ライブラリ</span>
        </button>

        <button
          type="button"
          role="tab"
          :aria-selected="activeTab === 'folders'"
          class="py-1.5 px-2 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-colors whitespace-nowrap"
          :class="activeTab === 'folders'
            ? 'bg-brand text-brand-fg shadow-sm'
            : 'text-ink hover:text-brand hover:bg-canvas-hover'"
          @click="activeTab = 'folders'"
        >
          <Folder class="w-3.5 h-3.5 shrink-0" />
          <span>フォルダ</span>
        </button>

        <button
          type="button"
          role="tab"
          :aria-selected="activeTab === 'search'"
          class="py-1.5 px-2 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-colors whitespace-nowrap"
          :class="activeTab === 'search'
            ? 'bg-brand text-brand-fg shadow-sm'
            : 'text-ink hover:text-brand hover:bg-canvas-hover'"
          @click="activeTab = 'search'; isPixivFeedMode = false"
        >
          <Search class="w-3.5 h-3.5 shrink-0" />
          <span>検索</span>
        </button>
      </div>
    </div>

    <!-- 3A. ライブラリタブ時: コンパクトなフォルダ切替ピル（複数ある場合のみ表示） -->
    <div
      v-if="activeTab === 'library' && (visibleFolders.length > 1 || isPixivFeedMode)"
      class="px-3 py-2 border-b border-canvas-border flex items-center gap-1.5 overflow-x-auto no-scrollbar shrink-0 bg-canvas-panel whitespace-nowrap"
    >
      <button
        v-for="folder in visibleFolders"
        :key="folder.name"
        type="button"
        class="px-2.5 py-1 rounded-full text-[11px] font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 border shrink-0"
        :class="[
          !isPixivFeedMode && boardStore.selectedFolder === folder.name
            ? 'bg-brand text-brand-fg border-brand font-bold'
            : 'bg-canvas-card border-canvas-border-strong text-ink hover:bg-canvas-hover',
          dragOverFolderTarget === folder.name ? 'ring-2 ring-brand border-brand bg-brand-soft font-bold scale-105' : '',
        ]"
        @dragover="onFolderBookmarkDragOver(folder, $event)"
        @dragleave="onFolderBookmarkDragLeave(folder)"
        @drop.prevent="onFolderBookmarkDrop(folder, $event)"
        @click="isPixivFeedMode = false; boardStore.selectedFolder = folder.name"
      >
        <span
          class="w-2 h-2 rounded-full shrink-0"
          :style="{ backgroundColor: !isPixivFeedMode && boardStore.selectedFolder === folder.name ? '#ffffff' : (folder.color || '#6366f1') }"
        />
        <span>{{ formatFolderLabel(folder.name) }}</span>
        <span class="text-[10px] font-mono opacity-85">{{ getFolderBookmarks(folder).length }}</span>
      </button>

      <button
        type="button"
        class="px-2.5 py-1 rounded-full text-[11px] font-semibold whitespace-nowrap transition-colors flex items-center gap-1 border shrink-0"
        :class="isPixivFeedMode
          ? 'bg-pixiv text-white border-pixiv font-bold'
          : 'bg-canvas-card border-canvas-border-strong text-ink hover:text-pixiv'"
        @click="openPixivBookmarksFeed"
      >
        <Compass class="w-3 h-3 shrink-0" />
        <span>Pixiv公開ブクマ</span>
      </button>
    </div>

    <!-- 3B. 検索タブ時: スマート検索パネル（キーワード・取得元・AIタグ） -->
    <div v-if="activeTab === 'search'" class="px-3 py-2.5 border-b border-canvas-border space-y-2 shrink-0 bg-canvas-panel">
      <div class="relative flex items-center">
        <Search class="absolute left-2.5 w-3.5 h-3.5 text-ink-subtle pointer-events-none" />
        <input
          v-model="localSearch"
          type="search"
          placeholder="タイトル・作者・AIタグで横断検索..."
          class="w-full bg-canvas-card border border-canvas-border-strong rounded-xl pl-8 pr-7 py-1.5 text-xs text-ink placeholder:text-ink-subtle focus:outline-none focus:border-brand transition-colors"
          aria-label="ブックマークを検索"
        >
        <button
          v-if="localSearch"
          type="button"
          class="absolute right-2 p-0.5 rounded-full text-ink-subtle hover:text-ink transition-colors"
          aria-label="検索をクリア"
          @click="localSearch = ''"
        >
          <X class="w-3.5 h-3.5" />
        </button>
      </div>

      <!-- 取得元ピル -->
      <div class="flex items-center justify-between gap-1">
        <div class="flex items-center gap-1 overflow-x-auto no-scrollbar">
          <button
            v-for="src in SOURCE_PILLS"
            :key="src.id"
            type="button"
            class="px-2.5 py-1 rounded-lg text-[11px] font-semibold whitespace-nowrap transition-colors border shrink-0"
            :class="sourceFilter === src.id
              ? 'bg-brand text-brand-fg border-brand'
              : 'bg-canvas-card text-ink-muted border-canvas-border hover:text-ink'"
            @click="sourceFilter = src.id"
          >
            {{ src.label }}
          </button>
        </div>

        <button
          v-if="localSearch || sourceFilter !== 'all'"
          type="button"
          class="p-1 rounded-lg text-ink-muted hover:text-ink shrink-0"
          title="検索条件をリセット"
          @click="localSearch = ''; sourceFilter = 'all'"
        >
          <RotateCcw class="w-3.5 h-3.5" />
        </button>
      </div>

      <!-- AIタグチップ -->
      <div v-if="popularAiTags.length" class="flex items-center gap-1 overflow-x-auto no-scrollbar pt-0.5">
        <button
          v-for="tag in popularAiTags"
          :key="tag"
          type="button"
          class="px-2 py-0.5 rounded-full text-[10px] font-medium whitespace-nowrap transition-colors border shrink-0"
          :class="localSearch === tag
            ? 'bg-brand-soft text-brand border-brand font-bold'
            : 'bg-canvas-bg text-ink-subtle border-canvas-border hover:text-brand'"
          @click="localSearch = localSearch === tag ? '' : tag"
        >
          #{{ tag }}
        </button>
      </div>
    </div>

    <!-- 4. メインスクロール領域 -->
    <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain p-3">
      <!-- ==================== フォルダタブ（ダッシュボード） ==================== -->
      <div v-if="activeTab === 'folders'" class="space-y-3">
        <div class="flex items-center justify-between gap-2">
          <p class="text-xs font-bold text-ink">フォルダを選択</p>
          <button
            v-if="!showNewFolderInput"
            type="button"
            class="px-2.5 py-1 rounded-lg bg-brand-soft text-brand hover:bg-brand hover:text-brand-fg text-[11px] font-bold transition-colors flex items-center gap-1 whitespace-nowrap"
            @click="showNewFolderInput = true"
          >
            <FolderPlus class="w-3.5 h-3.5 shrink-0" />
            <span>新規フォルダ</span>
          </button>
        </div>

        <!-- 新規フォルダ作成フォーム -->
        <form
          v-if="showNewFolderInput"
          class="p-2.5 rounded-xl bg-canvas-card border border-brand flex items-center gap-2"
          @submit.prevent="handleCreateFolder"
        >
          <input
            v-model="newFolderName"
            type="text"
            placeholder="新しいフォルダ名を入力..."
            class="flex-1 min-w-0 bg-canvas-bg border border-canvas-border rounded-lg px-2.5 py-1.5 text-xs text-ink focus:outline-none focus:border-brand"
            autofocus
          >
          <button
            type="button"
            class="px-2 py-1.5 rounded-lg text-xs text-ink-muted hover:text-ink whitespace-nowrap shrink-0"
            @click="showNewFolderInput = false"
          >
            キャンセル
          </button>
          <button
            type="submit"
            class="px-3 py-1.5 rounded-lg bg-brand text-brand-fg text-xs font-bold whitespace-nowrap shrink-0"
          >
            作成
          </button>
        </form>

        <!-- フォルダカードグリッド -->
        <div class="grid grid-cols-2 gap-2.5">
          <button
            v-for="folder in visibleFolders"
            :key="folder.name"
            type="button"
            class="group text-left rounded-xl border bg-canvas-card overflow-hidden transition-all hover:border-brand"
            :class="[
              !isPixivFeedMode && boardStore.selectedFolder === folder.name
                ? 'border-brand ring-2 ring-brand/25'
                : 'border-canvas-border',
              dragOverFolderTarget === folder.name ? 'ring-2 ring-brand border-brand bg-brand-soft/40 scale-[1.02]' : '',
            ]"
            @dragover="onFolderBookmarkDragOver(folder, $event)"
            @dragleave="onFolderBookmarkDragLeave(folder)"
            @drop.prevent="onFolderBookmarkDrop(folder, $event)"
            @click="selectFolderAndOpenLibrary(folder.name)"
          >
            <div class="h-24 bg-canvas-sunken grid grid-cols-3 gap-0.5 overflow-hidden">
              <template v-if="getFolderPreviewThumbs(folder).length > 0">
                <div class="col-span-2 h-full bg-canvas-sunken overflow-hidden">
                  <img
                    :src="getFolderPreviewThumbs(folder)[0]"
                    alt=""
                    class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    loading="lazy"
                  >
                </div>
                <div class="col-span-1 grid grid-rows-2 gap-0.5 h-full">
                  <div class="bg-canvas-sunken overflow-hidden">
                    <img
                      v-if="getFolderPreviewThumbs(folder)[1]"
                      :src="getFolderPreviewThumbs(folder)[1]"
                      alt=""
                      class="w-full h-full object-cover"
                      loading="lazy"
                    >
                  </div>
                  <div class="bg-canvas-sunken overflow-hidden">
                    <img
                      v-if="getFolderPreviewThumbs(folder)[2]"
                      :src="getFolderPreviewThumbs(folder)[2]"
                      alt=""
                      class="w-full h-full object-cover"
                      loading="lazy"
                    >
                  </div>
                </div>
              </template>
              <div v-else class="col-span-3 flex items-center justify-center text-ink-subtle">
                <Folder class="w-6 h-6 opacity-40" />
              </div>
            </div>

            <div class="p-2.5 flex items-center justify-between gap-1.5">
              <div class="flex items-center gap-1.5 min-w-0">
                <span class="w-2.5 h-2.5 rounded-full shrink-0" :style="{ backgroundColor: folder.color || '#6366f1' }" />
                <span class="text-xs font-bold text-ink truncate">{{ formatFolderLabel(folder.name) }}</span>
              </div>
              <span class="text-[11px] font-mono text-ink-muted shrink-0">
                {{ getFolderBookmarks(folder).length }}件
              </span>
            </div>
          </button>

          <!-- Pixiv公開ブックマーク連携カード -->
          <button
            type="button"
            class="group text-left rounded-xl border bg-canvas-card overflow-hidden transition-all hover:border-pixiv"
            :class="isPixivFeedMode ? 'border-pixiv ring-2 ring-pixiv/25' : 'border-canvas-border'"
            @click="openPixivBookmarksFeed"
          >
            <div class="h-24 bg-pixiv/10 flex flex-col items-center justify-center gap-1.5 text-pixiv">
              <Compass class="w-7 h-7" />
              <span class="text-[10px] font-bold">Pixiv アカウント連携</span>
            </div>
            <div class="p-2.5 flex items-center justify-between gap-1.5">
              <span class="text-xs font-bold text-ink truncate">Pixiv公開ブクマ</span>
              <span class="text-[10px] font-semibold text-pixiv shrink-0">開く</span>
            </div>
          </button>
        </div>
      </div>

      <!-- ==================== Pixiv 公開ブックマーク表示時 ==================== -->
      <div v-else-if="isPixivFeedMode && activeTab === 'library'" class="space-y-3">
        <div v-if="!pixiv.isConnected.value" class="py-12 text-center space-y-3">
          <Compass class="w-8 h-8 text-ink-subtle mx-auto" />
          <p class="text-xs font-bold text-ink">Pixivアカウント連携が必要です</p>
          <button
            v-if="pixiv.canConnect.value"
            type="button"
            class="px-4 py-2 rounded-xl bg-pixiv text-white text-xs font-bold hover:bg-pixiv-hover transition-colors"
            @click="pixiv.connect()"
          >
            Pixivに接続する
          </button>
          <p v-else class="text-[11px] text-ink-subtle">{{ pixiv.statusMessage.value }}</p>
        </div>

        <div v-else class="space-y-2.5">
          <div class="flex items-center justify-between gap-2">
            <span class="text-[11px] text-ink-muted truncate">公開ブックマーク · {{ pixiv.accountName.value }}</span>
            <button
              type="button"
              class="text-[11px] font-semibold text-pixiv hover:underline shrink-0"
              :disabled="pixiv.isLoading.value"
              @click="loadPixivBookmarks"
            >
              更新
            </button>
          </div>

          <div v-if="pixiv.isLoading.value" class="py-12 text-center text-xs text-ink-muted">読み込み中…</div>

          <div v-else-if="!displayedPixivBookmarks.length" class="py-10 text-center text-xs text-ink-muted space-y-2">
            <p>{{ pixiv.feedError.value ? 'Pixivの取得に失敗しました' : '公開ブックマークがありません' }}</p>
            <button
              v-if="!pixiv.feedError.value"
              type="button"
              class="px-3 py-1.5 rounded-xl bg-pixiv text-white text-xs font-semibold"
              @click="openAccountSwitcher"
            >
              RefLensアカウントを切り替える
            </button>
          </div>

          <div v-else class="grid grid-cols-2 gap-2.5">
            <figure
              v-for="item in displayedPixivBookmarks"
              :key="item.id"
              draggable="true"
              class="group rounded-xl overflow-hidden bg-canvas-card border border-canvas-border flex flex-col cursor-grab active:cursor-grabbing hover:border-canvas-border-strong transition-colors"
              @dragstart="dragPixivBookmark($event, item)"
            >
              <div class="aspect-square relative bg-canvas-sunken overflow-hidden">
                <PixivImage :src="item.image_url" :alt="item.title" class="w-full h-full object-cover pointer-events-none" loading="lazy" />
              </div>
              <figcaption class="p-2 flex flex-col gap-1.5 flex-1 justify-between">
                <div class="min-w-0">
                  <p class="text-[11px] font-bold text-ink truncate" :title="item.title">{{ item.title }}</p>
                  <p class="text-[10px] text-ink-subtle truncate">{{ item.author_name }}</p>
                </div>
                <button
                  type="button"
                  class="w-full py-1.5 rounded-lg bg-pixiv hover:bg-pixiv-hover text-white text-[11px] font-bold transition-colors flex items-center justify-center gap-1 disabled:opacity-40 whitespace-nowrap"
                  :disabled="pixiv.isImporting.value"
                  @click="placePixivBookmark(item)"
                >
                  <Plus class="w-3.5 h-3.5 shrink-0" />
                  <span>キャンバスへ配置</span>
                </button>
              </figcaption>
            </figure>
          </div>
        </div>
      </div>

      <!-- ==================== ライブラリ / 検索結果一覧 ==================== -->
      <template v-else>
        <!-- 空状態 -->
        <div v-if="!displayedBookmarks.length" class="py-12 text-center space-y-3">
          <Bookmark class="w-8 h-8 text-ink-subtle mx-auto opacity-60" />
          <div class="space-y-1">
            <p class="text-xs font-bold text-ink">
              {{ activeTab === 'search' ? '条件に一致するブックマークがありません' : 'ブックマークがありません' }}
            </p>
            <p class="text-[11px] text-ink-subtle leading-relaxed">
              右上の「＋URL保存」から追加するか、<br>別のフォルダを選択してください
            </p>
          </div>
          <button
            v-if="localSearch || sourceFilter !== 'all' || boardStore.selectedFolder !== 'All References'"
            type="button"
            class="px-3 py-1.5 rounded-xl bg-canvas-card border border-canvas-border text-xs font-semibold text-ink hover:bg-canvas-hover transition-colors"
            @click="localSearch = ''; sourceFilter = 'all'; boardStore.selectedFolder = 'All References'"
          >
            すべての資料を表示
          </button>
        </div>

        <!-- 2列グリッド（Managerのカードデザインと統一） -->
        <div v-else-if="viewMode === 'grid'" class="grid grid-cols-2 gap-2.5">
          <article
            v-for="item in displayedBookmarks"
            :key="item.id"
            tabindex="0"
            draggable="true"
            class="group rounded-xl overflow-hidden bg-canvas-card border transition-all flex flex-col cursor-grab active:cursor-grabbing"
            :class="selectedBookmarkId === item.id
              ? 'border-brand ring-2 ring-brand/25'
              : 'border-canvas-border hover:border-canvas-border-strong'"
            @dragstart="onDragStart($event, item)"
            @click="selectedBookmarkId = item.id"
            @focus="selectedBookmarkId = item.id"
            @keydown.enter.self.prevent="handlePlaceOnBoard(item)"
          >
            <!-- サムネイル（クリックでQuickLook拡大プレビュー） -->
            <div
              class="relative aspect-square bg-canvas-sunken overflow-hidden cursor-pointer"
              title="クリックで拡大プレビュー"
              @click.stop="boardStore.openQuickLook(item)"
            >
              <img
                :src="resolveImageUrl(item.file_path)"
                :alt="item.title"
                class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300 pointer-events-none"
                loading="lazy"
                draggable="false"
              >

              <!-- 左上: ソースバッジ -->
              <span
                v-if="item.source_type === 'pixiv'"
                class="absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded text-[9px] font-bold bg-pixiv text-white shadow-sm"
              >
                pixiv
              </span>
              <span
                v-else-if="item.source_type === 'instagram'"
                class="absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded text-[9px] font-bold bg-instagram text-white flex items-center gap-0.5 shadow-sm"
              >
                <Instagram class="w-2.5 h-2.5" />
                IG
              </span>
              <span
                v-else-if="item.source_type === 'local_upload'"
                class="absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded text-[9px] font-medium bg-canvas-panel/90 text-ink border border-canvas-border shadow-sm"
              >
                Local
              </span>
              <span
                v-else
                class="absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded text-[9px] font-medium bg-canvas-panel/90 text-ink-muted border border-canvas-border shadow-sm"
              >
                Web
              </span>

              <!-- 右上: 配置済バッジ -->
              <span
                v-if="isPlacedOnBoard(item)"
                class="absolute top-1.5 right-1.5 px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-ok text-white flex items-center gap-0.5 shadow-sm"
                title="このキャンバスに配置済み"
              >
                <Check class="w-2.5 h-2.5 stroke-[3]" />
                配置済
              </span>
            </div>

            <!-- カード情報 + 配置ボタン -->
            <div class="p-2 flex flex-col gap-1.5 flex-1 justify-between bg-canvas-card border-t border-canvas-border">
              <div class="min-w-0">
                <p class="text-[11px] font-bold text-ink truncate leading-tight" :title="item.title">
                  {{ item.title }}
                </p>
                <div class="flex items-center justify-between gap-1 mt-0.5">
                  <p class="text-[10px] font-medium text-ink-muted truncate">
                    {{ item.author_name || formatFolderLabel(item.folder_name) }}
                  </p>
                  <div class="flex items-center gap-0.5 shrink-0">
                    <button
                      type="button"
                      class="p-1 rounded text-ink-subtle hover:text-ink hover:bg-canvas-hover transition-colors"
                      title="詳細プレビュー"
                      aria-label="詳細プレビュー"
                      @click.stop="boardStore.openQuickLook(item)"
                    >
                      <Eye class="w-3 h-3" />
                    </button>
                    <a
                      v-if="item.source_url"
                      :href="item.source_url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="p-1 rounded text-ink-subtle hover:text-brand hover:bg-canvas-hover transition-colors"
                      title="元のページを開く"
                      aria-label="元のページを開く"
                      @click.stop
                    >
                      <ExternalLink class="w-3 h-3" />
                    </a>
                    <BookmarkActionsMenu
                      :item="item"
                      @place="handlePlaceOnBoard(item)"
                      @move="handleMoveBookmark(item, $event)"
                      @delete="handleDeleteBookmark(item)"
                    />
                  </div>
                </div>
              </div>

              <button
                type="button"
                class="w-full py-1.5 px-2 rounded-lg text-[11px] font-bold transition-colors flex items-center justify-center gap-1 whitespace-nowrap"
                :class="isPlacedOnBoard(item)
                  ? 'bg-canvas-bg hover:bg-brand hover:text-brand-fg text-ink border border-canvas-border-strong'
                  : 'bg-brand hover:bg-brand-hover text-brand-fg'"
                @click.stop="handlePlaceOnBoard(item)"
              >
                <Plus class="w-3.5 h-3.5 shrink-0" />
                <span>{{ isPlacedOnBoard(item) ? 'もう1枚配置' : 'キャンバスへ配置' }}</span>
              </button>
            </div>
          </article>
        </div>

        <!-- リスト表示 -->
        <div v-else class="space-y-1.5">
          <div
            v-for="item in displayedBookmarks"
            :key="item.id"
            tabindex="0"
            draggable="true"
            class="group p-2 rounded-xl border border-canvas-border bg-canvas-card hover:border-canvas-border-strong transition-colors cursor-grab active:cursor-grabbing flex items-center gap-2.5"
            @dragstart="onDragStart($event, item)"
            @click="boardStore.openQuickLook(item)"
            @keydown.enter.self.prevent="handlePlaceOnBoard(item)"
          >
            <img
              :src="resolveImageUrl(item.file_path)"
              :alt="item.title"
              class="w-11 h-11 rounded-lg object-cover shrink-0 pointer-events-none bg-canvas-sunken"
              loading="lazy"
            >
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-1.5">
                <p class="text-xs font-bold text-ink truncate">{{ item.title }}</p>
                <span
                  v-if="isPlacedOnBoard(item)"
                  class="px-1.5 py-0.2 rounded-full bg-ok/15 text-ok text-[9px] font-bold shrink-0 whitespace-nowrap"
                >
                  配置済
                </span>
              </div>
              <p class="text-[10px] text-ink-subtle truncate mt-0.5">
                {{ item.author_name || formatFolderLabel(item.folder_name) }}
              </p>
            </div>
            <BookmarkActionsMenu
              :item="item"
              @place="handlePlaceOnBoard(item)"
              @move="handleMoveBookmark(item, $event)"
              @delete="handleDeleteBookmark(item)"
            />
            <button
              type="button"
              class="px-2.5 py-1.5 rounded-lg bg-brand hover:bg-brand-hover text-brand-fg text-[11px] font-bold transition-colors shrink-0 flex items-center gap-1 whitespace-nowrap"
              @click.stop="handlePlaceOnBoard(item)"
            >
              <Plus class="w-3 h-3 shrink-0" />
              <span>配置</span>
            </button>
          </div>
        </div>
      </template>
    </div>

    <!-- 5. フッター -->
    <div class="px-3.5 py-2 border-t border-canvas-border flex items-center justify-between gap-2 text-[11px] bg-canvas-panel shrink-0 whitespace-nowrap">
      <span class="text-ink-subtle font-mono" aria-live="polite">
        {{ isPixivFeedMode ? `${displayedPixivBookmarks.length} 件表示` : `${displayedBookmarks.length} 件表示` }}
      </span>

      <div class="flex items-center gap-2">
        <button
          v-if="selectedBookmarkId && !isPixivFeedMode"
          type="button"
          class="px-2 py-1 rounded-lg text-ink-subtle hover:text-danger hover:bg-danger-soft transition-colors flex items-center gap-1"
          title="選択中のブックマークを削除 (Delete)"
          @click="boardStore.deleteBookmark(selectedBookmarkId); selectedBookmarkId = null"
        >
          <Trash2 class="w-3.5 h-3.5 shrink-0" />
          <span>削除</span>
        </button>

        <button
          type="button"
          class="md:hidden px-3 py-1 rounded-lg bg-brand text-brand-fg font-bold text-xs"
          @click="boardStore.isBrowserOpen = false"
        >
          キャンバスを見る
        </button>
        <span class="hidden md:inline text-ink-subtle">ドラッグ＆ドロップ配置対応</span>
      </div>
    </div>

    <!-- PC用: パネル幅リサイズハンドル -->
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="ブックマークブラウザの幅を調整"
      tabindex="0"
      class="hidden md:block absolute top-0 -right-1 w-2 h-full cursor-col-resize hover:bg-brand/40 focus-visible:bg-brand/60 transition-colors z-40"
      title="ドラッグまたは左右キーで幅を変更"
      @mousedown.stop="startResize"
      @keydown.left.prevent="browserWidth = Math.max(300, browserWidth - 20)"
      @keydown.right.prevent="browserWidth = Math.min(640, browserWidth + 20)"
    />
  </aside>
</template>
