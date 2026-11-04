<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  FlipHorizontal,
  FlipVertical,
  SunMoon,
  RotateCw,
  Lock,
  Unlock,
  Trash2,
  ChevronUp,
  ChevronDown,
  Sparkles,
  ExternalLink,
  Copy,
  Maximize2,
  Pencil,
} from 'lucide-vue-next'
import type { CanvasItem } from '~/types'
import { useBoardStore } from '~/stores/boardStore'
import { useToast } from '~/composables/useToast'

const props = defineProps<{
  item: CanvasItem | null
  /** クリックされたビューポート座標 */
  x: number
  y: number
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'open-insight'): void
  (e: 'focus-item', item: CanvasItem): void
  (e: 'changed'): void
}>()

const boardStore = useBoardStore()
const toast = useToast()

const menuRef = ref<HTMLElement | null>(null)
const position = ref({ left: 0, top: 0 })
const draftCaption = ref('')
const isEditingCaption = ref(false)

const OPACITY_PRESETS = [0.25, 0.5, 0.75, 1] as const

const item = computed(() => props.item)

function saveCaption() {
  if (!item.value) return
  const next = draftCaption.value.trim()
  if (next !== (item.value.caption || '')) {
    boardStore.updateItem(item.value.id, { caption: next || undefined })
    emit('changed')
    toast.success(next ? 'メモを保存しました' : 'メモをクリアしました')
  }
  isEditingCaption.value = false
}

function setOpacity(opacity: number) {
  if (!item.value) return
  boardStore.updateItem(item.value.id, { opacity })
  emit('changed')
}

/** 画面端で切れないように位置を補正する */
async function clampPosition() {
  const el = menuRef.value
  if (!el) return

  const { offsetWidth: w, offsetHeight: h } = el
  const margin = 8
  position.value = {
    left: Math.max(margin, Math.min(props.x, window.innerWidth - w - margin)),
    top: Math.max(margin, Math.min(props.y, window.innerHeight - h - margin)),
  }
}

function run(action: () => void | Promise<void>) {
  action()
  emit('close')
}

async function copySourceUrl() {
  const url = item.value?.media?.source_url
  if (!url) {
    toast.warning('リンクがありません')
    return
  }
  try {
    await navigator.clipboard.writeText(url)
    toast.success('リンクをコピーしました')
  } catch {
    toast.error('クリップボードにコピーできませんでした')
  }
}

function onKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

watch(
  () => [props.item, props.x, props.y],
  async () => {
    if (!props.item) {
      isEditingCaption.value = false
      return
    }
    draftCaption.value = props.item.caption || ''
    isEditingCaption.value = false
    position.value = { left: props.x, top: props.y }
    await nextTick()
    clampPosition()
  },
  { immediate: true }
)

onMounted(() => {
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('resize', clampPosition)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('resize', clampPosition)
})
</script>

<template>
  <Teleport to="body">
    <div v-if="item" class="fixed inset-0 z-[75]" @pointerdown="emit('close')" @contextmenu.prevent="emit('close')">
      <div
        ref="menuRef"
        class="absolute min-w-[220px] max-w-[calc(100vw-16px)] max-h-[calc(100dvh-16px)] overflow-y-auto p-1 rounded-xl border border-canvas-border bg-canvas-raised shadow-pop animate-scale-in"
        :style="{ left: `${position.left}px`, top: `${position.top}px` }"
        role="menu"
        aria-label="キャンバス資料の操作メニュー"
        @pointerdown.stop
      >
        <!-- タイトル / キャプション（メモ）編集 -->
        <div class="px-2.5 py-1.5 border-b border-canvas-border mb-1 space-y-1.5">
          <div v-if="!isEditingCaption" class="flex items-center justify-between gap-2">
            <p class="text-[11px] font-semibold text-ink truncate" :title="item.caption || item.media?.original_file_name">
              {{ item.caption || item.media?.original_file_name || 'Reference' }}
            </p>
            <button
              type="button"
              class="p-1 rounded text-ink-subtle hover:text-brand hover:bg-canvas-hover transition-colors shrink-0"
              title="メモ（キャプション）を編集"
              aria-label="メモを編集"
              @click="isEditingCaption = true"
            >
              <Pencil class="w-3 h-3" />
            </button>
          </div>
          <form v-else class="space-y-1" @submit.prevent="saveCaption">
            <input
              v-model="draftCaption"
              type="text"
              placeholder="メモ・キャプションを入力..."
              aria-label="資料のメモ・キャプション"
              class="w-full bg-canvas-card border border-brand rounded-md px-2 py-1 text-[11px] text-ink focus:outline-none"
              autofocus
              @keydown.esc.stop.prevent="isEditingCaption = false"
            >
            <div class="flex justify-end gap-1">
              <button
                type="button"
                class="px-1.5 py-0.5 text-[10px] text-ink-muted hover:text-ink"
                @click="isEditingCaption = false"
              >
                キャンセル
              </button>
              <button
                type="submit"
                class="px-2 py-0.5 rounded bg-brand text-brand-fg text-[10px] font-semibold"
              >
                保存
              </button>
            </div>
          </form>
        </div>

        <!-- 不透明度 (Opacity) -->
        <div class="px-2.5 py-1.5 border-b border-canvas-border mb-1">
          <p class="text-[10px] text-ink-subtle mb-1">不透明度</p>
          <div class="grid grid-cols-4 gap-1" role="group" aria-label="不透明度の変更">
            <button
              v-for="op in OPACITY_PRESETS"
              :key="op"
              type="button"
              class="py-1 rounded text-[10px] font-mono transition-colors border"
              :class="Math.abs((item.opacity ?? 1) - op) < 0.05
                ? 'bg-brand text-brand-fg border-brand font-bold'
                : 'bg-canvas-card text-ink-muted border-canvas-border hover:text-ink'"
              :aria-pressed="Math.abs((item.opacity ?? 1) - op) < 0.05"
              @click="setOpacity(op)"
            >
              {{ Math.round(op * 100) }}%
            </button>
          </div>
        </div>

        <button
          type="button"
          class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          role="menuitem"
          @click="run(() => emit('focus-item', item!))"
        >
          <Maximize2 class="w-3.5 h-3.5" />
          <span class="flex-1 text-left">この資料にフォーカス</span>
        </button>

        <!-- 変形 -->
        <button
          type="button"
          class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          role="menuitem"
          @click="run(() => boardStore.flipHorizontal(item!.id))"
        >
          <FlipHorizontal class="w-3.5 h-3.5" />
          <span class="flex-1 text-left">左右反転</span>
          <kbd class="font-mono text-[10px] text-ink-subtle">H</kbd>
        </button>

        <button
          type="button"
          class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          role="menuitem"
          @click="run(() => boardStore.flipVertical(item!.id))"
        >
          <FlipVertical class="w-3.5 h-3.5" />
          <span class="flex-1 text-left">上下反転</span>
          <kbd class="font-mono text-[10px] text-ink-subtle">V</kbd>
        </button>

        <button
          type="button"
          class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          role="menuitem"
          @click="run(() => boardStore.toggleGrayscale(item!.id))"
        >
          <SunMoon class="w-3.5 h-3.5" />
          <span class="flex-1 text-left">グレースケール</span>
          <kbd class="font-mono text-[10px] text-ink-subtle">G</kbd>
        </button>

        <button
          type="button"
          class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          role="menuitem"
          @click="run(() => boardStore.updateItem(item!.id, { rotation: (item!.rotation + 90) % 360 }))"
        >
          <RotateCw class="w-3.5 h-3.5" />
          <span class="flex-1 text-left">90°回転</span>
          <kbd class="font-mono text-[10px] text-ink-subtle">R</kbd>
        </button>

        <div class="my-1 border-t border-canvas-border" />

        <!-- 並び替え -->
        <button
          type="button"
          class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          role="menuitem"
          @click="run(() => boardStore.bringToFront(item!.id))"
        >
          <ChevronUp class="w-3.5 h-3.5" />
          <span>前面へ</span>
        </button>

        <button
          type="button"
          class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          role="menuitem"
          @click="run(() => boardStore.sendToBack(item!.id))"
        >
          <ChevronDown class="w-3.5 h-3.5" />
          <span>背面へ</span>
        </button>

        <button
          type="button"
          class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          role="menuitem"
          @click="run(() => boardStore.updateItem(item!.id, { is_locked: !item!.is_locked }))"
        >
          <component :is="item.is_locked ? Unlock : Lock" class="w-3.5 h-3.5" />
          <span>{{ item.is_locked ? 'ロック解除' : '位置を固定' }}</span>
        </button>

        <div class="my-1 border-t border-canvas-border" />

        <!-- 解析・リンク -->
        <button
          type="button"
          class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          role="menuitem"
          @click="run(() => emit('open-insight'))"
        >
          <Sparkles class="w-3.5 h-3.5 text-brand" />
          <span>AI 解析を開く</span>
        </button>

        <a
          v-if="item.media?.source_url"
          :href="item.media.source_url"
          target="_blank"
          rel="noopener noreferrer"
          class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          role="menuitem"
        >
          <ExternalLink class="w-3.5 h-3.5" />
          <span class="flex-1 text-left">元のページを開く</span>
        </a>

        <button
          type="button"
          class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          role="menuitem"
          @click="run(copySourceUrl)"
        >
          <Copy class="w-3.5 h-3.5" />
          <span>リンクをコピー</span>
        </button>

        <div class="my-1 border-t border-canvas-border" />

        <button
          type="button"
          class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs text-danger hover:bg-danger-soft transition-colors"
          role="menuitem"
          @click="run(() => boardStore.deleteItem(item!.id))"
        >
          <Trash2 class="w-3.5 h-3.5" />
          <span class="flex-1 text-left">削除</span>
          <kbd class="font-mono text-[10px] opacity-70">Del</kbd>
        </button>
      </div>
    </div>
  </Teleport>
</template>