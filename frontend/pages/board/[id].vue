<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ChevronLeft, Sparkles, FolderOpen, Edit2, Layers, Compass, Keyboard } from 'lucide-vue-next'
import type { CanvasItem } from '~/types'
import { useBoardStore } from '~/stores/boardStore'
import { useHelpStore } from '~/stores/helpStore'
import InfiniteCanvas from '~/components/canvas/InfiniteCanvas.vue'
import AIInsightDrawer from '~/components/panel/AIInsightDrawer.vue'
import SearchFilterBar from '~/components/panel/SearchFilterBar.vue'
import PixivImportModal from '~/components/panel/PixivImportModal.vue'
import InstagramImportModal from '~/components/panel/InstagramImportModal.vue'
import CanvasControls from '~/components/ui/CanvasControls.vue'
import AssetFileBrowser from '~/components/browser/AssetFileBrowser.vue'
import QuickLookModal from '~/components/browser/QuickLookModal.vue'
import ThemeToggle from '~/components/ui/ThemeToggle.vue'
import AuthButton from '~/components/ui/AuthButton.vue'
import SiteInfoMenu from '~/components/ui/SiteInfoMenu.vue'

const route = useRoute()
const boardStore = useBoardStore()
const helpStore = useHelpStore()

const boardId = computed(() => route.params.id as string)

const canvasRef = ref<any>(null)
const isInsightOpen = ref(false)
const isPixivModalOpen = ref(false)
const isInstagramModalOpen = ref(false)
const isEditingTitle = ref(false)
const editableTitle = ref('')

async function init() {
  await boardStore.loadBoard(boardId.value)
  if (boardStore.currentBoard) {
    editableTitle.value = boardStore.currentBoard.title
  }
}

function handleOpenInsight(item?: CanvasItem | null) {
  if (item) boardStore.selectItem(item.id)
  isInsightOpen.value = true
}

function handleTagFilter(tag: string) {
  boardStore.searchQuery = boardStore.searchQuery === tag ? '' : tag
}

function saveTitle() {
  isEditingTitle.value = false
  const title = editableTitle.value.trim()
  if (title && title !== boardStore.currentBoard?.title) {
    boardStore.updateBoardTitle(title)
  }
}

function handleFitView() {
  canvasRef.value?.fitView()
}

onMounted(init)
</script>

<template>
  <div class="relative w-screen h-screen overflow-hidden bg-canvas-bg text-ink flex flex-col select-none">
    <!-- ヘッダー -->
    <header class="h-14 border-b border-canvas-border bg-canvas-panel px-3 flex items-center justify-between gap-3 z-30 shrink-0">
      <!-- 左 -->
      <div class="flex items-center gap-2 min-w-0">
        <NuxtLink
          to="/"
          class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors shrink-0"
          title="Manager に戻る"
          aria-label="Manager に戻る"
        >
          <ChevronLeft class="w-4 h-4" />
        </NuxtLink>

        <!-- タイトル編集 -->
        <div class="flex items-center gap-2 min-w-0">
          <input
            v-if="isEditingTitle"
            v-model="editableTitle"
            type="text"
            class="bg-canvas-card border border-brand rounded-lg px-2 py-1 text-xs font-bold text-ink focus:outline-none w-40"
            @blur="saveTitle"
            @keydown.enter="saveTitle"
            @keydown.esc="isEditingTitle = false"
            autofocus
          >
          <button
            v-else
            type="button"
            class="flex items-center gap-1.5 px-1.5 py-1 rounded-lg text-xs font-bold text-ink hover:bg-canvas-hover transition-colors min-w-0 group"
            title="クリックでタイトルを編集"
            @click="isEditingTitle = true"
          >
            <span class="truncate">{{ boardStore.currentBoard?.title || '読み込み中...' }}</span>
            <Edit2 class="w-3 h-3 text-ink-subtle opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
          </button>
        </div>

        <span class="hidden sm:inline text-[11px] font-mono text-ink-subtle bg-canvas-card px-2 py-0.5 rounded-full border border-canvas-border shrink-0">
          {{ boardStore.items.length }} items
        </span>
      </div>

      <!-- 中央: ナビ + 検索（flex-1 + min-w-0 で左右の余白を吸収させる） -->
      <div class="flex-1 flex items-center justify-center gap-2 min-w-0">
        <nav class="hidden lg:flex items-center gap-0.5 p-0.5 rounded-lg border border-canvas-border bg-canvas-card shrink-0">
          <NuxtLink
            to="/"
            class="px-2.5 py-1 rounded-md text-[11px] font-semibold text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          >
            Manager
          </NuxtLink>
          <NuxtLink
            to="/view"
            class="px-2.5 py-1 rounded-md text-[11px] font-semibold text-ink-muted hover:text-pixiv hover:bg-canvas-hover transition-colors flex items-center gap-1"
          >
            <Compass class="w-3 h-3" />
            pixiv
          </NuxtLink>
          <span class="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-brand text-brand-fg flex items-center gap-1">
            <Layers class="w-3 h-3" />
            Canvas
          </span>
        </nav>

        <div class="hidden xl:block min-w-0">
          <SearchFilterBar />
        </div>
      </div>

      <!-- 右 -->
      <div class="flex items-center gap-1.5 shrink-0">
        <!-- 検索（狭い画面用） -->
        <div class="xl:hidden">
          <button
            type="button"
            class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
            title="検索"
            aria-label="検索"
            @click="boardStore.toggleBrowser()"
          >
            <FolderOpen class="w-4 h-4" />
          </button>
        </div>

        <button
          type="button"
          class="p-1.5 rounded-lg transition-colors relative"
          :class="isInsightOpen ? 'bg-brand-soft text-brand' : 'text-ink-muted hover:text-ink hover:bg-canvas-hover'"
          title="AI 解析パネル [I]"
          aria-label="AI 解析パネル"
          @click="isInsightOpen = !isInsightOpen"
        >
          <Sparkles class="w-4 h-4" />
          <span
            v-if="boardStore.activeItem?.ai_analysis"
            class="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-ok"
          />
        </button>

        <button
          type="button"
          class="hidden md:block p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          title="ショートカット一覧 (?)"
          aria-label="ショートカット一覧"
          @click="helpStore.toggle()"
        >
          <Keyboard class="w-4 h-4" />
        </button>

        <AuthButton />
        <ThemeToggle />
        <SiteInfoMenu />
      </div>
    </header>

    <!-- モバイル検索 -->
    <div v-if="boardStore.isBrowserOpen" class="xl:hidden border-b border-canvas-border bg-canvas-panel px-3 py-2">
      <SearchFilterBar />
    </div>

    <!-- ワークスペース -->
    <main class="relative flex-1 w-full h-full overflow-hidden flex">
      <AssetFileBrowser v-if="boardStore.isBrowserOpen" :board-id="boardId" :insight-open="isInsightOpen" />

      <div data-canvas-pane class="relative flex-1 min-w-0 h-full overflow-hidden" style="container-type: inline-size; container-name: canvas-pane">
        <InfiniteCanvas ref="canvasRef" :board-id="boardId" @open-insight="handleOpenInsight" />

        <!-- 下部ツールバー -->
        <div class="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 pointer-events-auto max-w-[calc(100%-2rem)] overflow-x-auto no-scrollbar">
          <CanvasControls
            :board-id="boardId"
            @fit-view="handleFitView"
            @reset-view="canvasRef?.resetView()"
            @open-pixiv="isPixivModalOpen = true"
            @open-instagram="isInstagramModalOpen = true"
            @open-insight="isInsightOpen = !isInsightOpen"
          />
        </div>
      </div>

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

      <QuickLookModal />
    </main>
  </div>
</template>
