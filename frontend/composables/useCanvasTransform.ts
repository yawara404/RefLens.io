import { computed, ref } from 'vue'

export interface CanvasItemBounds {
  pos_x: number
  pos_y: number
  width: number
  height: number
}

/**
 * 無限キャンバスのパン / ズーム状態。
 * 座標はすべてワールド座標（キャンバス内の絶対座標）で扱う。
 */
export function useCanvasTransform(options?: { minZoom?: number; maxZoom?: number }) {
  const minZoom = options?.minZoom ?? 0.05
  const maxZoom = options?.maxZoom ?? 5.0

  const panX = ref(0)
  const panY = ref(0)
  const zoom = ref(1.0)

  const transformStyle = computed(() => ({
    transform: `translate3d(${panX.value}px, ${panY.value}px, 0px) scale(${zoom.value})`,
    transformOrigin: '0 0',
  }))

  /**
   * ビューポート座標 (clientX/clientY) → ワールド座標
   *
   * 注意: コンテナ基準の座標 (offsetX/Y) を渡しても正しい結果が返るよう、
   * rect の left/top を明示的に引いて正規化する。
   */
  function screenToWorld(clientX: number, clientY: number, containerRect: DOMRect) {
    return {
      x: (clientX - containerRect.left - panX.value) / zoom.value,
      y: (clientY - containerRect.top - panY.value) / zoom.value,
    }
  }

  /** ワールド座標 → ビューポート座標 */
  function worldToScreen(worldX: number, worldY: number, containerRect: DOMRect) {
    return {
      x: containerRect.left + panX.value + worldX * zoom.value,
      y: containerRect.top + panY.value + worldY * zoom.value,
    }
  }

  /** 指定位置を中心にズーム（ポインタ位置を固定したまま拡大縮小） */
  function zoomAt(clientX: number, clientY: number, containerRect: DOMRect, deltaZoom: number) {
    const mouseX = clientX - containerRect.left
    const mouseY = clientY - containerRect.top

    // パンDefsAnchor(変更前) を保持
    const prevZoom = zoom.value
    const nextZoom = Math.min(maxZoom, Math.max(minZoom, prevZoom * deltaZoom))
    if (nextZoom === prevZoom) return

    // マウス位置のワールド座標が同じスクリーン位置に留まるように再計算
    const worldX = (mouseX - panX.value) / prevZoom
    const worldY = (mouseY - panY.value) / prevZoom

    panX.value = mouseX - worldX * nextZoom
    panY.value = mouseY - worldY * nextZoom
    zoom.value = nextZoom
  }

  /** 相対移動 (Pan) */
  function panBy(dx: number, dy: number) {
    panX.value += dx
    panY.value += dy
  }

  /** すべてのアイテムを画面内に収める (Fit View) */
  function fitToItems(
    items: CanvasItemBounds[],
    containerRect: DOMRect,
    padding = 80
  ) {
    if (!items.length || containerRect.width === 0 || containerRect.height === 0) {
      panX.value = containerRect.width / 2
      panY.value = containerRect.height / 2
      zoom.value = 1.0
      return
    }

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
    for (const it of items) {
      minX = Math.min(minX, it.pos_x)
      minY = Math.min(minY, it.pos_y)
      maxX = Math.max(maxX, it.pos_x + it.width)
      maxY = Math.max(maxY, it.pos_y + it.height)
    }

    const boundingW = Math.max(1, maxX - minX)
    const boundingH = Math.max(1, maxY - minY)

    // 狭い画面では余白を小さくして尽可能広く表示する
    const pad = Math.min(padding, Math.min(containerRect.width, containerRect.height) * 0.15)
    const availableW = Math.max(1, containerRect.width - pad * 2)
    const availableH = Math.max(1, containerRect.height - pad * 2)

    const targetZoom = Math.min(
      1.5,
      Math.max(minZoom, Math.min(availableW / boundingW, availableH / boundingH))
    )

    zoom.value = targetZoom
    panX.value = containerRect.width / 2 - (minX + boundingW / 2) * targetZoom
    panY.value = containerRect.height / 2 - (minY + boundingH / 2) * targetZoom
  }

  /** 100%スケールにリセット */
  function resetView(containerRect?: DOMRect) {
    zoom.value = 1.0
    if (containerRect) {
      panX.value = containerRect.width / 4
      panY.value = containerRect.height / 4
    } else {
      panX.value = 100
      panY.value = 100
    }
  }

  return {
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
  }
}