<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import {
  Lock,
  Sparkles,
  ExternalLink,
  Instagram,
  Globe,
  Bookmark,
  Folder,
  GripVertical,
} from 'lucide-vue-next'
import type { CanvasItem } from '~/types'
import { useMediaUrl } from '~/composables/useMediaUrl'

const props = defineProps<{
  item: CanvasItem
  isSelected: boolean
  isDimmed: boolean
  isDragging?: boolean
  zoom: number
}>()

const emit = defineEmits<{
  (e: 'select', evt: MouseEvent): void
  (e: 'start-drag', evt: PointerEvent, item: CanvasItem): void
  (e: 'start-resize', evt: PointerEvent, item: CanvasItem, direction: string): void
  (e: 'start-rotate', evt: PointerEvent, item: CanvasItem): void
  (e: 'open-insight', item: CanvasItem): void
  (e: 'context-menu', evt: MouseEvent, item: CanvasItem): void
  (e: 'focus-item', item: CanvasItem): void
}>()

const { resolveMediaUrl } = useMediaUrl()

const isHovered = ref(false)

const resolvedImageUrl = computed(() => resolveMediaUrl(props.item.media?.file_path))

const itemStyle = computed(() => ({
  transform: `translate3d(${props.item.pos_x}px, ${props.item.pos_y}px, 0px) rotate(${props.item.rotation}deg)`,
  width: `${props.item.width}px`,
  height: `${props.item.height}px`,
  zIndex: props.item.z_index,
  opacity: props.isDragging ? 0.32 : (props.isDimmed ? 0.22 : props.item.opacity),
}))

const imageStyle = computed(() => ({
  transform: `scale(${props.item.is_flipped_h ? -1 : 1}, ${props.item.is_flipped_v ? -1 : 1})`,
  filter: props.item.is_grayscale ? 'grayscale(100%) contrast(1.15)' : 'none',
  border: props.item.border_width > 0
    ? `${props.item.border_width}px solid ${props.item.border_color}`
    : 'none',
}))

/** ズームが低いときはハンドルを隠して視認性の妨げにしない */
const isDetailed = computed(() => props.zoom >= 0.25)

function onPointerDown(evt: PointerEvent) {
  if (evt.button === 2) return // 右クリックは contextmenu で処理
  if (evt.button !== 0) return

  if (evt.pointerType === 'touch') {
    const now = Date.now()
    if (now - lastTapAt < 320) {
      clearLongPress()
      lastTapAt = 0
      emit('focus-item', props.item)
      return
    }
    lastTapAt = now
    touchStartPos = { x: evt.clientX, y: evt.clientY }
    clearLongPress()
    longPressTimer = setTimeout(() => {
      emit('context-menu', { clientX: touchStartPos.x, clientY: touchStartPos.y, preventDefault: () => {} } as unknown as MouseEvent, props.item)
    }, 480)
  }

  if (evt.pointerType !== 'touch') {
    evt.preventDefault()
  }

  emit('select', evt as unknown as MouseEvent)
  if (!props.item.is_locked) {
    emit('start-drag', evt, props.item)
  }
}

let longPressTimer: ReturnType<typeof setTimeout> | null = null
let touchStartPos = { x: 0, y: 0 }
let lastTapAt = 0

function clearLongPress() {
  if (longPressTimer) {
    clearTimeout(longPressTimer)
    longPressTimer = null
  }
}

function onPointerMove(evt: PointerEvent) {
  if (!longPressTimer) return
  if (Math.hypot(evt.clientX - touchStartPos.x, evt.clientY - touchStartPos.y) > 8) {
    clearLongPress()
  }
}

onBeforeUnmount(clearLongPress)

function onDragStart(evt: DragEvent) {
  if (!evt.dataTransfer) return
  evt.dataTransfer.effectAllowed = 'copyMove'
  const bookmarkId = props.item.media_item_id || props.item.media?.id || props.item.id
  evt.dataTransfer.setData('application/reflens-bookmark-id', bookmarkId)
  evt.dataTransfer.setData('application/reflens-canvas-item-id', props.item.id)
  evt.dataTransfer.setData('text/plain', props.item.caption || props.item.media?.title || props.item.id)
}

function onContextMenu(evt: MouseEvent) {
  emit('context-menu', evt, props.item)
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
    tabindex="0"
    role="group"
    :aria-label="item.caption || item.media?.title || item.media?.original_file_name || 'キャンバス上の資料'"
    :class="[
      item.is_locked ? 'cursor-default' : 'cursor-move',
      isSelected ? 'ring-2 ring-brand shadow-canvas-item' : 'shadow-canvas-item hover:ring-1 hover:ring-canvas-border-strong',
      item.is_locked && !isSelected ? 'ring-1 ring-warn/50' : ''
    ]"
    :style="itemStyle"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="clearLongPress"
    @pointercancel="clearLongPress"
    @dblclick.stop="emit('focus-item', item)"
    @contextmenu="onContextMenu"
    @focus.self="emit('select', { shiftKey: false, metaKey: false, ctrlKey: false } as MouseEvent)"
    @keydown.enter.self.prevent="emit('open-insight', item)"
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
        class="absolute top-2 right-2 p-1 rounded bg-canvas-raised/90 text-warn shadow-sm z-10"
      >
        <Lock class="w-3.5 h-3.5" />
      </div>

      <!-- ブックマークブラウザへのドラッグハンドル（非ロックかつホバーまたは選択時に表示） -->
      <div
        v-else-if="isHovered || isSelected"
        class="absolute top-2 right-2 z-20 flex items-center gap-1 pointer-events-auto animate-fade-in"
        @pointerdown.stop
      >
        <div
          draggable="true"
          class="px-1.5 py-1 rounded-lg bg-canvas-panel/95 hover:bg-brand hover:text-brand-fg text-ink-muted border border-canvas-border shadow-sm cursor-grab active:cursor-grabbing transition-colors flex items-center gap-0.5 text-[10px] font-bold"
          title="ドラッグしてブックマークブラウザやフォルダへ保存"
          @dragstart="onDragStart"
        >
          <GripVertical class="w-3 h-3 opacity-60" />
          <Bookmark class="w-3 h-3" />
        </div>
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

      <!-- フォルダバッジ -->
      <div
        v-if="item.media?.folder_name && item.media.folder_name !== 'All References'"
        class="absolute bottom-2 left-2 z-10 flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-canvas-panel/90 text-brand border border-canvas-border shadow-sm pointer-events-none truncate max-w-[140px]"
      >
        <Folder class="w-3 h-3 shrink-0" />
        <span class="truncate">{{ item.media.folder_name }}</span>
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

    <!-- 変形ハンドル（選択中かつ非ロック時・ツールバーと干渉しないよう上部に回転ハンドルのみ配置） -->
    <template v-if="isSelected && !item.is_locked && isDetailed">
      <!-- 回転ハンドル -->
      <div
        class="absolute -top-8 left-1/2 -translate-x-1/2 z-20 cursor-grab p-1"
        title="ドラッグして回転（Shiftで15°スナップ）"
        @pointerdown.stop="emit('start-rotate', $event, item)"
      >
        <div class="w-5 h-5 sm:w-4 sm:h-4 rounded-full bg-canvas-panel border-2 border-brand flex items-center justify-center shadow-canvas-item hover:scale-125 transition-transform">
          <div class="w-1.5 h-1.5 sm:w-1 sm:h-1 rounded-full bg-brand" />
        </div>
      </div>
      <div class="absolute -top-4 left-1/2 -translate-x-1/2 w-0.5 h-4 bg-brand pointer-events-none" />

      <!-- 四隅のリサイズハンドル（タッチ向けに大きめ） -->
      <div
        v-for="dir in (['se', 'sw', 'ne', 'nw'] as const)"
        :key="dir"
        class="absolute w-5 h-5 sm:w-4 sm:h-4 bg-canvas-panel border-2 border-brand rounded-sm shadow-canvas-item hover:scale-125 transition-transform z-20"
        :class="{
          'cursor-se-resize': dir === 'se',
          'cursor-sw-resize': dir === 'sw',
          'cursor-ne-resize': dir === 'ne',
          'cursor-nw-resize': dir === 'nw',
          '-bottom-2.5 -right-2.5 sm:-bottom-2 sm:-right-2': dir === 'se',
          '-bottom-2.5 -left-2.5 sm:-bottom-2 sm:-left-2': dir === 'sw',
          '-top-2.5 -right-2.5 sm:-top-2 sm:-right-2': dir === 'ne',
          '-top-2.5 -left-2.5 sm:-top-2 sm:-left-2': dir === 'nw',
        }"
        @pointerdown.stop="emit('start-resize', $event, item, dir)"
      />
    </template>
  </div>
</template>
