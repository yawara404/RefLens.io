import { ref } from 'vue'

export function useImageProcessor() {
  const isEyeDropperActive = ref(false)
  const pickedColor = ref<string | null>(null)

  /**
   * ブラウザのEyeDropper API または Canvas サンプリングによるカラーピッカー
   */
  async function pickColor(): Promise<string | null> {
    if (typeof window !== 'undefined' && 'EyeDropper' in window) {
      try {
        isEyeDropperActive.value = true
        // @ts-ignore - EyeDropper is a modern experimental API supported in Chromium/Edge/Safari
        const eyeDropper = new (window as any).EyeDropper()
        const result = await eyeDropper.open()
        pickedColor.value = result.sRGBHex
        return result.sRGBHex
      } catch (e) {
        // Cancelled or unsupported
        return null
      } finally {
        isEyeDropperActive.value = false
      }
    }
    return null
  }

  /**
   * クリップボードまたはDrag&Dropイベントから画像ファイルを取り出す
   */
  function extractImagesFromDataTransfer(dataTransfer: DataTransfer): File[] {
    const files: File[] = []
    if (dataTransfer.items) {
      for (let i = 0; i < dataTransfer.items.length; i++) {
        const item = dataTransfer.items[i]
        if (item.kind === 'file' && item.type.startsWith('image/')) {
          const file = item.getAsFile()
          if (file) files.push(file)
        }
      }
    }
    if (!files.length && dataTransfer.files) {
      for (let i = 0; i < dataTransfer.files.length; i++) {
        const file = dataTransfer.files[i]
        if (file.type.startsWith('image/')) {
          files.push(file)
        }
      }
    }
    return files
  }

  /**
   * テキストをクリップボードにコピー
   *
   * navigator.clipboard は https 以外や権限が無い環境で失敗するため、
   * 選択範囲 + execCommand のフォールバックも試す。
   */
  async function copyToClipboard(text: string): Promise<boolean> {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(text)
        return true
      } catch {
        /* フォールバックへ */
      }
    }

    if (typeof document === 'undefined') return false
    const previousFocus = document.activeElement as HTMLElement | null
    const textarea = document.createElement('textarea')
    try {
      textarea.value = text
      textarea.setAttribute('readonly', '')
      textarea.style.position = 'fixed'
      textarea.style.top = '-1000px'
      textarea.style.opacity = '0'
      // フォーカストラップがあるモーダル内でもコピーできるようにする。
      const host = previousFocus?.closest('[aria-modal="true"]') || document.body
      host.appendChild(textarea)
      textarea.select()
      return document.execCommand('copy')
    } catch {
      return false
    } finally {
      textarea.remove()
      if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true })
    }
  }

  return {
    isEyeDropperActive,
    pickedColor,
    pickColor,
    extractImagesFromDataTransfer,
    copyToClipboard
  }
}
