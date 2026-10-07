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
}>()

const boardStore = useBoardStore()
const toast = useToast()

const menuRef = ref<HTMLElement | null>(null)
const position = ref({ left: 0, top: 0 })

const item = computed(() => props.item)

/** 画面端で切れないように位置を補正する */
async function clampPosition() {
  const el = menuRef.value
  if (!el) return

  const { offsetWidth: w, offsetHeight: h } = el
  const margin = 8
  position.value = {
    left: Math.min(props.x, window.innerWidth - w - margin),
    top: Math.min(props.y, window.innerHeight - h - margin),
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
    if (!props.item) return
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
        class="absolute min-w-[196px] p-1 rounded-xl border border-canvas-border bg-canvas-raised shadow-pop animate-scale-in"
        :style="{ left: `${position.left}px`, top: `${position.top}px` }"
        role="menu"
        @pointerdown.stop
      >
        <!-- タイトル -->
        <div class="px-2.5 py-1.5 border-b border-canvas-border mb-1">
          <p class="text-[11px] font-semibold text-ink truncate" :title="item.caption || item.media?.original_file_name">
            {{ item.caption || item.media?.original_file_name || 'Reference' }}
          </p>
        </div>

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