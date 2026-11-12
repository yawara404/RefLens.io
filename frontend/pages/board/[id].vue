<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  Bookmark,
  Check,
  Loader2,
  RefreshCw,
  Edit2,
  Search,
  Sparkles,
  X,
} from 'lucide-vue-next'
import type { CanvasItem } from '~/types'
import { useBoardStore } from '~/stores/boardStore'
import { useMobileNav } from '~/composables/useMobileNav'
import AppHeader from '~/components/ui/AppHeader.vue'
import InfiniteCanvas from '~/components/canvas/InfiniteCanvas.vue'
import AIInsightDrawer from '~/components/panel/AIInsightDrawer.vue'
import SearchFilterBar from '~/components/panel/SearchFilterBar.vue'
import PixivImportModal from '~/components/panel/PixivImportModal.vue'
import InstagramImportModal from '~/components/panel/InstagramImportModal.vue'
import CanvasSaveModal from '~/components/panel/CanvasSaveModal.vue'
import CanvasControls from '~/components/ui/CanvasControls.vue'
import AssetFileBrowser from '~/components/browser/AssetFileBrowser.vue'
import QuickLookModal from '~/components/browser/QuickLookModal.vue'
import { useAuthStore } from '~/stores/authStore'
import { useToast } from '~/composables/useToast'
import { useSeo } from '~/composables/useSeo'
import { useRequireAuth } from '~/composables/useRequireAuth'

const route = useRoute()
const boardStore = useBoardStore()
const mobileNav = useMobileNav()
const auth = useAuthStore()
const toast = useToast()

const boardId = computed(() => route.params.id as string)

// ボードは個人の作業スペースなので検索インデックスには載せない（タイトルだけタブに反映）
useSeo(computed(() => {
  const name = boardStore.currentBoard?.title?.trim()
  return {
    title: name ? `${name} | Canvas | RefLens.io` : 'Canvas | RefLens.io',
    description: 'ボードに配置した参照資料を無限キャンバスで閲覧できます。',
    path: `/board/${boardId.value}`,
    noindex: true,
  }
}))

const canvasRef = ref<any>(null)
const isInsightOpen = ref(false)
const isSearchModalOpen = ref(false)
const isPixivModalOpen = ref(false)
const isInstagramModalOpen = ref(false)
const isSaveModalOpen = ref(false)
const editableTitle = ref('')
const boardReady = ref(false)
const loadError = ref(false)

/** ログイン専用アクションのガード（通知とダイアログ起動は共通 composable） */
const requireAuth = useRequireAuth()

function handleOpenSaveModal() {
  if (!requireAuth('キャンバスの一括フォルダ保存')) return
  isSaveModalOpen.value = true
}

async function init() {
  const requestedId = boardId.value
  boardReady.value = false
  loadError.value = false
  const [board] = await Promise.all([
    boardStore.loadBoard(requestedId),
    !boardStore.hasLoadedBookmarks ? boardStore.fetchBookmarks() : Promise.resolve(),
    !boardStore.folders.length ? boardStore.fetchFolders() : Promise.resolve(),
  ])
  if (boardId.value !== requestedId) return
  boardReady.value = !!board && board.id === requestedId
  loadError.value = !boardReady.value
  if (board) editableTitle.value = board.title
}

function handleOpenInsight(item?: CanvasItem | null) {
  if (item) boardStore.selectItem(item.id)
  if (typeof window !== 'undefined' && window.matchMedia('(max-width: 767px)').matches) {
    boardStore.isBrowserOpen = false
    mobileNav.close()
  }
  isInsightOpen.value = true
}

function toggleBookmarkBrowser() {
  boardStore.toggleBrowser()
  if (boardStore.isBrowserOpen) {
    mobileNav.close()
    if (typeof window !== 'undefined' && window.matchMedia('(max-width: 767px)').matches) {
      isInsightOpen.value = false
    }
  }
}

function handleTagFilter(tag: string) {
  boardStore.searchQuery = boardStore.searchQuery === tag ? '' : tag
}

function saveTitle() {
  const title = editableTitle.value.trim()
  if (title && title !== boardStore.currentBoard?.title) {
    boardStore.updateBoardTitle(title)
  }
}

function handleFitView() {
  canvasRef.value?.fitView()
}

const { dialogRef: searchDialogRef } = useDialogA11y(isSearchModalOpen, () => { isSearchModalOpen.value = false })

onBeforeRouteLeave(async () => {
  // 自動保存の待ち時間中にページ移動しても編集を失わない。
  return await canvasRef.value?.flushAutoSave() !== false
})

onBeforeRouteUpdate(async () => await canvasRef.value?.flushAutoSave() !== false)
watch(boardId, init)
onMounted(init)
</script>

<template>
  <div class="relative w-full h-app-screen overflow-hidden bg-canvas-bg text-ink flex flex-col select-none antialiased">
    <!-- サイト全体で統一された共通ヘッダー（Manager / View / Canvas で完全共通） -->
    <AppHeader class="shrink-0" />

    <!-- ワークスペース -->
    <main id="main-content" tabindex="-1" class="relative flex-1 w-full h-full min-h-0 overflow-hidden flex focus:outline-none">
      <!-- モバイル用ドロワー背景オーバーレイ -->
      <div
        v-if="boardStore.isBrowserOpen || isInsightOpen"
        class="md:hidden fixed inset-0 top-14 bg-canvas-bg/60 z-30"
        @click="boardStore.isBrowserOpen = false; isInsightOpen = false"
      />

      <!-- ブックマークブラウザ -->
      <AssetFileBrowser v-if="boardStore.isBrowserOpen" :board-id="boardId" :insight-open="isInsightOpen" />

      <div data-canvas-pane class="relative flex-1 min-w-0 h-full overflow-hidden" style="container-type: inline-size; container-name: canvas-pane">
        <InfiniteCanvas
          v-if="boardReady"
          ref="canvasRef"
          :board-id="boardId"
          @open-insight="handleOpenInsight"
          @open-pixiv="isPixivModalOpen = true"
        />

        <div v-if="!boardReady" class="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6 text-center" role="status" aria-live="polite">
          <Loader2 v-if="!loadError" class="w-6 h-6 text-brand animate-spin" aria-hidden="true" />
          <p class="text-sm font-semibold">{{ loadError ? 'キャンバスを読み込めませんでした' : 'キャンバスを読み込んでいます…' }}</p>
          <p v-if="loadError" class="text-xs text-ink-muted">接続と、このボードへのアクセス権を確認してください。</p>
          <button v-if="loadError" type="button" class="inline-flex items-center gap-2 rounded-xl bg-brand px-4 py-2.5 text-xs font-bold text-brand-fg hover:bg-brand-hover" @click="init">
            <RefreshCw class="w-3.5 h-3.5" aria-hidden="true" />再試行
          </button>
          <NuxtLink v-if="loadError" to="/" class="text-xs text-brand underline underline-offset-4">資料ライブラリに戻る</NuxtLink>
        </div>
        <div v-if="boardReady && auth.isAuthenticated" class="absolute bottom-32 right-3 z-20 floating-bar rounded-xl px-2.5 py-1.5 text-[11px] text-ink-muted flex items-center gap-1.5" role="status" aria-live="polite" aria-atomic="true">
          <Loader2 v-if="boardStore.isSaving" class="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
          <Check v-else-if="!boardStore.hasUnsavedChanges" class="w-3.5 h-3.5 text-ok" aria-hidden="true" />
          <span>{{ boardStore.isSaving ? '保存中…' : boardStore.hasUnsavedChanges ? '未保存の変更' : '保存済み' }}</span>
          <button v-if="boardStore.hasUnsavedChanges && !boardStore.isSaving" type="button" class="text-brand font-semibold underline underline-offset-2" @click="canvasRef?.flushAutoSave()">保存</button>
        </div>

        <!-- キャンバス左上: ブックマーク開閉 + ボード情報・キャンバス内検索バー -->
        <div v-if="boardReady" class="absolute top-3 left-3 z-20 flex items-center gap-1.5 pointer-events-none max-w-[calc(100%-12rem)] whitespace-nowrap">
          <!-- ブックマークブラウザが閉じているとき、左上からも1クリックで開けるボタン -->
          <button
            v-if="!boardStore.isBrowserOpen"
            type="button"
            class="pointer-events-auto floating-bar px-3 py-1.5 rounded-xl flex items-center gap-1.5 text-xs font-bold text-ink hover:text-brand transition-colors shrink-0 shadow-sm whitespace-nowrap"
            title="ブックマークブラウザを開く [B]"
            @click="toggleBookmarkBrowser"
          >
            <Bookmark class="w-3.5 h-3.5 text-brand shrink-0" />
            <span>ブックマーク</span>
            <span class="px-1.5 py-0.2 rounded-full bg-canvas-bg border border-canvas-border text-[10px] font-mono text-ink-muted shrink-0">
              {{ boardStore.bookmarks.length }}
            </span>
          </button>

          <!-- ボード名・キャンバス検索モーダル起動ピル -->
          <button
            type="button"
            class="pointer-events-auto floating-bar px-3 py-1.5 rounded-xl flex items-center gap-2 text-xs font-bold text-ink hover:border-brand transition-colors min-w-0 shadow-sm whitespace-nowrap"
            title="キャンバス内検索・ボード名の変更"
            @click="isSearchModalOpen = true"
          >
            <Search class="w-3.5 h-3.5 text-brand shrink-0" />
            <span class="truncate max-w-[110px] sm:max-w-[180px]">
              {{ boardStore.searchQuery
                ? `検索: ${boardStore.searchQuery}`
                : (boardStore.currentBoard?.title || 'My Reference Board') }}
            </span>
            <span class="hidden sm:inline-block px-1.5 py-0.2 rounded-full bg-canvas-bg border border-canvas-border text-[10px] font-mono text-ink-muted shrink-0">
              {{ boardStore.items.length }}枚
            </span>
            <Edit2 class="hidden sm:block w-3 h-3 text-ink-subtle shrink-0" />
          </button>

          <!-- 検索フィルタ解除ボタン -->
          <button
            v-if="boardStore.searchQuery"
            type="button"
            class="pointer-events-auto floating-bar px-2.5 py-1.5 rounded-xl text-[11px] font-bold text-danger flex items-center gap-1 shrink-0 whitespace-nowrap"
            title="検索絞り込みを解除"
            @click="boardStore.searchQuery = ''"
          >
            <X class="w-3.5 h-3.5 shrink-0" />
            <span class="hidden sm:inline">解除</span>
          </button>

          <!-- デモ表示バッジ (未ログイン時) -->
          <div
            v-if="!auth.isAuthenticated"
            class="pointer-events-auto floating-bar px-2.5 py-1.5 rounded-xl flex items-center gap-1.5 text-[11px] font-mono font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30 shrink-0 shadow-sm"
          >
            <span>DEMO MODE</span>
          </div>
        </div>

        <!-- 下部メインドック（w-max を指定してボタン文字の縦折り返しを完全防止） -->
        <div v-if="boardReady" class="absolute bottom-3 sm:bottom-6 left-1/2 -translate-x-1/2 w-max max-w-[calc(100%-1rem)] sm:max-w-[calc(100%-2rem)] z-20 pointer-events-auto pb-safe">
          <CanvasControls
            :board-id="boardId"
            @fit-view="handleFitView"
            @reset-view="canvasRef?.resetView()"
            @open-pixiv="isPixivModalOpen = true"
            @open-instagram="isInstagramModalOpen = true"
            @open-insight="handleOpenInsight(boardStore.activeItem)"
            @open-save-modal="handleOpenSaveModal"
          />
        </div>
      </div>

      <!-- キャンバス内検索・タグ絞り込み・ボード名変更モーダル -->
      <Teleport to="body">
        <div
          v-if="isSearchModalOpen"
          class="fixed inset-0 z-[75] flex items-end sm:items-center justify-center p-2 sm:p-4 scrim animate-fade-in"
          @click.self="isSearchModalOpen = false"
        >
          <div
            class="w-full max-w-md rounded-2xl border border-canvas-border bg-canvas-panel shadow-pop overflow-hidden animate-scale-in"
            ref="searchDialogRef" role="dialog"
            aria-modal="true"
            aria-label="キャンバス検索・ボード設定"
          >
            <div class="px-4 py-3 border-b border-canvas-border flex items-center justify-between">
              <h2 class="text-sm font-bold text-ink flex items-center gap-2">
                <Search class="w-4 h-4 text-brand" />
                <span>キャンバス内検索・ボード設定</span>
              </h2>
              <button
                type="button"
                class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
                aria-label="閉じる"
                @click="isSearchModalOpen = false"
              >
                <X class="w-4 h-4" />
              </button>
            </div>

            <div class="p-4 space-y-4 max-h-[82dvh] overflow-y-auto">
              <!-- キャンバス内検索・タグフィルター -->
              <div class="space-y-2">
                <p class="text-xs font-bold text-ink">キャンバス上の資料を絞り込み</p>
                <SearchFilterBar />
              </div>

              <!-- ボードタイトル変更 -->
              <div class="pt-3 border-t border-canvas-border space-y-2">
                <p class="text-xs font-bold text-ink">ボード名の変更</p>
                <form
                  class="flex items-center gap-2"
                  @submit.prevent="saveTitle(); isSearchModalOpen = false"
                >
                  <input
                    v-model="editableTitle"
                    type="text"
                    placeholder="ボード名を入力..."
                    class="flex-1 bg-canvas-bg border border-canvas-border-strong rounded-xl px-3 py-2 text-xs font-medium text-ink focus:outline-none focus:border-brand"
                    aria-label="ボード名"
                  >
                  <button
                    type="submit"
                    class="px-3.5 py-2 rounded-xl bg-brand text-brand-fg hover:bg-brand-hover text-xs font-bold transition-colors shrink-0 whitespace-nowrap"
                  >
                    保存
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      </Teleport>

      <AIInsightDrawer
        :item="boardStore.activeItem"
        :is-open="isInsightOpen"
        @close="isInsightOpen = false"
        @select-tag="handleTagFilter"
      />

      <PixivImportModal
        :is-open="isPixivModalOpen"
        :board-id="boardId"
        @close="isPixivModalOpen = false"
        @imported="handleFitView"
      />

      <InstagramImportModal
        :is-open="isInstagramModalOpen"
        :board-id="boardId"
        @close="isInstagramModalOpen = false"
        @imported="handleFitView"
      />

      <CanvasSaveModal
        :is-open="isSaveModalOpen"
        :board-id="boardId"
        @close="isSaveModalOpen = false"
      />

      <QuickLookModal />
    </main>
  </div>
</template>
