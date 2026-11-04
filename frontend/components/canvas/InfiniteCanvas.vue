<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import {
  Bookmark,
  Compass,
  Sparkles,
  FlipHorizontal,
  FlipVertical,
  SunMoon,
  RotateCw,
  ChevronUp,
  ChevronDown,
  Lock,
  Unlock,
  MoreHorizontal,
  Trash2,
  Maximize2,
  X,
} from 'lucide-vue-next'
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
  (e: 'open-pixiv'): void
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

// 自動保存 & ビューポート中央座標の同期
function syncViewportCenter() {
  if (!containerRef.value) return
  const rect = containerRef.value.getBoundingClientRect()
  if (rect.width === 0 || rect.height === 0) return
  const centerWorld = screenToWorld(rect.left + rect.width / 2, rect.top + rect.height / 2, rect)
  boardStore.setViewportCenter(centerWorld.x, centerWorld.y)
}

let autoSaveTimer: ReturnType<typeof setTimeout> | null = null
function triggerAutoSave() {
  syncViewportCenter()
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

  // マウスボタンが既に離されている（ウィンドウ外で離した等）場合は即座にドラッグ状態を終了する
  if (
    e.pointerType === 'mouse'
    && e.buttons === 0
    && (isPanning.value || draggingItem.value || resizingItem.value || rotatingItem.value || isSelectingBox.value)
  ) {
    onPointerUp(e)
    return
  }

  if (pointers.has(e.pointerId)) {
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY })
  }

  // --- ピンチズーム + 2本指パン ---
  if (isTouchGesture.value && pointers.size === 2) {
    const [a, b] = [...pointers.values()]
    const midX = (a.x + b.x) / 2
    const midY = (a.y + b.y) / 2
    const dist = Math.hypot(b.x - a.x, b.y - a.y)
    const rect = containerRef.value.getBoundingClientRect()

    // 2本指の中点の移動量でパン
    panBy(midX - pinchAnchor.x, midY - pinchAnchor.y)
    pinchAnchor = { x: midX, y: midY }

    if (pinchStartDist > 0) {
      const target = Math.max(0.05, Math.min(5, pinchStartZoom * (dist / pinchStartDist)))
      zoomAt(midX, midY, rect, target / zoom.value)
    }
    triggerAutoSave()
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

function onPointerUp(e?: PointerEvent) {
  if (e) {
    pointers.delete(e.pointerId)
  } else {
    pointers.clear()
  }

  if (pointers.size < 2) {
    isTouchGesture.value = false
    pinchStartDist = 0
  }

  const wasPanning = isPanning.value
  const wasTransformingItem = Boolean(draggingItem.value || resizingItem.value || rotatingItem.value)

  // 状態解除を最優先で実行し、例外時でも「持ったまま離せない」状態にならないようにする
  isPanning.value = false
  draggingItem.value = null
  resizingItem.value = null
  rotatingItem.value = null
  isSelectingBox.value = false

  if (wasTransformingItem) {
    boardStore.recordHistory()
  }

  if (wasPanning || wasTransformingItem) {
    triggerAutoSave()
  }
}

function onWindowBlur() {
  isSpacePressed.value = false
  onPointerUp()
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
        triggerAutoSave()
        return
      case '=':
      case '+':
        e.preventDefault()
        stepZoom(1.2)
        return
      case '-':
        e.preventDefault()
        stepZoom(1 / 1.2)
        return
    }
    return
  }

  // 矢印キー: 選択アイテムの微調整移動（Shiftで10px）、未選択時はキャンバスのパン
  if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
    e.preventDefault()
    const movable = boardStore.selectedItems.filter(it => !it.is_locked)
    if (movable.length > 0) {
      const step = e.shiftKey ? 10 : 1
      const dx = e.key === 'ArrowLeft' ? -step : e.key === 'ArrowRight' ? step : 0
      const dy = e.key === 'ArrowUp' ? -step : e.key === 'ArrowDown' ? step : 0
      for (const item of movable) {
        boardStore.updateItem(item.id, {
          pos_x: item.pos_x + dx,
          pos_y: item.pos_y + dy,
        }, false)
      }
      boardStore.recordHistory()
      triggerAutoSave()
    } else {
      const panStep = e.shiftKey ? 120 : 40
      const dx = e.key === 'ArrowLeft' ? panStep : e.key === 'ArrowRight' ? -panStep : 0
      const dy = e.key === 'ArrowUp' ? panStep : e.key === 'ArrowDown' ? -panStep : 0
      panBy(dx, dy)
      triggerAutoSave()
    }
    return
  }

  // 単独キー
  switch (e.key) {
    case '+':
    case '=':
      e.preventDefault()
      stepZoom(1.2)
      break
    case '-':
      e.preventDefault()
      stepZoom(1 / 1.2)
      break
    case '[':
      if (boardStore.selectedItemIds.length) {
        e.preventDefault()
        boardStore.sendToBack()
        triggerAutoSave()
      }
      break
    case ']':
      if (boardStore.selectedItemIds.length) {
        e.preventDefault()
        boardStore.bringToFront()
        triggerAutoSave()
      }
      break
    case 'h': case 'H':
      e.preventDefault()
      boardStore.flipHorizontal()
      triggerAutoSave()
      break
    case 'v': case 'V':
      e.preventDefault()
      boardStore.flipVertical()
      triggerAutoSave()
      break
    case 'g': case 'G':
      e.preventDefault()
      boardStore.toggleGrayscale()
      triggerAutoSave()
      break
    case 'r': case 'R':
      e.preventDefault()
      for (const item of boardStore.selectedItems) {
        boardStore.updateItem(item.id, { rotation: (item.rotation + 90) % 360 })
      }
      triggerAutoSave()
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

function openActiveItemMenu(evt: MouseEvent) {
  const item = boardStore.activeItem || boardStore.selectedItems[0]
  if (!item) return
  const target = evt.currentTarget as HTMLElement | null
  const rect = target?.getBoundingClientRect()
  const x = rect ? rect.left : evt.clientX
  const y = rect ? rect.bottom + 8 : evt.clientY
  menuState.value = { item, x, y }
}

function toggleLockSelected() {
  const allLocked = boardStore.selectedItems.every(it => it.is_locked)
  for (const item of boardStore.selectedItems) {
    boardStore.updateItem(item.id, { is_locked: !allLocked }, false)
  }
  boardStore.recordHistory()
  triggerAutoSave()
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
    triggerAutoSave()
  }
}

function focusItem(item: CanvasItem) {
  if (!containerRef.value) return
  boardStore.selectItem(item.id)
  fitToItems([item], containerRef.value.getBoundingClientRect(), 96)
  triggerAutoSave()
}

function stepZoom(factor: number) {
  if (!containerRef.value) return
  const rect = containerRef.value.getBoundingClientRect()
  zoomAt(rect.left + rect.width / 2, rect.top + rect.height / 2, rect, factor)
  triggerAutoSave()
}

function handleResetZoom() {
  if (!containerRef.value) return
  resetView(containerRef.value.getBoundingClientRect())
  triggerAutoSave()
}

defineExpose({ fitView, resetView, focusItem })

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
  window.addEventListener('blur', onWindowBlur)

  // 初期ロード後に自動で全体表示
  initialFitTimer = setTimeout(() => {
    if (boardStore.items.length) fitView()
    else syncViewportCenter()
  }, 350)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('keyup', onKeyUp)
  window.removeEventListener('paste', onPaste)
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', onPointerUp)
  window.removeEventListener('blur', onWindowBlur)
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
        @focus-item="focusItem"
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
      @changed="triggerAutoSave"
      @focus-item="(it) => { focusItem(it); menuState = null }"
      @open-insight="() => {
        if (menuState) emit('open-insight', menuState.item)
        menuState = null
      }"
    />

    <!-- 選択中アイテムの固定操作バー（回転やズームに影響されず常に押しやすい画面上部バー） -->
    <div
      v-if="boardStore.selectedItems.length > 0"
      class="absolute top-14 md:top-3 left-1/2 -translate-x-1/2 w-max max-w-[calc(100%-1rem)] z-20 pointer-events-auto overflow-x-auto no-scrollbar animate-fade-in whitespace-nowrap"
      @pointerdown.stop
    >
      <div class="floating-bar px-2 py-1.5 rounded-2xl flex items-center gap-1 shadow-pop whitespace-nowrap">
        <span class="px-2 py-0.5 text-[11px] font-bold text-ink truncate max-w-[110px] sm:max-w-[160px] shrink-0">
          {{ boardStore.selectedItems.length === 1
            ? (boardStore.activeItem?.caption || boardStore.activeItem?.media?.title || '選択中の資料')
            : `${boardStore.selectedItems.length}件を選択中` }}
        </span>

        <div class="h-4 w-px bg-canvas-border mx-0.5 shrink-0" />

        <button
          v-if="boardStore.activeItem"
          type="button"
          class="px-2.5 py-1 rounded-xl text-xs font-bold text-brand bg-brand-soft hover:bg-brand hover:text-brand-fg transition-colors flex items-center gap-1 shrink-0 whitespace-nowrap"
          title="AI 解析を開く [I]"
          @click="emit('open-insight', boardStore.activeItem)"
        >
          <Sparkles class="w-3.5 h-3.5 shrink-0" />
          <span class="hidden sm:inline whitespace-nowrap">AI解析</span>
        </button>

        <button
          v-if="boardStore.activeItem"
          type="button"
          class="p-1.5 rounded-xl text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors shrink-0"
          title="この資料にズームフォーカス"
          aria-label="この資料にズームフォーカス"
          @click="focusItem(boardStore.activeItem)"
        >
          <Maximize2 class="w-3.5 h-3.5" />
        </button>

        <button
          type="button"
          class="p-1.5 rounded-xl transition-colors shrink-0"
          :class="boardStore.activeItem?.is_flipped_h ? 'text-brand bg-brand-soft' : 'text-ink-muted hover:text-ink hover:bg-canvas-hover'"
          title="左右反転 [H]"
          aria-label="左右反転"
          @click="boardStore.flipHorizontal(); triggerAutoSave()"
        >
          <FlipHorizontal class="w-3.5 h-3.5" />
        </button>

        <button
          type="button"
          class="p-1.5 rounded-xl transition-colors shrink-0"
          :class="boardStore.activeItem?.is_flipped_v ? 'text-brand bg-brand-soft' : 'text-ink-muted hover:text-ink hover:bg-canvas-hover'"
          title="上下反転 [V]"
          aria-label="上下反転"
          @click="boardStore.flipVertical(); triggerAutoSave()"
        >
          <FlipVertical class="w-3.5 h-3.5" />
        </button>

        <button
          type="button"
          class="p-1.5 rounded-xl transition-colors shrink-0"
          :class="boardStore.activeItem?.is_grayscale ? 'text-brand bg-brand-soft' : 'text-ink-muted hover:text-ink hover:bg-canvas-hover'"
          title="グレースケール [G]"
          aria-label="グレースケール"
          @click="boardStore.toggleGrayscale(); triggerAutoSave()"
        >
          <SunMoon class="w-3.5 h-3.5" />
        </button>

        <button
          type="button"
          class="p-1.5 rounded-xl text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors shrink-0"
          title="90°回転 [R]"
          aria-label="90度回転"
          @click="boardStore.rotateSelection(90); triggerAutoSave()"
        >
          <RotateCw class="w-3.5 h-3.5" />
        </button>

        <button
          type="button"
          class="p-1.5 rounded-xl text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors shrink-0"
          title="前面へ移動"
          aria-label="前面へ移動"
          @click="boardStore.bringToFront(); triggerAutoSave()"
        >
          <ChevronUp class="w-3.5 h-3.5" />
        </button>

        <button
          type="button"
          class="p-1.5 rounded-xl text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors shrink-0"
          title="背面へ移動"
          aria-label="背面へ移動"
          @click="boardStore.sendToBack(); triggerAutoSave()"
        >
          <ChevronDown class="w-3.5 h-3.5" />
        </button>

        <button
          type="button"
          class="p-1.5 rounded-xl transition-colors shrink-0"
          :class="boardStore.selectedItems.every(i => i.is_locked) ? 'text-warn bg-warn/15' : 'text-ink-muted hover:text-ink hover:bg-canvas-hover'"
          title="位置とサイズを固定 / 解除"
          aria-label="ロック切替"
          @click="toggleLockSelected"
        >
          <component :is="boardStore.selectedItems.every(i => i.is_locked) ? Lock : Unlock" class="w-3.5 h-3.5" />
        </button>

        <button
          v-if="boardStore.activeItem"
          type="button"
          class="p-1.5 rounded-xl text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors shrink-0"
          title="メモ・不透明度・詳細メニュー"
          aria-label="詳細メニュー"
          @click="openActiveItemMenu"
        >
          <MoreHorizontal class="w-3.5 h-3.5" />
        </button>

        <button
          type="button"
          class="p-1.5 rounded-xl text-danger hover:bg-danger-soft transition-colors shrink-0"
          title="削除 [Delete]"
          aria-label="削除"
          @click="boardStore.deleteSelected()"
        >
          <Trash2 class="w-3.5 h-3.5" />
        </button>

        <div class="h-4 w-px bg-canvas-border mx-0.5 shrink-0" />

        <button
          type="button"
          class="p-1.5 rounded-xl text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors shrink-0"
          title="選択解除 [Esc]"
          aria-label="選択解除"
          @click="boardStore.clearSelection()"
        >
          <X class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>

    <!-- 空の状態（1クリックでブックマークブラウザやPixiv取り込みを開けるクイックスタート付き） -->
    <div
      v-if="!boardStore.items.length"
      class="absolute inset-0 flex items-center justify-center pointer-events-none p-6"
    >
      <div class="pointer-events-auto text-center max-w-md p-6 rounded-2xl bg-canvas-panel/90 border border-canvas-border shadow-card space-y-4">
        <div class="w-11 h-11 rounded-2xl bg-brand-soft text-brand flex items-center justify-center mx-auto">
          <Bookmark class="w-5 h-5" />
        </div>
        <div class="space-y-1.5">
          <p class="text-sm font-bold text-ink">キャンバスに資料を配置しましょう</p>
          <p class="text-xs text-ink-muted leading-relaxed">
            ブックマークブラウザから保存済み資料を1クリックで配置したり、画像をドラッグ＆ドロップして自由に並べられます。
          </p>
        </div>
        <div class="flex flex-wrap items-center justify-center gap-2">
          <button
            type="button"
            class="px-4 py-2 rounded-xl bg-brand hover:bg-brand-hover text-brand-fg text-xs font-bold transition-colors flex items-center gap-1.5"
            @click="boardStore.isBrowserOpen = true"
          >
            <Bookmark class="w-3.5 h-3.5" />
            <span>ブックマークから配置</span>
          </button>
          <button
            type="button"
            class="px-3.5 py-2 rounded-xl bg-pixiv hover:bg-pixiv-hover text-white text-xs font-bold transition-colors flex items-center gap-1.5"
            @click="emit('open-pixiv')"
          >
            <Compass class="w-3.5 h-3.5" />
            <span>pixivから探す</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 選択中アイテムのカラーチップバー（下部ツールバーと重ならないよう上に配置） -->
    <div
      v-if="activePalette.length > 0"
      class="absolute bottom-16 sm:bottom-20 left-1/2 -translate-x-1/2 w-max max-w-[calc(100%-1.5rem)] z-20 pointer-events-auto overflow-x-auto no-scrollbar animate-slide-up whitespace-nowrap"
    >
      <ColorPaletteBar :palette="activePalette" :title="boardStore.activeItem?.caption" />
    </div>

    <!-- ズーム操作 / ホイールモード（モバイルでは右上に配置して下部ツールバーとの重なりを防ぐ） -->
    <div class="absolute top-3 right-3 md:top-auto md:bottom-6 md:right-6 flex items-center gap-2 z-10 select-none" role="group" aria-label="ズームとスクロール操作">
      <button
        type="button"
        class="hidden md:inline-flex floating-bar px-2.5 py-1 rounded-full text-xs font-mono text-ink-muted hover:text-ink transition-colors"
        :title="wheelMode === 'scroll' ? 'ホイール/トラックパッド: パン。クリックでズームに切替' : 'ホイール: ズーム。クリックでパンに切替'"
        :aria-label="`ホイールモード切り替え（現在: ${wheelMode === 'scroll' ? 'パン' : 'ズーム'}）`"
        :aria-pressed="wheelMode === 'zoom'"
        @click="wheelMode = wheelMode === 'scroll' ? 'zoom' : 'scroll'"
      >
        {{ wheelMode === 'scroll' ? 'Pan' : 'Zoom' }}
      </button>

      <div class="floating-bar px-1 py-0.5 rounded-full flex items-center gap-0.5 text-xs font-mono text-ink-muted">
        <button
          type="button"
          class="w-6 h-6 rounded-full hover:bg-canvas-hover hover:text-ink transition-colors flex items-center justify-center font-bold"
          title="ズームアウト (-)"
          aria-label="ズームアウト"
          @click="stepZoom(1 / 1.2)"
        >
          −
        </button>
        <button
          type="button"
          class="px-1.5 py-0.5 rounded hover:bg-canvas-hover hover:text-ink transition-colors min-w-[44px] text-center"
          title="クリックで100%にリセット (Cmd+0)"
          aria-label="ズーム倍率を100%にリセット"
          @click="handleResetZoom"
        >
          {{ Math.round(zoom * 100) }}%
        </button>
        <button
          type="button"
          class="w-6 h-6 rounded-full hover:bg-canvas-hover hover:text-ink transition-colors flex items-center justify-center font-bold"
          title="ズームイン (+)"
          aria-label="ズームイン"
          @click="stepZoom(1.2)"
        >
          +
        </button>
      </div>
    </div>
  </div>
</template>
