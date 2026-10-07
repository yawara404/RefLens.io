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
        if (item.type.indexOf('image') !== -1) {
          const file = item.getAsFile()
          if (file) files.push(file)
        }
      }
    } else if (dataTransfer.files) {
      for (let i = 0; i < dataTransfer.files.length; i++) {
        const file = dataTransfer.files[i]
        if (file.type.indexOf('image') !== -1) {
          files.push(file)
        }
      }
    }
    return files
  }

  /**
   * 画像URLをクリップボードにコピー
   */
  async function copyToClipboard(text: string): Promise<boolean> {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      return false
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
