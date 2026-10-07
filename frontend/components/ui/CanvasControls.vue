<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import {
  Folder,
  Upload,
  Instagram,
  LayoutGrid,
  Maximize2,
  RotateCcw,
  Palette,
  Sparkles,
  Check,
  Compass,
  Menu,
} from 'lucide-vue-next'
import { useBoardStore } from '~/stores/boardStore'

defineProps<{ boardId: string }>()

const emit = defineEmits<{
  (e: 'fit-view'): void
  (e: 'reset-view'): void
  (e: 'open-instagram'): void
  (e: 'open-pixiv'): void
  (e: 'open-insight'): void
}>()

const boardStore = useBoardStore()
const fileInputRef = ref<HTMLInputElement | null>(null)
const openMenu = ref(false)
const menuButtonRef = ref<HTMLElement | null>(null)
const menuPanelRef = ref<HTMLElement | null>(null)
const menuStyle = ref({ left: '0px', top: '0px', width: '208px' })
let paneObserver: ResizeObserver | null = null

function updateMenuPosition() {
  const button = menuButtonRef.value
  const pane = button?.closest('[data-canvas-pane]') as HTMLElement | null
  if (!button || !pane) return

  const trigger = button.getBoundingClientRect()
  const bounds = pane.getBoundingClientRect()
  const width = Math.min(208, Math.max(160, bounds.width - 16))
  const menuHeight = menuPanelRef.value?.offsetHeight || 286
  const left = Math.max(bounds.left + 8, Math.min(trigger.right - width, bounds.right - width - 8))
  const top = Math.max(bounds.top + 8, trigger.top - menuHeight - 8)
  menuStyle.value = { left: `${left}px`, top: `${top}px`, width: `${width}px` }
}

async function toggleMenu() {
  openMenu.value = !openMenu.value
  if (openMenu.value) {
    await nextTick()
    updateMenuPosition()
  }
}

function onOutsidePointer(event: PointerEvent) {
  const target = event.target as Node
  if (!menuPanelRef.value?.contains(target) && !menuButtonRef.value?.contains(target)) openMenu.value = false
}

function onMenuKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') openMenu.value = false
}

watch(openMenu, value => {
  if (value) {
    document.addEventListener('pointerdown', onOutsidePointer)
    document.addEventListener('keydown', onMenuKeydown)
    window.addEventListener('resize', updateMenuPosition)
    paneObserver = new ResizeObserver(updateMenuPosition)
    const pane = menuButtonRef.value?.closest('[data-canvas-pane]')
    if (pane) paneObserver.observe(pane)
  } else {
    document.removeEventListener('pointerdown', onOutsidePointer)
    document.removeEventListener('keydown', onMenuKeydown)
    window.removeEventListener('resize', updateMenuPosition)
    paneObserver?.disconnect()
    paneObserver = null
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onOutsidePointer)
  document.removeEventListener('keydown', onMenuKeydown)
  window.removeEventListener('resize', updateMenuPosition)
  paneObserver?.disconnect()
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
    await boardStore.uploadImages(Array.from(target.files), 100, 100)
    target.value = ''
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
  <div class="relative flex items-center gap-1 floating-bar px-2 py-1.5 rounded-2xl select-none">
    <input
      ref="fileInputRef"
      type="file"
      accept="image/*"
      multiple
      class="hidden"
      @change="handleFileChange"
    >

    <!-- 主要アクション（常に表示） -->
    <button
      type="button"
      class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-colors border"
      :class="boardStore.isBrowserOpen
        ? 'bg-brand text-brand-fg border-brand'
        : 'text-ink-muted hover:text-ink border-canvas-border hover:bg-canvas-hover'"
      title="資料ライブラリ [B]"
      aria-label="資料ライブラリの開閉"
      :aria-pressed="boardStore.isBrowserOpen"
      @click="boardStore.toggleBrowser()"
    >
      <Folder class="w-3.5 h-3.5" />
      <span class="control-label hidden sm:inline">Library</span>
    </button>

    <button
      type="button"
      class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-brand text-brand-fg hover:bg-brand-hover transition-colors"
      title="画像を追加"
      @click="fileInputRef?.click()"
    >
      <Upload class="w-3.5 h-3.5" />
      <span class="control-label hidden md:inline">Add Image</span>
    </button>

    <!-- pixiv / Instagram 取り込み -->
    <button
      type="button"
      class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-pixiv text-white hover:bg-pixiv-hover transition-colors"
      title="pixivから作品を取り込む"
      @click="emit('open-pixiv')"
    >
      <Compass class="w-3.5 h-3.5" />
      <span class="control-label hidden lg:inline">pixiv</span>
    </button>

    <button
      type="button"
      class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-instagram text-white hover:bg-instagram-hover transition-colors"
      title="Instagramから取り込む"
      @click="emit('open-instagram')"
    >
      <Instagram class="w-3.5 h-3.5" />
      <span class="control-label hidden lg:inline">Instagram</span>
    </button>

    <div class="h-4 w-px bg-canvas-border mx-0.5" />

    <button
      type="button"
      class="p-2 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
      title="全アイテムが画面に収まるようフィット [F]"
      aria-label="フィットビュー"
      @click="emit('fit-view')"
    >
      <Maximize2 class="w-4 h-4" />
    </button>

    <button
      type="button"
      class="p-2 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
      title="ズームを100%に戻す [Cmd+0]"
      aria-label="ビューを100%にリセット"
      @click="emit('reset-view')"
    >
      <RotateCcw class="w-4 h-4" />
    </button>

    <!-- AI インサイト + 保存状態 -->
    <button
      type="button"
      class="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-brand hover:bg-brand-soft transition-colors border border-transparent"
      title="AI 解析パネル [I]"
      @click="emit('open-insight')"
    >
      <Sparkles class="w-3.5 h-3.5" />
      <span class="control-label hidden lg:inline">AI Inspect</span>
    </button>

    <div class="flex items-center gap-1 pl-1 pr-1 text-[11px] text-ink-subtle font-mono">
      <template v-if="boardStore.isSaving">
        <div class="w-2.5 h-2.5 rounded-full border-2 border-brand border-t-transparent animate-spin" />
        <span class="control-label hidden lg:inline">保存中</span>
      </template>
      <template v-else>
        <Check class="w-3 h-3 text-ok" />
        <span class="control-label hidden lg:inline">保存済</span>
      </template>
    </div>

    <!-- その他の操作（自動整列・背景パターン） -->
    <div class="relative">
      <button
        ref="menuButtonRef"
        type="button"
        class="p-2 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
        title="その他の操作"
        aria-label="その他の操作"
        :aria-expanded="openMenu"
        @click="toggleMenu"
      >
        <Menu class="w-4 h-4" />
      </button>

    </div>
  </div>

  <Teleport to="body">
    <div
      v-if="openMenu"
      ref="menuPanelRef"
      class="fixed z-[80] p-1 rounded-xl border border-canvas-border bg-canvas-raised shadow-pop animate-scale-in"
      :style="menuStyle"
      role="menu"
      aria-label="Canvasのその他の操作"
    >
        <p class="px-2.5 py-1.5 text-[10px] font-mono uppercase tracking-wider text-ink-subtle">
          自動整列
        </p>
        <button
          v-for="opt in ARRANGE_OPTIONS"
          :key="opt.id"
          type="button"
          class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          @click="arrange(opt.id)"
        >
          <LayoutGrid class="w-3.5 h-3.5 shrink-0" />
          <span class="flex-1 text-left">{{ opt.label }}</span>
        </button>

        <p class="px-2.5 pt-2 pb-1.5 mt-1 border-t border-canvas-border text-[10px] font-mono uppercase tracking-wider text-ink-subtle">
          背景パターン
        </p>
        <button
          v-for="opt in THEME_OPTIONS"
          :key="opt.id"
          type="button"
          class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs transition-colors"
          :class="boardStore.currentBoard?.background_theme === opt.id
            ? 'text-brand font-semibold bg-brand-soft'
            : 'text-ink-muted hover:text-ink hover:bg-canvas-hover'"
          @click="setTheme(opt.id)"
        >
          <Palette class="w-3.5 h-3.5 shrink-0" />
          <span class="flex-1 text-left">{{ opt.label }}</span>
          <Check
            v-if="boardStore.currentBoard?.background_theme === opt.id"
            class="w-3.5 h-3.5"
          />
        </button>
    </div>
  </Teleport>
</template>

<style scoped>
@container canvas-pane (max-width: 720px) {
  .control-label {
    display: none;
  }
}
</style>
