<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import {
  Bookmark,
  Upload,
  Instagram,
  LayoutGrid,
  Maximize2,
  RotateCcw,
  Palette,
  Sparkles,
  Check,
  Compass,
  SlidersHorizontal,
  Undo2,
  Redo2,
  Plus,
  Globe,
  Folder,
  X,
} from 'lucide-vue-next'
import { useBoardStore } from '~/stores/boardStore'
import { useToast } from '~/composables/useToast'
import { useVisualSearch } from '~/composables/useVisualSearch'

defineProps<{ boardId: string }>()

const emit = defineEmits<{
  (e: 'fit-view'): void
  (e: 'reset-view'): void
  (e: 'open-instagram'): void
  (e: 'open-pixiv'): void
  (e: 'open-insight'): void
  (e: 'open-save-modal'): void
}>()

const boardStore = useBoardStore()
const toast = useToast()
const { startCircleSearch } = useVisualSearch()
const fileInputRef = ref<HTMLInputElement | null>(null)
const openMenu = ref(false)
const isAddModalOpen = ref(false)
const directUrl = ref('')

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    openMenu.value = false
    isAddModalOpen.value = false
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})

const ARRANGE_OPTIONS = [
  { id: 'grid', label: 'グリッド整列', hint: '等間隔のグリッドに並べる' },
  { id: 'horizontal', label: '水平整列', hint: '1行に横並びで並べる' },
  { id: 'vertical', label: '垂直整列', hint: '1列に縦並びで並べる' },
] as const

const THEME_OPTIONS = [
  { id: 'dark-grid', label: 'グリッド線', hint: '等間隔の方眼' },
  { id: 'dark-dots', label: 'ドット', hint: '点状の座標インジケータ' },
  { id: 'dark-plain', label: 'プレーン', hint: '余白のみ' },
] as const

async function handleFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files?.length) {
    isAddModalOpen.value = false
    const coords = boardStore.getNextPlacementCoords()
    await boardStore.uploadImages(Array.from(target.files), coords.x, coords.y)
    target.value = ''
  }
}

async function handleDirectUrlAdd() {
  const url = directUrl.value.trim()
  if (!url) return
  const coords = boardStore.getNextPlacementCoords()
  const res = await boardStore.addBookmark(url, undefined, true, coords.x, coords.y)
  if (res) {
    directUrl.value = ''
    isAddModalOpen.value = false
    toast.success('キャンバスへ追加しました', url)
  }
}

async function arrange(type: 'grid' | 'horizontal' | 'vertical') {
  openMenu.value = false
  await boardStore.arrange(type)
  emit('fit-view')
}

function setTheme(theme: string) {
  openMenu.value = false
  if (boardStore.currentBoard) {
    boardStore.currentBoard.background_theme = theme as any
  }
}
</script>

<template>
  <div class="w-max max-w-full overflow-x-auto no-scrollbar flex items-center gap-1 sm:gap-1.5 floating-bar px-2 sm:px-2.5 py-1.5 rounded-2xl select-none shadow-pop whitespace-nowrap">
    <input
      ref="fileInputRef"
      type="file"
      accept="image/*"
      multiple
      class="hidden"
      @change="handleFileChange"
    >

    <!-- 1. ブックマークブラウザ開閉 -->
    <button
      type="button"
      class="shrink-0 whitespace-nowrap flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-xl text-xs font-bold transition-colors border"
      :class="boardStore.isBrowserOpen
        ? 'bg-brand text-brand-fg border-brand shadow-sm'
        : 'text-ink hover:text-brand border-canvas-border-strong bg-canvas-bg hover:bg-canvas-hover'"
      title="ブックマークブラウザを開閉 [B]"
      aria-label="ブックマークブラウザを開閉"
      :aria-pressed="boardStore.isBrowserOpen"
      @click="boardStore.toggleBrowser()"
    >
      <Bookmark class="w-3.5 h-3.5 shrink-0" />
      <span class="whitespace-nowrap">ブックマーク</span>
      <span
        class="hidden sm:inline-block px-1.5 py-0.2 rounded-full text-[10px] font-mono shrink-0"
        :class="boardStore.isBrowserOpen ? 'bg-white/20 text-white' : 'bg-canvas-card text-ink-muted'"
      >
        {{ boardStore.bookmarks.length }}
      </span>
    </button>

    <!-- 一括フォルダ保存 -->
    <button
      type="button"
      class="shrink-0 whitespace-nowrap flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-xl text-xs font-semibold text-ink hover:text-brand border border-canvas-border-strong bg-canvas-bg hover:bg-canvas-hover transition-colors"
      title="キャンバス上の資料を一括でフォルダに保存"
      @click="emit('open-save-modal')"
    >
      <Folder class="w-3.5 h-3.5 text-brand shrink-0" />
      <span class="whitespace-nowrap">一括セーブ</span>
    </button>

    <!-- 2. 資料を追加 -->
    <button
      type="button"
      class="shrink-0 whitespace-nowrap flex items-center gap-1 px-2.5 sm:px-3 py-1.5 rounded-xl text-xs font-bold bg-brand text-brand-fg hover:bg-brand-hover transition-colors"
      title="画像・URL・pixiv・Instagramから資料を追加"
      aria-label="資料を追加"
      @click="isAddModalOpen = true"
    >
      <Plus class="w-3.5 h-3.5 shrink-0" />
      <span class="whitespace-nowrap">追加</span>
    </button>

    <button
      type="button"
      class="hidden md:inline-flex shrink-0 p-2 rounded-xl text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
      title="端末の画像を直接アップロード"
      aria-label="端末の画像を直接アップロード"
      @click="fileInputRef?.click()"
    >
      <Upload class="w-4 h-4 shrink-0" />
    </button>

    <div class="h-4 w-px bg-canvas-border mx-0.5 shrink-0" />

    <!-- 3. Undo / Redo -->
    <button
      type="button"
      class="shrink-0 p-2 rounded-xl text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors disabled:opacity-35 disabled:pointer-events-none"
      title="元に戻す [Cmd+Z]"
      aria-label="元に戻す"
      :disabled="!boardStore.canUndo"
      @click="boardStore.undo()"
    >
      <Undo2 class="w-4 h-4 shrink-0" />
    </button>

    <button
      type="button"
      class="shrink-0 p-2 rounded-xl text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors disabled:opacity-35 disabled:pointer-events-none"
      title="やり直し [Cmd+Shift+Z]"
      aria-label="やり直し"
      :disabled="!boardStore.canRedo"
      @click="boardStore.redo()"
    >
      <Redo2 class="w-4 h-4 shrink-0" />
    </button>

    <div class="h-4 w-px bg-canvas-border mx-0.5 shrink-0" />

    <!-- 4. 全体表示 & 整列・表示設定 -->
    <button
      type="button"
      class="hidden sm:inline-flex shrink-0 p-2 rounded-xl text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
      title="全アイテムが画面に収まるようフィット [F]"
      aria-label="フィットビュー"
      @click="emit('fit-view')"
    >
      <Maximize2 class="w-4 h-4 shrink-0" />
    </button>

    <button
      type="button"
      class="shrink-0 whitespace-nowrap flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-semibold text-ink hover:bg-canvas-hover border border-canvas-border-strong bg-canvas-bg transition-colors"
      title="自動整列・表示設定"
      aria-label="自動整列・表示設定"
      :aria-expanded="openMenu"
      @click="openMenu = !openMenu"
    >
      <SlidersHorizontal class="w-3.5 h-3.5 shrink-0" />
      <span class="hidden md:inline whitespace-nowrap">整列・表示</span>
    </button>

    <!-- 5. AI 解析 -->
    <button
      type="button"
      class="shrink-0 whitespace-nowrap flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-bold text-brand bg-brand-soft hover:bg-brand hover:text-brand-fg transition-colors"
      title="AI 解析パネル [I]"
      aria-label="AI 解析パネル"
      @click="emit('open-insight')"
    >
      <Sparkles class="w-3.5 h-3.5 shrink-0" />
      <span class="hidden sm:inline whitespace-nowrap">AI解析</span>
    </button>

    <!-- 6. Galaxy AI かこって検索 -->
    <button
      type="button"
      class="shrink-0 whitespace-nowrap flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-bold text-indigo-400 bg-canvas-card hover:bg-canvas-hover border border-indigo-500/30 transition-all shadow-xs"
      title="画面上をドラッグして囲んだ部分の類似資料をAI検索"
      aria-label="Galaxy AI かこって検索"
      @click="startCircleSearch"
    >
      <Sparkles class="w-3.5 h-3.5 shrink-0 text-pink-400 animate-pulse" />
      <span class="whitespace-nowrap">かこって検索</span>
    </button>

    <!-- 保存ステータス -->
    <div class="hidden sm:flex shrink-0 items-center pl-1 pr-0.5 text-[11px] text-ink-subtle font-mono">
      <div v-if="boardStore.isSaving" class="w-3 h-3 rounded-full border-2 border-brand border-t-transparent animate-spin" />
      <Check v-else class="w-3.5 h-3.5 text-ok" title="自動保存済み" />
    </div>
  </div>

  <!-- 統合「キャンバスに資料を追加」モーダル -->
  <Teleport to="body">
    <div
      v-if="isAddModalOpen"
      class="fixed inset-0 z-[80] flex items-end sm:items-center justify-center p-2 sm:p-4 scrim animate-fade-in"
      @click.self="isAddModalOpen = false"
    >
      <div
        class="w-full max-w-md rounded-2xl border border-canvas-border bg-canvas-panel shadow-pop overflow-hidden animate-scale-in"
        role="dialog"
        aria-modal="true"
        aria-label="キャンバスに資料を追加"
      >
        <div class="px-4 py-3 border-b border-canvas-border flex items-center justify-between">
          <h2 class="text-sm font-bold text-ink flex items-center gap-2">
            <Plus class="w-4 h-4 text-brand" />
            <span>キャンバスに資料を追加</span>
          </h2>
          <button
            type="button"
            class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
            aria-label="閉じる"
            @click="isAddModalOpen = false"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <div class="p-4 space-y-3.5 max-h-[82dvh] overflow-y-auto">
          <!-- URLから直接配置 -->
          <form class="space-y-1.5" @submit.prevent="handleDirectUrlAdd">
            <label class="text-xs font-bold text-ink block">URLから直接キャンバスへ配置</label>
            <div class="flex items-center gap-2">
              <div class="relative flex-1 flex items-center">
                <Globe class="absolute left-3 w-3.5 h-3.5 text-ink-subtle pointer-events-none" />
                <input
                  v-model="directUrl"
                  type="url"
                  placeholder="pixiv / Instagram / Web 画像URL..."
                  class="w-full bg-canvas-bg border border-canvas-border-strong rounded-xl pl-8 pr-3 py-2 text-xs text-ink placeholder:text-ink-subtle focus:outline-none focus:border-brand"
                >
              </div>
              <button
                type="submit"
                class="px-3.5 py-2 rounded-xl bg-brand text-brand-fg hover:bg-brand-hover text-xs font-bold transition-colors disabled:opacity-40 shrink-0 whitespace-nowrap"
                :disabled="!directUrl.trim() || boardStore.isAddingBookmark"
              >
                {{ boardStore.isAddingBookmark ? '追加中...' : '配置' }}
              </button>
            </div>
          </form>

          <div class="border-t border-canvas-border pt-3 space-y-2">
            <p class="text-xs font-bold text-ink">追加方法を選択</p>

            <button
              type="button"
              class="w-full flex items-center gap-3 p-3 rounded-xl bg-canvas-bg hover:bg-canvas-hover border border-canvas-border-strong text-left transition-colors"
              @click="isAddModalOpen = false; boardStore.isBrowserOpen = true"
            >
              <div class="w-9 h-9 rounded-xl bg-brand-soft text-brand flex items-center justify-center shrink-0">
                <Bookmark class="w-4 h-4" />
              </div>
              <div>
                <p class="text-xs font-bold text-ink">ブックマークブラウザから配置</p>
                <p class="text-[11px] text-ink-muted">保存済みフォルダ・ブックマークから選んで配置</p>
              </div>
            </button>

            <button
              type="button"
              class="w-full flex items-center gap-3 p-3 rounded-xl bg-canvas-bg hover:bg-canvas-hover border border-canvas-border-strong text-left transition-colors"
              @click="fileInputRef?.click()"
            >
              <div class="w-9 h-9 rounded-xl bg-brand text-brand-fg flex items-center justify-center shrink-0">
                <Upload class="w-4 h-4" />
              </div>
              <div>
                <p class="text-xs font-bold text-ink">端末の画像を追加</p>
                <p class="text-[11px] text-ink-muted">ローカルの画像ファイルを直接アップロード</p>
              </div>
            </button>

            <button
              type="button"
              class="w-full flex items-center gap-3 p-3 rounded-xl bg-canvas-bg hover:bg-canvas-hover border border-canvas-border-strong text-left transition-colors"
              @click="isAddModalOpen = false; emit('open-pixiv')"
            >
              <div class="w-9 h-9 rounded-xl bg-pixiv text-white flex items-center justify-center shrink-0">
                <Compass class="w-4 h-4" />
              </div>
              <div>
                <p class="text-xs font-bold text-ink">pixivから作品を取り込む</p>
                <p class="text-[11px] text-ink-muted">キーワード検索やランキングから一括配置</p>
              </div>
            </button>

            <button
              type="button"
              class="w-full flex items-center gap-3 p-3 rounded-xl bg-canvas-bg hover:bg-canvas-hover border border-canvas-border-strong text-left transition-colors"
              @click="isAddModalOpen = false; emit('open-instagram')"
            >
              <div class="w-9 h-9 rounded-xl bg-instagram text-white flex items-center justify-center shrink-0">
                <Instagram class="w-4 h-4" />
              </div>
              <div>
                <p class="text-xs font-bold text-ink">Instagramから取り込む</p>
                <p class="text-[11px] text-ink-muted">投稿フィードから画像を選択して取り込む</p>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- キャンバス整列・ビュー・背景設定モーダル -->
  <Teleport to="body">
    <div
      v-if="openMenu"
      class="fixed inset-0 z-[80] flex items-end sm:items-center justify-center p-2 sm:p-4 scrim animate-fade-in"
      @click.self="openMenu = false"
    >
      <div
        class="w-full max-w-sm rounded-2xl border border-canvas-border bg-canvas-panel shadow-pop overflow-hidden animate-scale-in"
        role="dialog"
        aria-modal="true"
        aria-label="キャンバスの整列・表示設定"
      >
        <div class="px-4 py-3 border-b border-canvas-border flex items-center justify-between">
          <h2 class="text-sm font-bold text-ink flex items-center gap-2">
            <SlidersHorizontal class="w-4 h-4 text-brand" />
            <span>キャンバス整列・表示設定</span>
          </h2>
          <button
            type="button"
            class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
            aria-label="閉じる"
            @click="openMenu = false"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <div class="p-4 space-y-4 max-h-[82dvh] overflow-y-auto">
          <!-- ビュー操作 -->
          <div class="space-y-2">
            <p class="text-xs font-bold text-ink">視点・ズーム操作</p>
            <div class="grid grid-cols-2 gap-2">
              <button
                type="button"
                class="flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl bg-canvas-bg hover:bg-canvas-hover border border-canvas-border-strong text-xs font-semibold text-ink transition-colors whitespace-nowrap"
                @click="openMenu = false; emit('fit-view')"
              >
                <Maximize2 class="w-3.5 h-3.5 text-brand shrink-0" />
                <span>全体表示</span>
              </button>
              <button
                type="button"
                class="flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl bg-canvas-bg hover:bg-canvas-hover border border-canvas-border-strong text-xs font-semibold text-ink transition-colors whitespace-nowrap"
                @click="openMenu = false; emit('reset-view')"
              >
                <RotateCcw class="w-3.5 h-3.5 text-ink-muted shrink-0" />
                <span>100%リセット</span>
              </button>
            </div>
          </div>

          <!-- 自動整列 -->
          <div class="pt-3 border-t border-canvas-border space-y-2">
            <p class="text-xs font-bold text-ink">自動整列</p>
            <div class="space-y-1.5">
              <button
                v-for="opt in ARRANGE_OPTIONS"
                :key="opt.id"
                type="button"
                class="w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl bg-canvas-bg hover:bg-canvas-hover border border-canvas-border-strong text-xs font-medium text-ink transition-colors"
                @click="arrange(opt.id)"
              >
                <span class="flex items-center gap-2 font-semibold whitespace-nowrap">
                  <LayoutGrid class="w-3.5 h-3.5 text-brand shrink-0" />
                  {{ opt.label }}
                </span>
                <span class="text-[11px] text-ink-muted truncate">{{ opt.hint }}</span>
              </button>
            </div>
          </div>

          <!-- 背景パターン -->
          <div class="pt-3 border-t border-canvas-border space-y-2">
            <p class="text-xs font-bold text-ink">背景パターン</p>
            <div class="grid grid-cols-3 gap-1.5">
              <button
                v-for="opt in THEME_OPTIONS"
                :key="opt.id"
                type="button"
                class="flex flex-col items-center justify-center gap-1 py-2.5 px-2 rounded-xl text-xs border transition-colors whitespace-nowrap"
                :class="boardStore.currentBoard?.background_theme === opt.id
                  ? 'text-brand font-bold bg-brand-soft border-brand'
                  : 'text-ink font-medium bg-canvas-bg border-canvas-border-strong hover:bg-canvas-hover'"
                @click="setTheme(opt.id)"
              >
                <Palette class="w-4 h-4 shrink-0" />
                <span>{{ opt.label }}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
