<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import {
  Layers,
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
  GripVertical,
} from 'lucide-vue-next'
import type { BookmarkItem } from '~/types'
import { useBoardStore } from '~/stores/boardStore'
import { useMediaUrl } from '~/composables/useMediaUrl'
import { useToast } from '~/composables/useToast'
import { usePixiv, type PixivArtwork } from '~/composables/usePixiv'
import PixivImage from '~/components/ui/PixivImage.vue'

const props = defineProps<{ boardId: string; insightOpen?: boolean }>()

const boardStore = useBoardStore()
const toast = useToast()
const pixiv = usePixiv()
const { resolveMediaUrl } = useMediaUrl()

const viewMode = ref<'grid-lg' | 'grid-sm' | 'list'>('grid-lg')
const browserWidth = ref(440)
const isResizing = ref(false)
const selectedBookmarkId = ref<string | null>(null)
const inputUrl = ref('')
const localSearch = ref('')
const newFolderName = ref('')
const showNewFolderInput = ref(false)
const isRemotePixiv = computed(() => boardStore.selectedSourceType === 'pixiv_bookmarks')
const displayedPixivBookmarks = computed(() => {
  const q = localSearch.value.toLowerCase().trim()
  return q ? pixiv.items.value.filter(item =>
    [item.title, item.author_name, ...item.tags].join(' ').toLowerCase().includes(q)
  ) : pixiv.items.value
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
  if (await pixiv.stockToCanvas([item.id], props.boardId)) {
    await boardStore.loadBoard(props.boardId)
    await boardStore.fetchBookmarks()
    toast.success('キャンバスへ配置しました')
  }
}

function dragPixivBookmark(e: DragEvent, item: PixivArtwork) {
  if (!e.dataTransfer) return
  e.dataTransfer.effectAllowed = 'copy'
  e.dataTransfer.setData('application/reflens-pixiv-id', item.id)
  e.dataTransfer.setData('text/uri-list', item.source_url)
  e.dataTransfer.setData('text/plain', item.source_url)
}

/** ライブラリ検索はローカルのクエリで行う（キャンバスの検索クエリとは独立） */
const displayedBookmarks = computed(() => {
  const q = localSearch.value.toLowerCase().trim()
  if (!q) return boardStore.filteredBookmarks

  return boardStore.filteredBookmarks.filter(b => {
    const corpus = [
      b.title,
      b.author_name || '',
      b.source_url || '',
      (b.ai_analysis?.tags || []).join(' '),
      b.ai_analysis?.composition || '',
      b.ai_analysis?.lighting || '',
    ].join(' ')
    return corpus.toLowerCase().includes(q)
  })
})

function resolveImageUrl(path?: string) {
  return resolveMediaUrl(path)
}

// -------------------------------------------------------------
// URL 追加
// -------------------------------------------------------------
async function handleAddUrl() {
  const url = inputUrl.value.trim()
  if (!url) return

  const res = await boardStore.addBookmark(url, boardStore.selectedFolder, false)
  if (res) {
    inputUrl.value = ''
    toast.success('ライブラリに保存しました', url)
  }
}

// -------------------------------------------------------------
// Drag & Drop（キャンバスへ配置）
// -------------------------------------------------------------
function onDragStart(e: DragEvent, item: BookmarkItem) {
  if (!e.dataTransfer) return
  e.dataTransfer.effectAllowed = 'copy'
  e.dataTransfer.setData('application/reflens-bookmark-id', item.id)
  e.dataTransfer.setData('text/plain', item.title)

  const ghost = new Image()
  ghost.src = resolveImageUrl(item.file_path)
  e.dataTransfer.setDragImage(ghost, 20, 20)
}

async function handlePlaceOnBoard(item: BookmarkItem) {
  await boardStore.placeBookmarkOnBoard(item.id, 200, 200)
}

// -------------------------------------------------------------
// フォルダ
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
    browserWidth.value = Math.max(320, Math.min(760, startWidth + (evt.clientX - startX)))
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
  if (isRemotePixiv.value) return
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
  if (isRemotePixiv.value) loadPixivBookmarks()
})

watch(isRemotePixiv, (active) => {
  if (active) {
    selectedBookmarkId.value = null
    loadPixivBookmarks()
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('reflens:auth-changed', loadPixivBookmarks)
})

const SOURCE_FILTERS = [
  { id: 'all', label: 'すべて', icon: Layers },
  { id: 'pixiv', label: '保存済みpixiv', icon: Compass },
  { id: 'pixiv_bookmarks', label: 'Pixivブックマーク', icon: Compass },
  { id: 'instagram', label: 'Instagram', icon: Instagram },
  { id: 'web_bookmark', label: 'Web', icon: Globe },
] as const
</script>

<template>
  <aside
    class="relative h-full max-w-[65vw] shrink-0 flex flex-col border-r border-canvas-border bg-canvas-panel select-none z-30"
    :style="{
      width: `${browserWidth}px`,
      maxWidth: props.insightOpen
        ? 'min(65vw, max(160px, calc(100vw - min(400px, 34vw) - 320px)))'
        : undefined,
    }"
    aria-label="資料ライブラリ"
  >
    <!-- ヘッダー -->
    <div class="p-3 border-b border-canvas-border space-y-2.5 shrink-0">
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-2 min-w-0">
          <div class="w-6 h-6 rounded-lg bg-brand-soft text-brand flex items-center justify-center shrink-0">
            <Layers class="w-3.5 h-3.5" />
          </div>
          <div class="min-w-0">
            <h2 class="text-[11px] font-bold text-ink tracking-wider">REFERENCE LIBRARY</h2>
            <p class="text-[10px] text-ink-subtle font-mono">資料ライブラリ</p>
          </div>
        </div>

        <div class="flex items-center gap-0.5 p-0.5 rounded-lg border border-canvas-border bg-canvas-card shrink-0">
          <button
            v-for="mode in (['grid-lg', 'grid-sm', 'list'] as const)"
            :key="mode"
            type="button"
            class="p-1 rounded transition-colors"
            :class="viewMode === mode ? 'bg-brand text-brand-fg' : 'text-ink-muted hover:text-ink'"
            :title="mode === 'grid-lg' ? '大サイズグリッド' : mode === 'grid-sm' ? '小サイズグリッド' : 'リスト表示'"
            :aria-label="mode"
            :aria-pressed="viewMode === mode"
            @click="viewMode = mode"
          >
            <LayoutGrid v-if="mode === 'grid-lg'" class="w-3.5 h-3.5" />
            <div v-else-if="mode === 'grid-sm'" class="grid grid-cols-2 gap-[2px] w-3.5 h-3.5">
              <span v-for="i in 4" :key="i" class="bg-current rounded-[1px]" />
            </div>
            <List v-else class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <!-- 検索 -->
      <div class="relative flex items-center">
        <Search class="absolute left-2.5 w-3.5 h-3.5 text-ink-subtle pointer-events-none" />
        <input
          v-model="localSearch"
          type="search"
          :placeholder="isRemotePixiv ? 'このページのPixivブックマークを検索' : 'ライブラリ内を検索'"
          class="w-full bg-canvas-card border border-canvas-border rounded-lg pl-8 pr-3 py-1.5 text-[11px] text-ink placeholder:text-ink-subtle focus:outline-none focus:border-brand transition-colors"
          aria-label="ライブラリ内を検索"
        >
      </div>

      <!-- URL 追加 -->
      <div class="relative flex items-center">
        <Globe class="absolute left-2.5 w-3.5 h-3.5 text-ink-subtle pointer-events-none" />
        <input
          v-model="inputUrl"
          type="url"
          placeholder="pixiv / Instagram / Web 画像URL"
          class="w-full bg-canvas-card border border-canvas-border rounded-lg pl-8 pr-16 py-1.5 text-[11px] text-ink placeholder:text-ink-subtle focus:outline-none focus:border-brand transition-colors font-mono"
          aria-label="URLをライブラリに追加"
          @keydown.enter="handleAddUrl"
        >
        <button
          type="button"
          class="absolute right-1 px-2 py-0.5 rounded-md text-[10px] font-semibold transition-colors disabled:opacity-40"
          :class="boardStore.isAddingBookmark ? 'text-ink-subtle' : 'bg-brand text-brand-fg hover:bg-brand-hover'"
          :disabled="!inputUrl.trim() || boardStore.isAddingBookmark"
          @click="handleAddUrl"
        >
          {{ boardStore.isAddingBookmark ? '...' : '保存' }}
        </button>
      </div>
    </div>

    <!-- ソースフィルタ -->
    <div class="px-2.5 py-2 flex items-center gap-1 overflow-x-auto border-b border-canvas-border no-scrollbar shrink-0">
      <button
        v-for="src in SOURCE_FILTERS"
        :key="src.id"
        type="button"
        class="px-2 py-1 rounded-md text-[11px] font-medium whitespace-nowrap transition-colors flex items-center gap-1"
        :class="boardStore.selectedSourceType === src.id
          ? 'bg-brand text-brand-fg'
          : 'text-ink-muted hover:text-ink hover:bg-canvas-hover'"
        :aria-pressed="boardStore.selectedSourceType === src.id"
        @click="boardStore.selectedSourceType = src.id"
      >
        <component :is="src.icon" class="w-3 h-3" />
        {{ src.label }}
      </button>
    </div>

    <!-- 本体 -->
    <div class="flex-1 flex overflow-hidden">
      <!-- フォルダ一覧 -->
      <div v-if="!isRemotePixiv" class="w-32 shrink-0 border-r border-canvas-border overflow-y-auto p-2 space-y-0.5">
        <p class="text-[10px] font-mono text-ink-subtle uppercase tracking-wider px-2 py-1">
          Collections
        </p>

        <button
          v-for="folder in boardStore.folders"
          :key="folder.name"
          type="button"
          class="w-full text-left px-2 py-1.5 rounded-lg text-[11px] transition-colors flex items-center justify-between gap-1 group"
          :class="boardStore.selectedFolder === folder.name
            ? 'bg-brand-soft text-brand font-semibold'
            : 'text-ink-muted hover:text-ink hover:bg-canvas-hover'"
          :aria-pressed="boardStore.selectedFolder === folder.name"
          @click="boardStore.selectedFolder = folder.name"
        >
          <span class="flex items-center gap-1.5 truncate">
            <span class="w-1.5 h-1.5 rounded-full shrink-0" :style="{ backgroundColor: folder.color || '#6366f1' }" />
            <span class="truncate">{{ folder.name }}</span>
          </span>
          <span class="text-[10px] font-mono text-ink-subtle shrink-0">{{ folder.count }}</span>
        </button>

        <div class="pt-2">
          <div v-if="showNewFolderInput" class="space-y-1">
            <input
              v-model="newFolderName"
              type="text"
              placeholder="フォルダ名"
              class="w-full bg-canvas-card border border-brand rounded px-2 py-1 text-[11px] text-ink focus:outline-none"
              @keydown.enter="handleCreateFolder"
              autofocus
            >
            <div class="flex justify-end gap-1">
              <button
                type="button"
                class="text-[10px] text-ink-muted hover:text-ink"
                @click="showNewFolderInput = false"
              >
                キャンセル
              </button>
              <button
                type="button"
                class="text-[10px] text-brand font-semibold"
                @click="handleCreateFolder"
              >
                作成
              </button>
            </div>
          </div>
          <button
            v-else
            type="button"
            class="w-full text-left px-2 py-1 rounded text-[11px] text-ink-subtle hover:text-ink transition-colors flex items-center gap-1"
            @click="showNewFolderInput = true"
          >
            <Plus class="w-3 h-3" />
            新規フォルダ
          </button>
        </div>
      </div>

      <!-- アイテム一覧 -->
      <div class="flex-1 overflow-y-auto p-2.5">
        <div v-if="isRemotePixiv" class="space-y-2.5">
          <div v-if="!pixiv.isConnected.value" class="py-10 text-center space-y-3">
            <Compass class="w-7 h-7 text-ink-subtle mx-auto" />
            <p class="text-xs text-ink-muted">Pixivへの接続が必要です</p>
            <button v-if="pixiv.canConnect.value" type="button" class="px-3 py-1.5 rounded-lg bg-pixiv text-white text-xs font-semibold" @click="pixiv.connect()">Pixivに接続</button>
            <p v-else class="text-[11px] text-ink-subtle">{{ pixiv.statusMessage.value }}</p>
          </div>
          <div v-else>
            <div class="flex items-center justify-between gap-2 pb-2">
              <span class="text-[11px] text-ink-muted">公開ブックマーク · {{ pixiv.accountName.value }}</span>
              <button type="button" class="text-[11px] text-pixiv hover:underline" :disabled="pixiv.isLoading.value" @click="loadPixivBookmarks">更新</button>
            </div>
            <div v-if="pixiv.isLoading.value" class="py-10 text-center text-xs text-ink-muted">読み込み中…</div>
            <div v-else-if="!displayedPixivBookmarks.length" class="py-10 text-center text-xs text-ink-muted space-y-2">
              <p>{{ pixiv.feedError.value ? 'Pixivの取得に失敗しました' : localSearch ? 'このページに一致する作品がありません' : '公開ブックマークがありません' }}</p>
              <p v-if="pixiv.feedError.value" class="text-danger">{{ pixiv.feedError.value }}</p>
              <p v-else-if="!localSearch">連携先は「{{ pixiv.accountName.value }}」です。別のRefLensアカウントにPixivを連携済みなら、アカウントを切り替えてください。</p>
              <button v-if="!pixiv.feedError.value && !localSearch" type="button" class="px-2.5 py-1 rounded-lg bg-pixiv text-white text-[11px] font-semibold" @click="openAccountSwitcher">RefLensアカウントを切り替える</button>
            </div>
            <div v-else class="grid grid-cols-2 gap-2">
              <figure
                v-for="item in displayedPixivBookmarks"
                :key="item.id"
                draggable="true"
                class="group rounded-lg overflow-hidden bg-canvas-card border border-canvas-border cursor-grab active:cursor-grabbing"
                @dragstart="dragPixivBookmark($event, item)"
              >
                <div class="aspect-square relative bg-canvas-sunken">
                  <PixivImage :src="item.image_url" :alt="item.title" class="w-full h-full object-cover pointer-events-none" loading="lazy" />
                  <button type="button" class="absolute inset-x-2 bottom-2 py-1 rounded-md bg-pixiv text-white text-[10px] font-bold opacity-0 group-hover:opacity-100 focus:opacity-100 disabled:opacity-40" :disabled="pixiv.isImporting.value" @click="placePixivBookmark(item)">キャンバスへ</button>
                </div>
                <figcaption class="p-1.5 space-y-0.5">
                  <p class="text-[10px] font-medium text-ink truncate" :title="item.title">{{ item.title }}</p>
                  <p class="text-[9px] text-ink-subtle truncate">{{ item.author_name }}</p>
                </figcaption>
              </figure>
            </div>
            <div class="flex items-center justify-center gap-2 pt-3 text-[11px] text-ink-muted">
              <button type="button" class="px-2 py-1 rounded hover:bg-canvas-hover disabled:opacity-40" :disabled="pixiv.isLoading.value || pixiv.currentPage.value <= 1" @click="pixiv.prevPage()">前へ</button>
              <span>{{ pixiv.currentPage.value }} ページ</span>
              <button type="button" class="px-2 py-1 rounded hover:bg-canvas-hover disabled:opacity-40" :disabled="pixiv.isLoading.value || !pixiv.hasNext.value" @click="pixiv.nextPage()">次へ</button>
            </div>
          </div>
        </div>
        <div v-else-if="!displayedBookmarks.length" class="py-14 text-center space-y-2">
          <Layers class="w-7 h-7 text-ink-subtle mx-auto" />
          <p class="text-xs text-ink-muted">資料がありません</p>
          <p class="text-[11px] text-ink-subtle leading-relaxed">
            上にURLを貼り付けるか、<br>画像をキャンバスへドラッグしてください
          </p>
        </div>

        <!-- グリッド（大） -->
        <div v-else-if="viewMode === 'grid-lg'" class="grid grid-cols-2 gap-2">
          <figure
            v-for="item in displayedBookmarks"
            :key="item.id"
            draggable="true"
            class="group relative rounded-lg overflow-hidden bg-canvas-card border transition-colors cursor-grab active:cursor-grabbing"
            :class="selectedBookmarkId === item.id
              ? 'border-brand ring-2 ring-brand/30'
              : 'border-canvas-border hover:border-canvas-border-strong'"
            @dragstart="onDragStart($event, item)"
            @click="selectedBookmarkId = item.id"
            @dblclick="boardStore.openQuickLook(item)"
          >
            <div class="relative aspect-square bg-canvas-sunken">
              <img
                :src="resolveImageUrl(item.file_path)"
                :alt="item.title"
                class="w-full h-full object-cover pointer-events-none"
                loading="lazy"
                draggable="false"
              >

              <!-- ソースバッジ -->
              <span
                v-if="item.source_type === 'pixiv'"
                class="absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded text-[9px] font-bold bg-pixiv text-white"
              >
                pixiv
              </span>
              <span
                v-else-if="item.source_type === 'instagram'"
                class="absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded text-[9px] font-bold bg-instagram text-white flex items-center gap-0.5"
              >
                <Instagram class="w-2.5 h-2.5" />
                IG
              </span>
              <span
                v-else
                class="absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded text-[9px] font-medium bg-canvas-panel/90 text-ink-muted border border-canvas-border"
              >
                Web
              </span>

              <!-- ホバー操作 -->
              <div
                class="absolute inset-0 bg-canvas-panel/75 opacity-0 group-hover:opacity-100 transition-opacity p-1.5 flex flex-col justify-between"
              >
                <div class="flex items-center justify-between">
                  <button
                    type="button"
                    class="p-1 rounded bg-canvas-raised text-ink hover:text-brand transition-colors"
                    title="クイックルック (Space)"
                    aria-label="クイックルック"
                    @click.stop="boardStore.openQuickLook(item)"
                  >
                    <Eye class="w-3 h-3" />
                  </button>
                  <a
                    v-if="item.source_url"
                    :href="item.source_url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="p-1 rounded bg-canvas-raised text-ink hover:text-pixiv transition-colors"
                    title="元のページを開く"
                    aria-label="元のページを開く"
                    @click.stop
                  >
                    <ExternalLink class="w-3 h-3" />
                  </a>
                </div>
                <button
                  type="button"
                  class="w-full py-1 rounded-md bg-brand text-brand-fg text-[10px] font-bold hover:bg-brand-hover transition-colors"
                  @click.stop="handlePlaceOnBoard(item)"
                >
                  キャンバスへ
                </button>
              </div>
            </div>

            <figcaption class="p-1.5 bg-canvas-card border-t border-canvas-border space-y-0.5">
              <p class="text-[10px] font-medium text-ink truncate leading-tight" :title="item.title">
                {{ item.title }}
              </p>
              <p class="text-[9px] text-ink-subtle truncate">{{ item.author_name || item.folder_name }}</p>
            </figcaption>
          </figure>
        </div>

        <!-- グリッド（小） -->
        <div v-else-if="viewMode === 'grid-sm'" class="grid grid-cols-3 gap-1.5">
          <div
            v-for="item in displayedBookmarks"
            :key="item.id"
            draggable="true"
            class="group relative rounded-md overflow-hidden bg-canvas-card border transition-colors cursor-grab active:cursor-grabbing aspect-square"
            :class="selectedBookmarkId === item.id ? 'border-brand ring-2 ring-brand/30' : 'border-canvas-border'"
            @dragstart="onDragStart($event, item)"
            @click="selectedBookmarkId = item.id"
            @dblclick="boardStore.openQuickLook(item)"
          >
            <img
              :src="resolveImageUrl(item.file_path)"
              :alt="item.title"
              class="w-full h-full object-cover pointer-events-none"
              loading="lazy"
              draggable="false"
            >
            <div
              class="absolute inset-0 bg-canvas-panel/75 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
            >
              <button
                type="button"
                class="p-1 rounded-md bg-brand text-brand-fg text-[9px] font-bold"
                @click.stop="handlePlaceOnBoard(item)"
              >
                + 配置
              </button>
            </div>
          </div>
        </div>

        <!-- リスト -->
        <div v-else class="space-y-0.5">
          <div
            v-for="item in displayedBookmarks"
            :key="item.id"
            draggable="true"
            class="group px-2 py-1.5 rounded-lg border transition-colors cursor-grab active:cursor-grabbing flex items-center gap-2"
            :class="selectedBookmarkId === item.id
              ? 'bg-brand-soft border-brand/40'
              : 'bg-canvas-card border-transparent hover:border-canvas-border hover:bg-canvas-hover'"
            @dragstart="onDragStart($event, item)"
            @click="selectedBookmarkId = item.id"
            @dblclick="boardStore.openQuickLook(item)"
          >
            <GripVertical class="w-3 h-3 text-ink-subtle shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
            <img
              :src="resolveImageUrl(item.file_path)"
              :alt="item.title"
              class="w-7 h-7 rounded object-cover shrink-0 pointer-events-none"
              loading="lazy"
            >
            <div class="flex-1 min-w-0">
              <p class="text-[11px] font-medium text-ink truncate">{{ item.title }}</p>
              <p class="text-[10px] text-ink-subtle truncate">{{ item.author_name || item.folder_name }}</p>
            </div>
            <button
              type="button"
              class="opacity-0 group-hover:opacity-100 p-1 rounded bg-brand text-brand-fg text-[10px] px-1.5 transition-opacity shrink-0"
              @click.stop="handlePlaceOnBoard(item)"
            >
              配置
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- フッター -->
    <div
      class="p-2 border-t border-canvas-border flex items-center justify-between text-[11px] shrink-0"
    >
      <span class="text-ink-subtle">{{ isRemotePixiv ? displayedPixivBookmarks.length : displayedBookmarks.length }} 件</span>
      <div class="flex items-center gap-2">
        <button
          v-if="selectedBookmarkId && !isRemotePixiv"
          type="button"
          class="p-1 rounded text-ink-subtle hover:text-danger hover:bg-danger-soft transition-colors"
          title="削除 (Delete)"
          aria-label="削除"
          @click="boardStore.deleteBookmark(selectedBookmarkId); selectedBookmarkId = null"
        >
          <Trash2 class="w-3.5 h-3.5" />
        </button>
        <span class="text-ink-subtle">{{ isRemotePixiv ? 'Pixiv作品をドラッグで配置' : 'ドラッグでキャンバスへ' }}</span>
      </div>
    </div>

    <!-- リサイズハンドル -->
    <div
      class="absolute top-0 -right-1 w-2 h-full cursor-col-resize hover:bg-brand/40 transition-colors z-40"
      title="幅を変更"
      @mousedown.stop="startResize"
    />
  </aside>
</template>
