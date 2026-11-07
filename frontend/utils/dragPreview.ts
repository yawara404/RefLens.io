/** 縦長・横長の画像も、縦横比を保ってプレビュー枠内に収める。 */
export function fitDragPreview(width: number, height: number, maxWidth = 160, maxHeight = 160) {
  const valid = Number.isFinite(width) && width > 0 && Number.isFinite(height) && height > 0
  const sourceWidth = valid ? width : maxWidth
  const sourceHeight = valid ? height : maxHeight
  const scale = Math.min(1, maxWidth / sourceWidth, maxHeight / sourceHeight)
  return {
    width: Math.max(1, Math.round(sourceWidth * scale)),
    height: Math.max(1, Math.round(sourceHeight * scale)),
  }
}

/** 原寸の Image を渡さず、読み込み済みサムネイルから小さなドラッグ画像を作る。 */
export function setReferenceDragPreview(event: DragEvent) {
  if (!event.dataTransfer) return
  const card = event.currentTarget as HTMLElement | null
  const image = card?.querySelector<HTMLImageElement>('img')
  const ready = image?.complete && image.naturalWidth > 0
  const size = fitDragPreview(ready ? image.naturalWidth : 160, ready ? image.naturalHeight : 160)
  const preview = document.createElement('canvas')
  preview.width = size.width
  preview.height = size.height
  const context = preview.getContext('2d')
  if (!context) return
  context.fillStyle = '#eef2ff'
  context.fillRect(0, 0, size.width, size.height)
  if (ready) {
    context.drawImage(image, 0, 0, size.width, size.height)
  }
  preview.setAttribute('aria-hidden', 'true')
  preview.style.cssText = 'position:fixed;left:-10000px;top:0;pointer-events:none;'
  document.body.appendChild(preview)
  try {
    event.dataTransfer.setDragImage(preview, Math.min(20, size.width / 2), Math.min(20, size.height / 2))
  } finally {
    // ブラウザが dragstart 終了時に画像を取得してから破棄する。
    setTimeout(() => preview.remove(), 0)
  }
}
