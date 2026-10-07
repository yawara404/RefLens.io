<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import {
  FolderOpen,
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
  Keyboard,
} from 'lucide-vue-next'
import AppHeader from '~/components/ui/AppHeader.vue'
import ThemeToggle from '~/components/ui/ThemeToggle.vue'
import QuickLookModal from '~/components/browser/QuickLookModal.vue'
import BookmarkActionsMenu from '~/components/ui/BookmarkActionsMenu.vue'
import type { BookmarkItem } from '~/types'
import { useBoardStore } from '~/stores/boardStore'
import { useHelpStore } from '~/stores/helpStore'
import { useMediaUrl } from '~/composables/useMediaUrl'
import { useToast } from '~/composables/useToast'

const boardStore = useBoardStore()
const helpStore = useHelpStore()
const toast = useToast()
const { resolveMediaUrl } = useMediaUrl()

const inputDropUrl = ref('')
const isDropping = ref(false)
const searchQuery = ref('')
const selectedSource = ref<'all' | 'pixiv' | 'instagram' | 'web_bookmark' | 'local_upload'>('all')
const selectedFolder = ref('All References')
const viewMode = ref<'grid' | 'list'>('grid')

const showNewFolder = ref(false)
const newFolderName = ref('')

const SOURCE_FILTERS = [
  { id: 'all', label: 'すべて', icon: FolderOpen },
  { id: 'pixiv', label: 'pixiv', icon: Compass },
  { id: 'instagram', label: 'Instagram', icon: Instagram },
  { id: 'web_bookmark', label: 'Web', icon: Globe },
] as const

const filteredBookmarks = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()

  return boardStore.bookmarks.filter(b => {
    if (selectedSource.value !== 'all' && b.source_type !== selectedSource.value) return false
    if (selectedFolder.value !== 'All References' && b.folder_name !== selectedFolder.value) return false
    if (!q) return true

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

function resolveThumbnail(path?: string) {
  return resolveMediaUrl(path)
}

async function handleDropUrl() {
  const url = inputDropUrl.value.trim()
  if (!url || isDropping.value) return

  isDropping.value = true
  inputDropUrl.value = ''

  const res = await boardStore.addBookmark(url, selectedFolder.value, false)
  if (res) toast.success('ライブラリに保存しました', url)
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
  newFolderName.value = ''
  showNewFolder.value = false
  await boardStore.createFolder(name)
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
  await Promise.all([boardStore.fetchBookmarks(), boardStore.fetchFolders()])
  // サイドバーの「キャンバスを開く」リンク用に最初のボードをロードしておく
  await boardStore.loadFirstBoard()
})
</script>

<template>
  <div class="min-h-screen bg-canvas-bg text-ink flex flex-col antialiased">
    <AppHeader />

    <div class="flex-1 flex max-w-[1680px] w-full mx-auto overflow-hidden">
      <!-- サイドバー -->
      <aside
        class="w-60 shrink-0 border-r border-canvas-border bg-canvas-panel p-3.5 space-y-5 hidden md:flex flex-col justify-between overflow-y-auto"
      >
        <div class="space-y-4">
          <!-- フォルダ -->
          <div>
            <div class="flex items-center justify-between px-1 mb-1.5">
              <span class="text-[10px] font-mono text-ink-subtle uppercase tracking-wider">Collections</span>
              <button
                type="button"
                class="p-0.5 rounded text-ink-subtle hover:text-ink transition-colors"
                title="新規フォルダ"
                aria-label="新規フォルダ"
                @click="showNewFolder = !showNewFolder"
              >
                <Plus class="w-3.5 h-3.5" />
              </button>
            </div>

            <div
              v-if="showNewFolder"
              class="p-2 rounded-lg bg-canvas-card border border-brand space-y-1.5 mb-1.5"
            >
              <input
                v-model="newFolderName"
                type="text"
                placeholder="フォルダ名"
                class="w-full bg-canvas-bg border border-canvas-border rounded px-2 py-1 text-[11px] text-ink focus:outline-none focus:border-brand"
                @keydown.enter="handleCreateFolder"
                autofocus
              >
              <div class="flex justify-end gap-1.5">
                <button
                  type="button"
                  class="text-[10px] text-ink-muted hover:text-ink px-1"
                  @click="showNewFolder = false"
                >
                  キャンセル
                </button>
                <button
                  type="button"
                  class="text-[10px] text-brand font-semibold px-1"
                  @click="handleCreateFolder"
                >
                  作成
                </button>
              </div>
            </div>

            <button
              v-for="folder in boardStore.folders"
              :key="folder.name"
              type="button"
              class="w-full text-left px-2.5 py-1.5 rounded-lg text-[11px] transition-colors flex items-center justify-between gap-2 group"
              :class="selectedFolder === folder.name
                ? 'bg-brand-soft text-brand font-semibold'
                : 'text-ink-muted hover:text-ink hover:bg-canvas-hover'"
              :aria-pressed="selectedFolder === folder.name"
              @click="selectedFolder = folder.name"
            >
              <span class="flex items-center gap-2 truncate">
                <span
                  class="w-2 h-2 rounded-full shrink-0"
                  :style="{ backgroundColor: folder.color || '#6366f1' }"
                />
                <span class="truncate">{{ folder.name }}</span>
              </span>
              <span class="text-[10px] font-mono text-ink-subtle shrink-0">{{ folder.count }}</span>
            </button>
          </div>

          <!-- ソース -->
          <div class="pt-3 border-t border-canvas-border">
            <p class="text-[10px] font-mono text-ink-subtle uppercase tracking-wider px-1 mb-1.5">
              Source
            </p>
            <button
              v-for="src in SOURCE_FILTERS"
              :key="src.id"
              type="button"
              class="w-full text-left px-2.5 py-1.5 rounded-lg text-[11px] transition-colors flex items-center gap-2"
              :class="selectedSource === src.id
                ? 'bg-canvas-hover text-ink font-semibold'
                : 'text-ink-muted hover:text-ink hover:bg-canvas-hover'"
              :aria-pressed="selectedSource === src.id"
              @click="selectedSource = src.id"
            >
              <component :is="src.icon" class="w-3.5 h-3.5" />
              {{ src.label }}
            </button>
          </div>
        </div>

        <!-- アクティブなボード -->
        <div
          v-if="boardStore.currentBoard"
          class="p-2.5 rounded-xl bg-canvas-card border border-canvas-border space-y-1.5"
        >
          <p class="text-[10px] font-semibold text-ink flex items-center gap-1.5">
            <Layers class="w-3.5 h-3.5 text-brand" />
            Active Board
          </p>
          <p class="text-[11px] text-ink-muted truncate">{{ boardStore.currentBoard.title }}</p>
          <NuxtLink
            :to="`/board/${boardStore.currentBoard.id}`"
            class="block w-full py-1.5 bg-brand text-brand-fg rounded-lg text-[11px] font-bold text-center hover:bg-brand-hover transition-colors"
          >
            キャンバスを開く
          </NuxtLink>
        </div>
      </aside>

      <!-- メイン -->
      <main class="flex-1 overflow-y-auto px-4 md:px-6 py-5 space-y-5">
        <!-- Drop & Stash -->
        <section class="p-4 rounded-2xl bg-canvas-panel border border-canvas-border space-y-3">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div class="min-w-0">
              <h2 class="text-sm font-bold text-ink flex items-center gap-2">
                <Bookmark class="w-4 h-4 text-pixiv" />
                Drop &amp; Stash Reference
              </h2>
              <p class="text-[11px] text-ink-muted mt-0.5">
                pixiv・Instagram・Web画像URLを貼り付けてライブラリへ保存
              </p>
            </div>

            <div class="flex items-center gap-1.5 shrink-0">
              <NuxtLink
                to="/view"
                class="px-2.5 py-1 rounded-full text-[11px] font-medium bg-pixiv-soft text-pixiv border border-pixiv/30 hover:border-pixiv transition-colors"
              >
                pixivで探す
              </NuxtLink>
              <button
                type="button"
                class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
                title="ショートカット一覧 (?)"
                aria-label="ショートカット一覧"
                @click="helpStore.toggle()"
              >
                <Keyboard class="w-4 h-4" />
              </button>
              <ThemeToggle />
            </div>
          </div>

          <div class="relative flex items-center">
            <Globe class="absolute left-3.5 w-4 h-4 text-ink-subtle pointer-events-none" />
            <input
              v-model="inputDropUrl"
              type="url"
              placeholder="https://www.pixiv.net/artworks/..."
              class="w-full bg-canvas-card border border-canvas-border rounded-xl pl-10 pr-28 py-2.5 text-xs text-ink placeholder:text-ink-subtle focus:outline-none focus:border-pixiv font-mono transition-colors"
              aria-label="URLをライブラリへ保存"
              @keydown.enter="handleDropUrl"
            >
            <button
              type="button"
              class="absolute right-2 px-3.5 py-1.5 bg-brand text-brand-fg hover:bg-brand-hover rounded-lg text-[11px] font-bold transition-colors disabled:opacity-50 flex items-center gap-1.5"
              :disabled="!inputDropUrl.trim() || isDropping"
              @click="handleDropUrl"
            >
              <Check class="w-3.5 h-3.5" />
              {{ isDropping ? '保存中...' : '保存' }}
            </button>
          </div>
        </section>

        <!-- ツールバー -->
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div class="relative flex-1 max-w-md">
            <Search class="absolute left-3 w-3.5 h-3.5 text-ink-subtle pointer-events-none" />
            <input
              v-model="searchQuery"
              type="search"
              placeholder="タイトル・作者・タグ・構図で検索"
              class="w-full bg-canvas-card border border-canvas-border rounded-full pl-8 pr-3 py-2 text-xs text-ink placeholder:text-ink-subtle focus:outline-none focus:border-brand transition-colors"
              aria-label="ライブラリを検索"
            >
          </div>

          <div class="flex items-center gap-3 shrink-0">
            <span class="text-[11px] text-ink-muted font-mono">{{ filteredBookmarks.length }} 件</span>
            <div class="flex items-center gap-0.5 p-0.5 rounded-lg border border-canvas-border bg-canvas-card">
              <button
                type="button"
                class="p-1.5 rounded-md transition-colors"
                :class="viewMode === 'grid' ? 'bg-brand text-brand-fg' : 'text-ink-muted hover:text-ink'"
                title="グリッド表示"
                aria-label="グリッド表示"
                @click="viewMode = 'grid'"
              >
                <LayoutGrid class="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                class="p-1.5 rounded-md transition-colors"
                :class="viewMode === 'list' ? 'bg-brand text-brand-fg' : 'text-ink-muted hover:text-ink'"
                title="リスト表示"
                aria-label="リスト表示"
                @click="viewMode = 'list'"
              >
                <List class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        <!-- グリッド -->
        <div v-if="viewMode === 'grid'" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3.5">
          <figure
            v-for="b in filteredBookmarks"
            :key="b.id"
            class="group relative flex flex-col rounded-xl bg-canvas-card border border-canvas-border transition-colors cursor-pointer hover:border-brand/50"
            @click="boardStore.openQuickLook(b)"
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

              <!-- ホバー -->
              <div
                class="absolute inset-0 bg-canvas-panel/75 opacity-0 group-hover:opacity-100 transition-opacity p-2 flex flex-col justify-between"
              >
                <div class="flex justify-end">
                  <a
                    v-if="b.source_url"
                    :href="b.source_url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="p-1.5 rounded-lg bg-canvas-raised text-ink hover:text-pixiv transition-colors"
                    title="元のページを開く"
                    aria-label="元のページを開く"
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

            <BookmarkActionsMenu
              class="absolute top-2 right-2"
              :item="b"
              :folders="boardStore.folders"
              @place="handlePlaceOnBoard(b)"
              @move="handleMoveBookmark(b, $event)"
              @delete="handleDeleteBookmark(b)"
            />

            <figcaption class="p-2.5 rounded-b-xl bg-canvas-card space-y-1.5 flex-1 flex flex-col">
              <p class="text-[11px] font-semibold text-ink truncate" :title="b.title">{{ b.title }}</p>
              <p class="text-[10px] text-ink-subtle truncate">{{ b.author_name || b.folder_name }}</p>

              <div v-if="b.ai_analysis?.palette?.length" class="flex items-center gap-1 mt-auto pt-1">
                <span
                  v-for="(hex, idx) in b.ai_analysis.palette.slice(0, 5)"
                  :key="idx"
                  class="w-2.5 h-2.5 rounded-full border border-canvas-border"
                  :style="{ backgroundColor: hex }"
                  :title="hex"
                />
              </div>
            </figcaption>
          </figure>
        </div>

        <!-- リスト -->
        <div v-else class="space-y-1.5">
          <div
            v-for="b in filteredBookmarks"
            :key="b.id"
            class="group relative flex items-center gap-3 p-2.5 rounded-xl bg-canvas-card border border-transparent hover:border-canvas-border cursor-pointer transition-colors"
            @click="boardStore.openQuickLook(b)"
          >
            <img
              :src="resolveThumbnail(b.file_path)"
              :alt="b.title"
              class="w-12 h-12 rounded-lg object-cover shrink-0 bg-canvas-sunken"
              loading="lazy"
            >
            <div class="flex-1 min-w-0">
              <p class="text-xs font-semibold text-ink truncate">{{ b.title }}</p>
              <p class="text-[11px] text-ink-subtle truncate">
                <span class="capitalize">{{ b.source_type }}</span> ·
                {{ b.author_name || b.folder_name }}
              </p>
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
          v-if="!filteredBookmarks.length"
          class="py-20 text-center space-y-3"
        >
          <Bookmark class="w-8 h-8 text-ink-subtle mx-auto" />
          <p class="text-sm text-ink-muted">
            {{ boardStore.bookmarks.length ? '条件に一致する資料がありません' : 'ライブラリは空です' }}
          </p>
          <p class="text-xs text-ink-subtle">
            {{ boardStore.bookmarks.length ? '検索条件を変更してください' : '上の入力欄にURLを貼り付けるか、pixivから取り込んでください' }}
          </p>
          <NuxtLink
            to="/view"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-pixiv text-white text-xs font-semibold hover:bg-pixiv-hover transition-colors"
          >
            <Compass class="w-3.5 h-3.5" />
            pixivクライアントを開く
          </NuxtLink>
        </div>
      </main>
    </div>

    <QuickLookModal />
  </div>
</template>
