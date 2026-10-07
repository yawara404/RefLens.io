<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  FlipHorizontal,
  FlipVertical,
  SunMoon,
  Trash2,
  Lock,
  Unlock,
  Sparkles,
  ChevronUp,
  ChevronDown,
  RotateCw,
  ExternalLink,
  Instagram,
  Globe,
} from 'lucide-vue-next'
import type { CanvasItem } from '~/types'
import { useBoardStore } from '~/stores/boardStore'
import { useMediaUrl } from '~/composables/useMediaUrl'

const props = defineProps<{
  item: CanvasItem
  isSelected: boolean
  isDimmed: boolean
  zoom: number
}>()

const emit = defineEmits<{
  (e: 'select', evt: MouseEvent): void
  (e: 'start-drag', evt: PointerEvent, item: CanvasItem): void
  (e: 'start-resize', evt: PointerEvent, item: CanvasItem, direction: string): void
  (e: 'start-rotate', evt: PointerEvent, item: CanvasItem): void
  (e: 'open-insight', item: CanvasItem): void
  (e: 'context-menu', evt: MouseEvent, item: CanvasItem): void
}>()

const boardStore = useBoardStore()
const { resolveMediaUrl } = useMediaUrl()

const isHovered = ref(false)

const resolvedImageUrl = computed(() => resolveMediaUrl(props.item.media?.file_path))

const itemStyle = computed(() => ({
  transform: `translate3d(${props.item.pos_x}px, ${props.item.pos_y}px, 0px) rotate(${props.item.rotation}deg)`,
  width: `${props.item.width}px`,
  height: `${props.item.height}px`,
  zIndex: props.item.z_index,
  opacity: props.isDimmed ? 0.22 : props.item.opacity,
}))

const imageStyle = computed(() => ({
  transform: `scale(${props.item.is_flipped_h ? -1 : 1}, ${props.item.is_flipped_v ? -1 : 1})`,
  filter: props.item.is_grayscale ? 'grayscale(100%) contrast(1.15)' : 'none',
  border: props.item.border_width > 0
    ? `${props.item.border_width}px solid ${props.item.border_color}`
    : 'none',
}))

/** ズームが低いときはハンドルやツールバーを隠して{item}の妨げにしない */
const isDetailed = computed(() => props.zoom >= 0.28)

function onPointerDown(evt: PointerEvent) {
  if (evt.button === 2) return // 右クリックは contextmenu で処理
  if (evt.button !== 0) return

  emit('select', evt as unknown as MouseEvent)
  if (!props.item.is_locked) {
    emit('start-drag', evt, props.item)
  }
}

function onContextMenu(evt: MouseEvent) {
  if (!props.item.is_locked) {
    // ロック中はメニューを出さない（誤操作防止）
    emit('context-menu', evt, props.item)
  }
}

const sourceBadgeClass = computed(() => {
  switch (props.item.media?.source_type) {
    case 'pixiv':
      return 'bg-pixiv text-white'
    case 'instagram':
      return 'bg-instagram text-white'
    default:
      return 'bg-canvas-raised text-ink-muted border border-canvas-border-strong'
  }
})
</script>

<template>
  <div
    class="absolute top-0 left-0 group no-context-menu"
    :class="[
      item.is_locked ? 'cursor-default' : 'cursor-move',
      isSelected ? 'ring-2 ring-brand shadow-canvas-item' : 'shadow-canvas-item hover:ring-1 hover:ring-canvas-border-strong',
      item.is_locked && !isSelected ? 'ring-1 ring-warn/50' : ''
    ]"
    :style="itemStyle"
    @pointerdown="onPointerDown"
    @contextmenu="onContextMenu"
    @pointerenter="isHovered = true"
    @pointerleave="isHovered = false"
  >
    <!-- メイン画像 -->
    <div class="w-full h-full relative overflow-hidden bg-canvas-sunken">
      <img
        :src="resolvedImageUrl"
        :alt="item.caption || 'Reference image'"
        class="w-full h-full object-cover pointer-events-none no-drag-select"
        :style="imageStyle"
        loading="lazy"
        draggable="false"
      />

      <!-- キャプション -->
      <div
        v-if="item.caption && isDetailed"
        class="absolute bottom-0 inset-x-0 bg-black/65 px-2 py-1 text-[11px] text-white/95 truncate pointer-events-none"
      >
        {{ item.caption }}
      </div>

      <!-- ロック表示 -->
      <div
        v-if="item.is_locked"
        class="absolute top-2 right-2 p-1 rounded bg-canvas-raised/90 text-warn"
      >
        <Lock class="w-3.5 h-3.5" />
      </div>

      <!-- ソースバッジ -->
      <div
        v-if="item.media?.source_type && item.media.source_type !== 'local_upload'"
        class="absolute top-2 left-2 z-10"
      >
        <a
          v-if="item.media.source_url"
          :href="item.media.source_url"
          target="_blank"
          rel="noopener noreferrer"
          class="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold shadow-canvas-item transition-opacity hover:opacity-80 pointer-events-auto"
          :class="sourceBadgeClass"
          :title="`開く: ${item.media.source_url}`"
          @pointerdown.stop
        >
          <span v-if="item.media.source_type === 'pixiv'">pixiv</span>
          <Instagram v-else-if="item.media.source_type === 'instagram'" class="w-3 h-3" />
          <Globe v-else class="w-3 h-3" />
          <ExternalLink class="w-2.5 h-2.5 opacity-75" />
        </a>
      </div>

      <!-- AI解析済みマーカー -->
      <div
        v-if="item.ai_analysis && isSelected"
        class="absolute bottom-2 right-2 bg-brand px-1.5 py-0.5 rounded text-[10px] font-medium text-brand-fg flex items-center gap-1 shadow-canvas-item z-10"
      >
        <Sparkles class="w-3 h-3" />
        <span class="hidden sm:inline">AI</span>
      </div>
    </div>

    <!-- 選択時の浮动ツールバー -->
    <div
      v-if="isSelected && isDetailed"
      class="absolute -top-10 left-1/2 -translate-x-1/2 floating-bar px-1 py-1 rounded-lg flex items-center gap-0.5 z-30"
      @pointerdown.stop
    >
      <button
        type="button"
        class="p-1.5 rounded text-ink-muted hover:text-brand hover:bg-brand-soft transition-colors flex items-center gap-1 text-xs px-1.5"
        title="AI 解析を開く"
        @click.stop="emit('open-insight', item)"
      >
        <Sparkles class="w-3.5 h-3.5" />
        <span class="text-[11px] font-medium hidden sm:inline">AI</span>
      </button>

      <div class="h-3 w-px bg-canvas-border mx-0.5" />

      <button
        type="button"
        class="p-1.5 rounded hover:bg-canvas-hover transition-colors"
        :class="item.is_flipped_h ? 'text-brand bg-brand-soft' : 'text-ink-muted hover:text-ink'"
        title="左右反転 [H]"
        aria-label="左右反転"
        @click.stop="boardStore.flipHorizontal(item.id)"
      >
        <FlipHorizontal class="w-3.5 h-3.5" />
      </button>

      <button
        type="button"
        class="p-1.5 rounded hover:bg-canvas-hover transition-colors"
        :class="item.is_flipped_v ? 'text-brand bg-brand-soft' : 'text-ink-muted hover:text-ink'"
        title="上下反転 [V]"
        aria-label="上下反転"
        @click.stop="boardStore.flipVertical(item.id)"
      >
        <FlipVertical class="w-3.5 h-3.5" />
      </button>

      <button
        type="button"
        class="p-1.5 rounded hover:bg-canvas-hover transition-colors"
        :class="item.is_grayscale ? 'text-brand bg-brand-soft' : 'text-ink-muted hover:text-ink'"
        title="グレースケール [G]"
        aria-label="グレースケール切り替え"
        @click.stop="boardStore.toggleGrayscale(item.id)"
      >
        <SunMoon class="w-3.5 h-3.5" />
      </button>

      <div class="h-3 w-px bg-canvas-border mx-0.5" />

      <button
        type="button"
        class="p-1.5 rounded text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
        title="90°回転 [R]"
        aria-label="90度回転"
        @click.stop="boardStore.updateItem(item.id, { rotation: (item.rotation + 90) % 360 })"
      >
        <RotateCw class="w-3.5 h-3.5" />
      </button>

      <button
        type="button"
        class="p-1.5 rounded text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
        title="前面へ"
        aria-label="前面へ移動"
        @click.stop="boardStore.bringToFront(item.id)"
      >
        <ChevronUp class="w-3.5 h-3.5" />
      </button>

      <button
        type="button"
        class="p-1.5 rounded text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
        title="背面へ"
        aria-label="背面へ移動"
        @click.stop="boardStore.sendToBack(item.id)"
      >
        <ChevronDown class="w-3.5 h-3.5" />
      </button>

      <button
        type="button"
        class="p-1.5 rounded text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
        :class="item.is_locked ? 'text-warn' : ''"
        :title="item.is_locked ? 'ロック解除' : '位置とサイズを固定'"
        :aria-label="item.is_locked ? 'ロック解除' : 'ロック'"
        @click.stop="boardStore.updateItem(item.id, { is_locked: !item.is_locked })"
      >
        <component :is="item.is_locked ? Lock : Unlock" class="w-3.5 h-3.5" />
      </button>

      <button
        type="button"
        class="p-1.5 rounded text-danger hover:bg-danger-soft transition-colors"
        title="削除 [Delete]"
        aria-label="削除"
        @click.stop="boardStore.deleteItem(item.id)"
      >
        <Trash2 class="w-3.5 h-3.5" />
      </button>
    </div>

    <!-- 変形ハンドル（選択中かつ非ロック時） -->
    <template v-if="isSelected && !item.is_locked && isDetailed">
      <!-- 回転ハンドル -->
      <div
        class="absolute -top-7 left-1/2 -translate-x-1/2 z-20 cursor-grab"
        title="回転（Shiftで15°スナップ）"
        @pointerdown.stop="emit('start-rotate', $event, item)"
      >
        <div class="w-4 h-4 rounded-full bg-canvas-panel border-2 border-brand flex items-center justify-center shadow-canvas-item hover:scale-125 transition-transform">
          <div class="w-1 h-1 rounded-full bg-brand" />
        </div>
      </div>
      <div class="absolute -top-7 left-1/2 -translate-x-1/2 w-px h-4 bg-brand/50 pointer-events-none" />

      <!-- 四隅のリサイズハンドル（タッチ向けに少し大きめ） -->
      <div
        v-for="dir in (['se', 'sw', 'ne', 'nw'] as const)"
        :key="dir"
        class="absolute w-4 h-4 bg-canvas-panel border-2 border-brand rounded-sm shadow-canvas-item hover:scale-125 transition-transform z-20"
        :class="{
          'cursor-se-resize': dir === 'se',
          'cursor-sw-resize': dir === 'sw',
          'cursor-ne-resize': dir === 'ne',
          'cursor-nw-resize': dir === 'nw',
          '-bottom-2 -right-2': dir === 'se',
          '-bottom-2 -left-2': dir === 'sw',
          '-top-2 -right-2': dir === 'ne',
          '-top-2 -left-2': dir === 'nw',
        }"
        @pointerdown.stop="emit('start-resize', $event, item, dir)"
      />
    </template>
  </div>
</template>