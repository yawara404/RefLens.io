<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import type { CanvasItem } from '~/types'
import { useBoardStore } from '~/stores/boardStore'
import { useHelpStore } from '~/stores/helpStore'
import { useToast } from '~/composables/useToast'
import { useTheme } from '~/composables/useTheme'
import { useCanvasTransform } from '~/composables/useCanvasTransform'
import { useImageProcessor } from '~/composables/useImageProcessor'
import { usePixiv } from '~/composables/usePixiv'
import ReferenceItem from './ReferenceItem.vue'
import CanvasItemMenu from './CanvasItemMenu.vue'
import ColorPaletteBar from './ColorPaletteBar.vue'

const props = defineProps<{ boardId: string }>()

const emit = defineEmits<{
  (e: 'open-insight', item: CanvasItem | null): void
}>()

const boardStore = useBoardStore()
const helpStore = useHelpStore()
const toast = useToast()
const pixiv = usePixiv()
const { setPreference } = useTheme()

const containerRef = ref<HTMLDivElement | null>(null)
const {
  panX,
  panY,
  zoom,
  transformStyle,
  screenToWorld,
  worldToScreen,
  zoomAt,
  panBy,
  fitToItems,
  resetView,
} = useCanvasTransform()

const { extractImagesFromDataTransfer } = useImageProcessor()

// ---------------------------------------------------------------
// インタラクション状態
// ---------------------------------------------------------------
const isPanning = ref(false)
const isSpacePressed = ref(false)
const panLast = { x: 0, y: 0 }

const draggingItem = ref<CanvasItem | null>(null)
const dragOffset = ref<{ id: string; offsetX: number; offsetY: number }[]>([])

const resizingItem = ref<CanvasItem | null>(null)
const resizeDirection = ref<string>('')
const resizeStart = { x: 0, y: 0, w: 0, h: 0, itemX: 0, itemY: 0, ratio: 1 }

const rotatingItem = ref<CanvasItem | null>(null)
const rotateCenter = { x: 0, y: 0 }
const rotateStartAngle = ref(0)
const rotateInitialItemAngle = ref(0)

const isSelectingBox = ref(false)
const selectionBoxStart = { x: 0, y: 0 }
const selectionBoxCurrent = { x: 0, y: 0 }

// タッチ操作（2本指パン / ピンチズーム）
const isTouchGesture = ref(false)
const pointers = new Map<number, { x: number; y: number }>()
let pinchStartDist = 0
let pinchStartZoom = 1
let pinchAnchor = { x: 0, y: 0 }

// ホイールモード（スクロール=パン / ズーム=ズーム）
const wheelMode = ref<'scroll' | 'zoom'>(
  typeof window !== 'undefined' && 'ontouchstart' in window ? 'zoom' : 'scroll'
)

// 自動保存
let autoSaveTimer: ReturnType<typeof setTimeout> | null = null
function triggerAutoSave() {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => {
    boardStore.saveCanvas(panX.value, panY.value, zoom.value)
  }, 900)
}

// ---------------------------------------------------------------
// ホイール（パン / ズーム）
// ---------------------------------------------------------------
function onWheel(e: WheelEvent) {
  if (!containerRef.value) return
  e.preventDefault()

  const rect = containerRef.value.getBoundingClientRect()

  // Ctrl / Cmd（ピンチの_numbaois）またはズームモード指定時はズーム
  if (e.ctrlKey || e.metaKey || wheelMode.value === 'zoom') {
    // トラックパッドの慣性を抑えるため係数を小さくする
    const factor = e.deltaY < 0 ? 1.06 : 1 / 1.06
    zoomAt(e.clientX, e.clientY, rect, factor)
    triggerAutoSave()
    return
  }

  const dx = e.shiftKey ? -e.deltaY : -e.deltaX
  const dy = e.shiftKey ? 0 : -e.deltaY

  panBy(dx, dy)
  triggerAutoSave()
}

// ---------------------------------------------------------------
// ポインタ（マウス / タッチ / ペン共通）
// ---------------------------------------------------------------
function onPointerDown(e: PointerEvent) {
  if (!containerRef.value) return

  // タッチはポインタイベントでまとめて扱う
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY })

  if (pointers.size === 2) {
    // 2本指: ピンチズーム + パン
    const [a, b] = [...pointers.values()]
    pinchStartDist = Math.hypot(b.x - a.x, b.y - a.y)
    pinchStartZoom = zoom.value
    pinchAnchor = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }
    isTouchGesture.value = true
    isPanning.value = false
    draggingItem.value = null
    resizingItem.value = null
    rotatingItem.value = null
    return
  }

  if (pointers.size > 2) return

  const isMiddleClick = e.button === 1
  const target = e.target as HTMLElement
  const isLeftOnBackground = e.button === 0 && (
    target === containerRef.value || target.dataset.canvasWorld === 'true'
  )
  const isLeftWithSpace = e.button === 0 && isSpacePressed.value
  // ライブラリの開閉に関係なく、空白ドラッグはパン、Shift+ドラッグは範囲選択。
  const isBackgroundPan = isLeftOnBackground && !e.shiftKey

  // 空白クリックはパンの開始と同時に選択を解除する。
  // パン分岐の後では通常クリックが早期 return してツールバーが残ってしまう。
  if (isLeftOnBackground && !e.shiftKey && !isSpacePressed.value) {
    boardStore.clearSelection()
  }

  if (isMiddleClick || isLeftWithSpace || isBackgroundPan) {
    e.preventDefault()
    isPanning.value = true
    panLast.x = e.clientX
    panLast.y = e.clientY
    return
  }

  if (isLeftOnBackground) {
    const rect = containerRef.value.getBoundingClientRect()
    const world = screenToWorld(e.clientX, e.clientY, rect)
    isSelectingBox.value = true
    selectionBoxStart.x = world.x
    selectionBoxStart.y = world.y
    selectionBoxCurrent.x = world.x
    selectionBoxCurrent.y = world.y
  }
}

function onPointerMove(e: PointerEvent) {
  if (!containerRef.value) return

  if (pointers.has(e.pointerId)) {
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY })
  }

  // --- ピンチズーム ---
  if (isTouchGesture && pointers.size === 2) {
    const [a, b] = [...pointers.values()]
    const dist = Math.hypot(b.x - a.x, b.y - a.y)
    if (pinchStartDist > 0) {
      const rect = containerRef.value.getBoundingClientRect()
      const target = Math.max(0.05, Math.min(5, pinchStartZoom * (dist / pinchStartDist)))
      zoomAt(pinchAnchor.x, pinchAnchor.y, rect, target / zoom.value)
      triggerAutoSave()
    }
    return
  }

  const rect = containerRef.value.getBoundingClientRect()

  // --- パン中 ---
  if (isPanning.value) {
    panBy(e.clientX - panLast.x, e.clientY - panLast.y)
    panLast.x = e.clientX
    panLast.y = e.clientY
    triggerAutoSave()
    return
  }

  // --- アイテムドラッグ ---
  if (draggingItem.value) {
    const worldMouse = screenToWorld(e.clientX, e.clientY, rect)
    for (const offset of dragOffset.value) {
      boardStore.updateItem(offset.id, {
        pos_x: Math.round(worldMouse.x + offset.offsetX),
        pos_y: Math.round(worldMouse.y + offset.offsetY),
      }, false)
    }
    return
  }

  // --- リサイズ ---
  if (resizingItem.value) {
    const dx = (e.clientX - resizeStart.x) / zoom.value
    const dy = (e.clientY - resizeStart.y) / zoom.value

    let newW = resizeStart.w
    let newH = resizeStart.h

    if (resizeDirection.value === 'se') {
      newW = Math.max(80, resizeStart.w + dx)
      newH = newW / resizeStart.ratio
    } else if (resizeDirection.value === 'sw') {
      newW = Math.max(80, resizeStart.w - dx)
      newH = newW / resizeStart.ratio
      boardStore.updateItem(resizingItem.value.id, {
        pos_x: resizeStart.itemX + (resizeStart.w - newW)
      }, false)
    } else if (resizeDirection.value === 'ne') {
      newW = Math.max(80, resizeStart.w + dx)
      newH = newW / resizeStart.ratio
      boardStore.updateItem(resizingItem.value.id, {
        pos_y: resizeStart.itemY + (resizeStart.h - newH)
      }, false)
    } else if (resizeDirection.value === 'nw') {
      newW = Math.max(80, resizeStart.w - dx)
      newH = newW / resizeStart.ratio
      boardStore.updateItem(resizingItem.value.id, {
        pos_x: resizeStart.itemX + (resizeStart.w - newW),
        pos_y: resizeStart.itemY + (resizeStart.h - newH)
      }, false)
    }

    boardStore.updateItem(resizingItem.value.id, {
      width: Math.round(newW),
      height: Math.round(newH)
    }, false)
    return
  }

  // --- 回転 ---
  if (rotatingItem.value) {
    const currentAngle = Math.atan2(e.clientY - rotateCenter.y, e.clientX - rotateCenter.x) * (180 / Math.PI)
    let delta = currentAngle - rotateStartAngle.value
    let finalAngle = (rotateInitialItemAngle.value + delta) % 360
    if (finalAngle < 0) finalAngle += 360
    if (e.shiftKey) finalAngle = Math.round(finalAngle / 15) * 15

    boardStore.updateItem(rotatingItem.value.id, { rotation: Math.round(finalAngle) }, false)
    return
  }

  // --- 矩形選択 ---
  if (isSelectingBox.value) {
    const world = screenToWorld(e.clientX, e.clientY, rect)
    selectionBoxCurrent.x = world.x
    selectionBoxCurrent.y = world.y

    const boxMinX = Math.min(selectionBoxStart.x, selectionBoxCurrent.x)
    const boxMaxX = Math.max(selectionBoxStart.x, selectionBoxCurrent.x)
    const boxMinY = Math.min(selectionBoxStart.y, selectionBoxCurrent.y)
    const boxMaxY = Math.max(selectionBoxStart.y, selectionBoxCurrent.y)

    boardStore.selectedItemIds = boardStore.items
      .filter(it => {
        const itRight = it.pos_x + it.width
        const itBottom = it.pos_y + it.height
        return !(it.pos_x > boxMaxX || itRight < boxMinX || it.pos_y > boxMaxY || itBottom < boxMinY)
      })
      .map(it => it.id)
  }
}

function onPointerUp(e: PointerEvent) {
  pointers.delete(e.pointerId)

  if (pointers.size < 2) {
    isTouchGesture.value = false
    pinchStartDist = 0
  }

  if (isPanning.value) {
    isPanning.value = false
    triggerAutoSave()
  }

  if (draggingItem.value || resizingItem.value || rotatingItem.value) {
    boardStore.recordHistory()
    triggerAutoSave()
  }

  draggingItem.value = null
  resizingItem.value = null
  rotatingItem.value = null
  isSelectingBox.value = false
}

// ---------------------------------------------------------------
// アイテム操作の開始
// ---------------------------------------------------------------
function handleItemSelect(item: CanvasItem, evt: MouseEvent) {
  boardStore.selectItem(item.id, evt.shiftKey || evt.metaKey || evt.ctrlKey)
}

function handleStartDrag(evt: PointerEvent, item: CanvasItem) {
  if (isSpacePressed.value || !containerRef.value) return
  draggingItem.value = item

  const rect = containerRef.value.getBoundingClientRect()
  const worldMouse = screenToWorld(evt.clientX, evt.clientY, rect)

  const targets = boardStore.selectedItems.length ? boardStore.selectedItems : [item]
  dragOffset.value = targets.map(t => ({
    id: t.id,
    offsetX: t.pos_x - worldMouse.x,
    offsetY: t.pos_y - worldMouse.y,
  }))
}

function handleStartResize(evt: PointerEvent, item: CanvasItem, direction: string) {
  resizingItem.value = item
  resizeDirection.value = direction
  resizeStart.x = evt.clientX
  resizeStart.y = evt.clientY
  resizeStart.w = item.width
  resizeStart.h = item.height
  resizeStart.itemX = item.pos_x
  resizeStart.itemY = item.pos_y
  resizeStart.ratio = item.width / item.height
}

function handleStartRotate(evt: PointerEvent, item: CanvasItem) {
  if (!containerRef.value) return
  rotatingItem.value = item

  const rect = containerRef.value.getBoundingClientRect()
  const centerScreen = worldToScreen(
    item.pos_x + item.width / 2,
    item.pos_y + item.height / 2,
    rect
  )
  rotateCenter.x = centerScreen.x
  rotateCenter.y = centerScreen.y
  rotateStartAngle.value = Math.atan2(evt.clientY - centerScreen.y, evt.clientX - centerScreen.x) * (180 / Math.PI)
  rotateInitialItemAngle.value = item.rotation
}

// ---------------------------------------------------------------
// キーボードショートカット
// ---------------------------------------------------------------
function isTypingTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null
  if (!el) return false
  if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') return true
  return !!el.isContentEditable
}

function onKeyDown(e: KeyboardEvent) {
  if (isTypingTarget(e.target)) return

  const mod = e.metaKey || e.ctrlKey

  // Space: パン準備（ただし入力欄以外）
  if (e.code === 'Space' && !isSpacePressed.value) {
    e.preventDefault()
    isSpacePressed.value = true
    return
  }

  // Cmd/Ctrl  系
  if (mod) {
    switch (e.key.toLowerCase()) {
      case 'a':
        e.preventDefault()
        boardStore.selectAll()
        return
      case 'z':
        e.preventDefault()
        if (e.shiftKey) boardStore.redo()
        else boardStore.undo()
        return
      case 'y':
        e.preventDefault()
        boardStore.redo()
        return
      case '0':
        e.preventDefault()
        if (containerRef.value) resetView(containerRef.value.getBoundingClientRect())
        return
    }
    return
  }

  // 単独キー
  switch (e.key) {
    case 'h': case 'H':
      e.preventDefault()
      boardStore.flipHorizontal()
      break
    case 'v': case 'V':
      e.preventDefault()
      boardStore.flipVertical()
      break
    case 'g': case 'G':
      e.preventDefault()
      boardStore.toggleGrayscale()
      break
    case 'r': case 'R':
      e.preventDefault()
      for (const item of boardStore.selectedItems) {
        boardStore.updateItem(item.id, { rotation: (item.rotation + 90) % 360 })
      }
      break
    case 'b': case 'B':
      e.preventDefault()
      boardStore.toggleBrowser()
      break
    case 'd': case 'D':
      e.preventDefault()
      setPreference(document.documentElement.classList.contains('dark') ? 'light' : 'dark')
      break
    case 'f': case 'F':
      e.preventDefault()
      fitView()
      break
    case 'i': case 'I':
      e.preventDefault()
      emit('open-insight', boardStore.activeItem)
      break
    case 'Delete':
    case 'Backspace':
      if (boardStore.selectedItemIds.length) {
        e.preventDefault()
        boardStore.deleteSelected()
      }
      break
    case 'Escape':
      if (!helpStore.isOpen) {
        boardStore.clearSelection()
      }
      break
  }
}

function onKeyUp(e: KeyboardEvent) {
  if (e.code === 'Space') isSpacePressed.value = false
}

// ---------------------------------------------------------------
// Drag & Drop / Paste
// ---------------------------------------------------------------
function onDragOver(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'
}

async function onDrop(e: DragEvent) {
  e.preventDefault()
  if (!e.dataTransfer || !containerRef.value) return

  const rect = containerRef.value.getBoundingClientRect()
  const world = screenToWorld(e.clientX, e.clientY, rect)

  const bookmarkId = e.dataTransfer.getData('application/reflens-bookmark-id')
  if (bookmarkId) {
    await boardStore.placeBookmarkOnBoard(bookmarkId, world.x, world.y)
    return
  }

  const pixivId = e.dataTransfer.getData('application/reflens-pixiv-id')
  if (/^\d+$/.test(pixivId)) {
    if (await pixiv.stockToCanvas([pixivId], props.boardId, world.x, world.y)) {
      await boardStore.loadBoard(props.boardId)
      await boardStore.fetchBookmarks()
    }
    return
  }

  const urlData = e.dataTransfer.getData('text/uri-list') || e.dataTransfer.getData('text/plain')
  if (urlData && /^https?:\/\//.test(urlData.trim())) {
    await boardStore.addBookmark(urlData.trim(), undefined, true, world.x, world.y)
    return
  }

  const files = extractImagesFromDataTransfer(e.dataTransfer)
  if (files.length) {
    await boardStore.uploadImages(files, world.x, world.y)
  }
}

async function onPaste(e: ClipboardEvent) {
  if (!e.clipboardData || !containerRef.value) return
  if (isTypingTarget(e.target)) return

  const files = extractImagesFromDataTransfer(e.clipboardData)
  if (files.length) {
    const rect = containerRef.value.getBoundingClientRect()
    const world = screenToWorld(rect.width / 2, rect.height / 2, rect)
    await boardStore.uploadImages(files, world.x, world.y)
  }
}

// 右クリック（または長押し）で開くアイテムメニュー
const menuState = ref<{ item: CanvasItem; x: number; y: number } | null>(null)

function handleContextMenu(evt: MouseEvent, item: CanvasItem) {
  evt.preventDefault()
  boardStore.selectItem(item.id)
  menuState.value = { item, x: evt.clientX, y: evt.clientY }
}

// ---------------------------------------------------------------
// Computed
// ---------------------------------------------------------------
const selectionBoxStyle = computed(() => {
  const x = Math.min(selectionBoxStart.x, selectionBoxCurrent.x)
  const y = Math.min(selectionBoxStart.y, selectionBoxCurrent.y)
  const w = Math.abs(selectionBoxCurrent.x - selectionBoxStart.x)
  const h = Math.abs(selectionBoxCurrent.y - selectionBoxStart.y)
  return {
    transform: `translate3d(${x}px, ${y}px, 0px)`,
    width: `${w}px`,
    height: `${h}px`,
  }
})

const activePalette = computed(() => boardStore.activeItem?.ai_analysis?.palette || [])

const backgroundClass = computed(() => {
  const theme = boardStore.currentBoard?.background_theme
  if (theme === 'dark-dots') return 'bg-canvas-dots'
  if (theme === 'dark-plain') return 'bg-canvas-plain'
  return 'bg-canvas-grid'
})

function fitView() {
  if (containerRef.value) {
    fitToItems(boardStore.items, containerRef.value.getBoundingClientRect())
  }
}

defineExpose({ fitView, resetView })

// ---------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------
let initialFitTimer: ReturnType<typeof setTimeout> | null = null

onMounted(() => {
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('keyup', onKeyUp)
  window.addEventListener('paste', onPaste)

  // ポインタをウィンドウ外に出てもドラッグ/パンが途切れないようにする
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('pointercancel', onPointerUp)

  // 初期ロード後に自動で全体表示
  initialFitTimer = setTimeout(() => {
    if (boardStore.items.length) fitView()
  }, 350)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('keyup', onKeyUp)
  window.removeEventListener('paste', onPaste)
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', onPointerUp)
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  if (initialFitTimer) clearTimeout(initialFitTimer)
})

// ボードが変わったら表示をリセット
watch(() => props.boardId, () => {
  boardStore.clearSelection()
  setTimeout(() => {
    if (boardStore.items.length) fitView()
  }, 350)
})
</script>

<template>
  <div
    ref="containerRef"
    class="relative w-full h-full overflow-hidden select-none touch-canvas no-touch-zoom"
    :class="[
      backgroundClass,
      isPanning || isTouchGesture ? 'cursor-grabbing' : isSpacePressed ? 'cursor-grab' : ''
    ]"
    @wheel="onWheel"
    @pointerdown="onPointerDown"
    @dragover="onDragOver"
    @drop="onDrop"
    @contextmenu.prevent
  >
    <!-- ワールドレイヤー -->
    <div
      class="absolute top-0 left-0 will-change-transform origin-top-left"
      data-canvas-world="true"
      :style="transformStyle"
    >
      <ReferenceItem
        v-for="item in boardStore.items"
        :key="item.id"
        :item="item"
        :is-selected="boardStore.selectedItemIds.includes(item.id)"
        :is-dimmed="!boardStore.filteredItemIds.includes(item.id)"
        :zoom="zoom"
        @select="handleItemSelect(item, $event)"
        @start-drag="handleStartDrag"
        @start-resize="handleStartResize"
        @start-rotate="handleStartRotate"
        @open-insight="emit('open-insight', $event)"
        @context-menu="handleContextMenu"
      />

      <!-- 矩形選択のラバーバンド -->
      <div
        v-if="isSelectingBox"
        class="absolute border border-brand bg-brand-soft pointer-events-none rounded-sm"
        :style="selectionBoxStyle"
      />
    </div>

    <!-- 右クリックメニュー -->
    <CanvasItemMenu
      :item="menuState?.item || null"
      :x="menuState?.x || 0"
      :y="menuState?.y || 0"
      @close="menuState = null"
      @open-insight="() => {
        if (menuState) emit('open-insight', menuState.item)
        menuState = null
      }"
    />

    <!-- 空の状態 -->
    <div
      v-if="!boardStore.items.length"
      class="absolute inset-0 flex items-center justify-center pointer-events-none p-8"
    >
      <div class="text-center max-w-sm">
        <p class="text-sm font-semibold text-ink">キャンバスが空です</p>
        <p class="text-xs text-ink-muted mt-2 leading-relaxed">
          画像をドラッグ＆ドロップ、または貼り付け（⌘V）で追加できます。<br>
          下部のツールバーからpixiv・Instagram取り込みも 가능합니다。
        </p>
      </div>
    </div>

    <!-- 選択中アイテムのカラーチップバー -->
    <div
      v-if="activePalette.length > 0"
      class="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 pointer-events-auto animate-slide-up"
    >
      <ColorPaletteBar :palette="activePalette" :title="boardStore.activeItem?.caption" />
    </div>

    <!-- 右下: ズーム表示 / ホイールモード -->
    <div class="absolute bottom-6 right-6 flex items-center gap-2 z-10 select-none">
      <button
        type="button"
        class="floating-bar px-2.5 py-1 rounded-full text-xs font-mono text-ink-muted hover:text-ink transition-colors"
        :title="wheelMode === 'scroll' ? 'ホイール/トラックパッド: パン。クリックでズームに切替' : 'ホイール: ズーム。クリックでパンに切替'"
        @click="wheelMode = wheelMode === 'scroll' ? 'zoom' : 'scroll'"
      >
        {{ wheelMode === 'scroll' ? 'Pan' : 'Zoom' }}
      </button>

      <div class="floating-bar px-3 py-1 rounded-full text-xs font-mono text-ink-muted pointer-events-none">
        {{ Math.round(zoom * 100) }}%
      </div>

    </div>
  </div>
</template>
