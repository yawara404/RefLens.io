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
} from 'lucide-vue-next'
import AppHeader from '~/components/ui/AppHeader.vue'
import PixivImage from '~/components/ui/PixivImage.vue'
import QuickLookModal from '~/components/browser/QuickLookModal.vue'
import { useBoardStore } from '~/stores/boardStore'
import { usePixiv, type PixivArtwork } from '~/composables/usePixiv'
import { useBackendUrl } from '~/composables/useBackendUrl'
import { useMediaUrl } from '~/composables/useMediaUrl'
import { useToast } from '~/composables/useToast'

const boardStore = useBoardStore()
const pixiv = usePixiv()
const toast = useToast()
const { apiBase } = useBackendUrl()
const { resolveMediaUrl } = useMediaUrl()

const searchInput = ref('')
const viewMainRef = ref<HTMLElement | null>(null)
const activeCategory = ref('recommended')
const savedBookmarks = computed(() => {
  const query = searchInput.value.trim().toLowerCase()
  const pixivBookmarks = boardStore.bookmarks.filter(item => item.source_type === 'pixiv')
  return query
    ? pixivBookmarks.filter(item => [item.title, item.author_name || '', item.source_url || '', item.folder_name || ''].join(' ').toLowerCase().includes(query))
    : pixivBookmarks
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

const isSidebarOpen = ref(false)

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
  // モバイルではサイドバーを閉じて結果を全面表示させる
  if (window.matchMedia('(max-width: 1023px)').matches) isSidebarOpen.value = false
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
  const count = await pixiv.stockToLibrary(ids)
  isStashing.value = false

  if (!count) return

  await boardStore.fetchBookmarks()
  await boardStore.fetchFolders()
  toast.success('RefLensのライブラリに保存しました')
  pixiv.clearSelection()
  closeDetail()
  searchInput.value = ''
  activeCategory.value = 'saved'
  await nextTick()
  if (viewMainRef.value) viewMainRef.value.scrollTop = 0
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
  const count = await pixiv.stockToCanvas(ids, boardId)
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

onMounted(async () => {
  await pixiv.init()
  boardStore.fetchBookmarks()

  // ログイン / ログアウトでユーザーごとに変わる
  // pixiv の接続状態（トークンはユーザーごとに持つ）を取り直す
  window.addEventListener('reflens:auth-changed', onAuthChanged)
})

onUnmounted(() => window.removeEventListener('reflens:auth-changed', onAuthChanged))
</script>

<template>
  <div class="min-h-screen bg-canvas-bg text-ink flex flex-col antialiased">
    <AppHeader />

    <!-- サブヘッダー: 接続状態と検索（カテゴリはサイドバーへ移動） -->
    <div class="border-b border-canvas-border bg-canvas-panel px-4 md:px-6 py-2.5 sticky top-14 z-30">
      <div class="max-w-[1600px] mx-auto flex items-center gap-2.5">
        <!-- モバイル: サイドバー開閉 -->
        <button
          type="button"
          class="lg:hidden p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors shrink-0"
          :aria-expanded="isSidebarOpen"
          aria-label="カテゴリメニュー"
          @click="isSidebarOpen = !isSidebarOpen"
        >
          <Menu class="w-4 h-4" />
        </button>

        <!-- タイトルと接続状態 -->
        <div class="flex items-center gap-2 min-w-0 shrink-0">
          <span class="px-2 py-0.5 rounded-md text-[11px] font-bold bg-pixiv text-white font-mono">
            pixiv
          </span>

          <template v-if="pixiv.isConnected.value">
            <PixivImage
              v-if="pixiv.status.value?.account?.avatar_url"
              :src="pixiv.proxyImage(pixiv.status.value.account.avatar_url)"
              :alt="pixiv.accountName.value"
              class="w-5 h-5 rounded-full shrink-0"
            />
            <span class="text-[11px] text-ink-muted truncate hidden sm:inline">
              <span class="text-pixiv font-medium">{{ pixiv.accountName.value }}</span>
            </span>
            <button
              type="button"
              class="p-1 rounded text-ink-subtle hover:text-danger hover:bg-danger-soft transition-colors shrink-0"
              title="接続を解除"
              aria-label="pixiv接続を解除"
              @click="pixiv.disconnect()"
            >
              <LogOut class="w-3.5 h-3.5" />
            </button>
          </template>
          <button
            v-else-if="pixiv.canConnect.value"
            type="button"
            class="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-pixiv text-white hover:bg-pixiv-hover transition-colors shrink-0"
            @click="pixiv.connect()"
          >
            Pixivに接続
          </button>
          <span v-else class="text-[11px] text-ink-subtle hidden sm:inline">デモフィード</span>
        </div>

        <!-- 検索 -->
        <form
          class="relative flex-1 flex items-center min-w-0"
          @submit.prevent="submitSearch"
        >
          <Search class="absolute left-3 w-3.5 h-3.5 text-ink-subtle pointer-events-none" />
          <input
            v-model="searchInput"
            type="search"
            :placeholder="activeCategory === 'saved' ? 'RefLensに保存したpixiv作品を検索' : 'タグ・キーワードで検索（例: ポーズ参考、逆光、衣装）'"
            class="w-full bg-canvas-card border border-canvas-border rounded-full pl-8 pr-8 py-1.5 text-xs text-ink placeholder:text-ink-subtle focus:outline-none focus:border-pixiv transition-colors"
            aria-label="pixiv作品を検索"
          >
          <button
            v-if="searchInput"
            type="button"
            class="absolute right-2.5 text-ink-subtle hover:text-ink transition-colors"
            aria-label="検索をクリア"
            @click="searchInput = ''"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </form>

        <!-- 更新 -->
        <button
          type="button"
          class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors shrink-0"
          title="再読み込み"
          aria-label="再読み込み"
          @click="activeCategory === 'saved' ? boardStore.fetchBookmarks() : pixiv.loadFeed()"
        >
          <RefreshCw class="w-4 h-4" :class="activeCategory !== 'saved' && pixiv.isLoading.value ? 'animate-spin' : ''" />
        </button>
      </div>
    </div>

    <!-- ワークスペース: サイドバー + 作品グリッド -->
    <div class="flex-1 flex max-w-[1600px] w-full mx-auto overflow-hidden">
      <!-- サイドバー: カテゴリ + 検索フィルタ -->
      <aside
        class="w-56 shrink-0 border-r border-canvas-border bg-canvas-panel overflow-y-auto shrink-0"
        :class="isSidebarOpen ? 'fixed inset-y-0 left-0 top-14 z-40 w-64 shadow-pop' : 'hidden lg:block'"
        aria-label="pixivカテゴリ"
      >
        <div class="p-3 space-y-4">
          <!-- カテゴリ -->
          <nav>
            <p class="text-[10px] font-mono text-ink-subtle uppercase tracking-wider px-1 mb-1.5">
              Browse
            </p>
            <button
              v-for="cat in CATEGORIES"
              :key="cat.id"
              type="button"
              class="w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-[11px] transition-colors text-left"
              :class="activeCategory === cat.id
                ? 'bg-brand-soft text-brand font-semibold'
                : 'text-ink-muted hover:text-ink hover:bg-canvas-hover'"
              :disabled="isCategoryDisabled(cat)"
              :title="isCategoryDisabled(cat) ? 'Pixivに接続すると利用できます' : cat.hint"
              :aria-current="activeCategory === cat.id ? 'page' : undefined"
              @click="pickCategory(cat.id)"
            >
              <component :is="cat.icon" class="w-3.5 h-3.5 shrink-0" />
              <span class="flex-1">{{ cat.label }}</span>
              <span
                v-if="isCategoryDisabled(cat)"
                class="text-[9px] text-ink-subtle shrink-0"
              >要ログイン</span>
            </button>
          </nav>

          <!-- 検索フィルタ（検索カテゴリのときだけ有効） -->
          <div class="pt-3 border-t border-canvas-border space-y-3">
            <p class="text-[10px] font-mono text-ink-subtle uppercase tracking-wider px-1 flex items-center gap-1">
              <SlidersHorizontal class="w-3 h-3" />
              Filters
            </p>

            <fieldset :disabled="activeCategory !== 'search'" class="space-y-2 disabled:opacity-40">
              <legend class="sr-only">ソート順</legend>
              <div>
                <p class="text-[10px] text-ink-muted mb-1 px-1">並び順</p>
                <div class="space-y-0.5">
                  <label
                    v-for="opt in SORT_OPTIONS"
                    :key="opt.id"
                    class="flex items-center gap-2 px-2 py-1.5 rounded-md text-[11px] cursor-pointer hover:bg-canvas-hover transition-colors"
                    :class="sortMode === opt.id ? 'text-brand font-semibold' : 'text-ink-muted'"
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
                <p class="text-[10px] text-ink-muted mb-1 px-1">投稿期間</p>
                <select
                  v-model="durationMode"
                  class="w-full bg-canvas-card border border-canvas-border rounded-lg px-2 py-1.5 text-[11px] text-ink focus:outline-none focus:border-pixiv transition-colors"
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
            <p class="text-[10px] font-mono text-ink-subtle uppercase tracking-wider px-1 mb-1.5">
              Account
            </p>
            <div v-if="pixiv.isConnected.value" class="px-2.5 py-2 rounded-lg bg-canvas-card border border-canvas-border">
              <div class="flex items-center gap-2">
                <PixivImage
                  v-if="pixiv.status.value?.account?.avatar_url"
                  :src="pixiv.proxyImage(pixiv.status.value.account.avatar_url)"
                  :alt="pixiv.accountName.value"
                  class="w-6 h-6 rounded-full shrink-0"
                />
                <div class="min-w-0">
                  <p class="text-[11px] font-medium text-ink truncate">{{ pixiv.accountName.value }}</p>
                  <p v-if="pixiv.status.value?.account?.account" class="text-[10px] text-ink-subtle truncate">
                    @{{ pixiv.status.value.account.account }}
                  </p>
                </div>
              </div>
            </div>
            <div v-else class="px-2.5 py-2 rounded-lg bg-canvas-card border border-canvas-border space-y-1.5">
              <p class="text-[11px] text-ink-muted leading-relaxed">
                {{ pixiv.statusMessage.value || 'デモフィードを表示中' }}
              </p>
              <button
                v-if="pixiv.canConnect.value"
                type="button"
                class="w-full py-1.5 rounded-lg bg-pixiv text-white text-[11px] font-semibold hover:bg-pixiv-hover transition-colors"
                @click="pixiv.connect()"
              >
                Pixivでログイン
              </button>
            </div>
          </div>
        </div>
      </aside>

      <!-- モバイル時のサイドバー背景 -->
      <div
        v-if="isSidebarOpen"
        class="lg:hidden fixed inset-0 top-14 bg-canvas-bg/60 z-30"
        @click="isSidebarOpen = false"
      />

      <!-- 作品グリッド -->
      <main ref="viewMainRef" class="flex-1 overflow-y-auto px-4 md:px-6 py-5 min-w-0">
      <!-- 通知バー -->
      <div
        v-if="activeCategory !== 'saved' && pixiv.notice.value"
        class="mb-4 flex items-start gap-2 p-3 rounded-xl border border-canvas-border bg-canvas-card"
      >
        <Info class="w-3.5 h-3.5 text-ink-subtle shrink-0 mt-px" />
        <p class="text-[11px] text-ink-muted leading-relaxed">{{ pixiv.notice.value }}</p>
      </div>

      <!-- RefLensに保存したブックマーク -->
      <div v-if="activeCategory === 'saved'">
        <div v-if="!savedBookmarks.length" class="py-24 text-center space-y-3">
          <Bookmark class="w-8 h-8 text-ink-subtle mx-auto" />
          <p class="text-sm text-ink-muted">{{ searchInput ? '検索に一致するpixiv作品がありません' : 'RefLensに保存したpixiv作品はありません' }}</p>
          <p class="text-xs text-ink-subtle">{{ searchInput ? '検索語を変えてください' : 'Pixiv作品の「ライブラリへ保存」で追加できます' }}</p>
        </div>
        <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          <article
            v-for="item in savedBookmarks"
            :key="item.id"
            class="group rounded-xl border border-canvas-border bg-canvas-card overflow-hidden cursor-pointer hover:border-canvas-border-strong transition-colors"
            @click="boardStore.openQuickLook(item)"
          >
            <div class="relative aspect-[4/3] bg-canvas-sunken overflow-hidden">
              <img :src="resolveMediaUrl(item.file_path)" :alt="item.title" class="w-full h-full object-cover" loading="lazy">
              <span class="absolute top-2 left-2 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-canvas-panel/90 text-ink">{{ item.source_type === 'pixiv' ? 'pixiv' : item.source_type === 'instagram' ? 'Instagram' : 'Web' }}</span>
            </div>
            <div class="p-2.5 space-y-1">
              <h3 class="text-[11px] font-semibold text-ink line-clamp-2" :title="item.title">{{ item.title }}</h3>
              <p class="text-[10px] text-ink-subtle truncate">{{ item.author_name || item.folder_name || item.source_url }}</p>
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
          class="group flex flex-col rounded-xl border bg-canvas-card overflow-hidden transition-colors cursor-pointer"
          :class="pixiv.isSelected(item.id)
            ? 'border-pixiv ring-2 ring-pixiv/40'
            : 'border-canvas-border hover:border-canvas-border-strong'"
          @click="openDetail(item)"
        >
          <!-- サムネイル -->
          <div class="relative aspect-[4/3] bg-canvas-sunken overflow-hidden">
            <PixivImage
              :src="item.image_url"
              :alt="item.title"
              class="w-full h-full object-cover pointer-events-none"
              loading="lazy"
            />

            <!-- 選択チェック -->
            <button
              type="button"
              class="absolute top-2 right-2 w-5 h-5 rounded-full border flex items-center justify-center transition-all"
              :class="pixiv.isSelected(item.id)
                ? 'bg-pixiv border-pixiv opacity-100'
                : 'bg-canvas-panel/85 border-canvas-border-strong opacity-0 group-hover:opacity-100'"
              :aria-label="pixiv.isSelected(item.id) ? '選択解除' : '選択'"
              @click.stop="toggleSelect(item.id)"
            >
              <Check v-if="pixiv.isSelected(item.id)" class="w-3 h-3 text-white stroke-[3]" />
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

            <!-- ホバー: クイックアクション -->
            <div
              class="absolute inset-0 bg-canvas-panel/70 opacity-0 group-hover:opacity-100 transition-opacity p-2.5 flex flex-col justify-between"
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
                  @click="pixiv.selectedIds.value.includes(item.id)
                    ? toggleSelect(item.id)
                    : (pixiv.clearSelection(), toggleSelect(item.id))"
                >
                  <Bookmark class="w-3 h-3" />
                  {{ pixiv.isSelected(item.id) ? '選択済み' : '選択' }}
                </button>
              </div>
            </div>
          </div>

          <!-- 情報 -->
          <div class="p-2.5 bg-canvas-card space-y-1.5 flex-1 flex flex-col">
            <h3 class="text-[11px] font-semibold text-ink line-clamp-2 leading-snug" :title="item.title">
              {{ item.title }}
            </h3>

            <div class="flex items-center gap-1.5 text-[10px] text-ink-subtle">
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
                class="px-1.5 py-0.5 rounded text-[10px] bg-canvas-raised text-ink-muted border border-canvas-border hover:text-pixiv hover:border-pixiv transition-colors truncate max-w-[90px]"
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
      class="sticky bottom-4 z-40 flex justify-center px-4 pointer-events-none"
    >
      <div
        class="pointer-events-auto flex items-center gap-3 floating-bar px-4 py-2 rounded-2xl animate-slide-up"
      >
        <button
          type="button"
          class="text-[11px] text-ink-subtle hover:text-ink transition-colors"
          @click="toggleSelectAll"
        >
          {{ allSelected ? '選択解除' : 'すべて選択' }}
        </button>
        <span class="text-[11px] text-ink-muted">
          <span class="text-ink font-semibold">{{ pixiv.selectedIds.value.length }}</span> 件選択中
        </span>
        <div class="h-4 w-px bg-canvas-border" />
        <button
          type="button"
          class="px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-pixiv text-white hover:bg-pixiv-hover transition-colors disabled:opacity-50 flex items-center gap-1"
          :disabled="isStashing || pixiv.isImporting.value"
          @click="stashSelected"
        >
          <RefreshCw v-if="isStashing" class="w-3 h-3 animate-spin" />
          <Bookmark v-else class="w-3 h-3" />
          {{ isStashing ? '保存中...' : 'ライブラリへ' }}
        </button>
        <button
          type="button"
          class="px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-brand text-brand-fg hover:bg-brand-hover transition-colors disabled:opacity-50 flex items-center gap-1"
          :disabled="pixiv.isImporting.value"
          @click="placeSelectedOnCanvas"
        >
          <Layers class="w-3 h-3" />
          キャンバスへ
        </button>
      </div>
    </div>

    <!-- 作品詳細モーダル -->
    <Teleport to="body">
      <div
        v-if="activeArtwork"
        class="fixed inset-0 z-[65] flex items-center justify-center p-4 md:p-6 scrim animate-fade-in"
        @click.self="closeDetail"
      >
        <div
          class="w-full max-w-5xl max-h-[90vh] rounded-2xl border border-canvas-border bg-canvas-panel shadow-pop flex flex-col md:flex-row overflow-hidden animate-scale-in"
          role="dialog"
          aria-modal="true"
          :aria-label="activeArtwork.title"
        >
          <!-- 画像 -->
          <div class="flex-1 bg-canvas-sunken relative flex items-center justify-center p-4 min-h-[320px]">
            <PixivImage
              v-if="activePageImage"
              :src="activePageImage.image_url"
              :alt="activeArtwork.title"
              class="max-w-full max-h-full object-contain rounded-lg"
            />
            <div v-else class="w-8 h-8 rounded-full border-2 border-brand border-t-transparent animate-spin" />

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
            class="w-full md:w-96 border-t md:border-t-0 md:border-l border-canvas-border p-4 flex flex-col gap-4 overflow-y-auto"
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

              <button
                type="button"
                class="w-full py-2 rounded-lg bg-pixiv text-white text-xs font-bold hover:bg-pixiv-hover transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
                :disabled="isStashing || pixiv.isImporting.value"
                @click="handleStashDetail"
              >
                <Bookmark class="w-3.5 h-3.5" />
                {{ isStashing ? '保存中...' : 'ライブラリへ保存' }}
              </button>

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
    <QuickLookModal />
  </div>
</template>
