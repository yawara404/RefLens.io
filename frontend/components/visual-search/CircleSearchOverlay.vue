<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { Sparkles, X, Loader2 } from 'lucide-vue-next'
import { useVisualSearch } from '~/composables/useVisualSearch'

const {
  isCircleSearchActive,
  isSearching,
  cancelCircleSearch,
  searchCrop,
} = useVisualSearch()

const isDragging = ref(false)
const startX = ref(0)
const startY = ref(0)
const currentX = ref(0)
const currentY = ref(0)

const boxStyle = computed(() => {
  const left = Math.min(startX.value, currentX.value)
  const top = Math.min(startY.value, currentY.value)
  const width = Math.abs(currentX.value - startX.value)
  const height = Math.abs(currentY.value - startY.value)

  return {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`,
  }
})

const boxDimensions = computed(() => {
  return {
    left: Math.min(startX.value, currentX.value),
    top: Math.min(startY.value, currentY.value),
    width: Math.abs(currentX.value - startX.value),
    height: Math.abs(currentY.value - startY.value),
  }
})

function onMouseDown(e: MouseEvent) {
  if (e.button !== 0) return
  isDragging.value = true
  startX.value = e.clientX
  startY.value = e.clientY
  currentX.value = e.clientX
  currentY.value = e.clientY
}

function onMouseMove(e: MouseEvent) {
  if (!isDragging.value) return
  currentX.value = e.clientX
  currentY.value = e.clientY
}

function onMouseUp() {
  if (!isDragging.value) return
  isDragging.value = false

  const box = boxDimensions.value
  if (box.width < 20 || box.height < 20) {
    // クリックだけの場合はキャンセルまたは無視
    return
  }

  executeCrop(box)
}

function onKeyDown(e: KeyboardEvent) {
  if (isCircleSearchActive.value && e.key === 'Escape') {
    cancelCircleSearch()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
})

/** 選択ボックス内の画像をクロップして Base64 に変換 */
function executeCrop(box: { left: number; top: number; width: number; height: number }) {
  const centerX = box.left + box.width / 2
  const centerY = box.top + box.height / 2

  // 選択ボックスの中心または四隅にある img 要素を探索
  const elements = [
    ...document.elementsFromPoint(centerX, centerY),
    ...document.elementsFromPoint(box.left + 5, box.top + 5),
    ...document.elementsFromPoint(box.left + box.width - 5, box.top + box.height - 5),
  ]

  let targetImg: HTMLImageElement | null = null
  for (const el of elements) {
    if (el instanceof HTMLImageElement && el.naturalWidth > 0) {
      targetImg = el
      break
    }
    const innerImg = el.querySelector('img')
    if (innerImg && innerImg.naturalWidth > 0) {
      targetImg = innerImg
      break
    }
  }

  if (!targetImg) {
    // 画面内に画像が見つからない場合は全画面から要素を探す
    const allImages = Array.from(document.querySelectorAll('img'))
    for (const img of allImages) {
      const rect = img.getBoundingClientRect()
      if (
        rect.left < box.left + box.width &&
        rect.right > box.left &&
        rect.top < box.top + box.height &&
        rect.bottom > box.top
      ) {
        targetImg = img
        break
      }
    }
  }

  if (!targetImg || targetImg.naturalWidth === 0) {
    cancelCircleSearch()
    return
  }

  try {
    const imgRect = targetImg.getBoundingClientRect()
    const scaleX = targetImg.naturalWidth / imgRect.width
    const scaleY = targetImg.naturalHeight / imgRect.height

    const cropX = Math.max(0, (box.left - imgRect.left) * scaleX)
    const cropY = Math.max(0, (box.top - imgRect.top) * scaleY)
    const cropW = Math.min(targetImg.naturalWidth - cropX, box.width * scaleX)
    const cropH = Math.min(targetImg.naturalHeight - cropY, box.height * scaleY)

    if (cropW <= 5 || cropH <= 5) {
      cancelCircleSearch()
      return
    }

    const canvas = document.createElement('canvas')
    canvas.width = Math.round(cropW)
    canvas.height = Math.round(cropH)
    const ctx = canvas.getContext('2d')

    if (!ctx) {
      cancelCircleSearch()
      return
    }

    ctx.drawImage(
      targetImg,
      cropX,
      cropY,
      cropW,
      cropH,
      0,
      0,
      canvas.width,
      canvas.height
    )

    const base64 = canvas.toDataURL('image/jpeg', 0.85)
    searchCrop(base64)
  } catch (err) {
    console.error('Failed to crop image on canvas:', err)
    cancelCircleSearch()
  }
}
</script>

<template>
  <div
    v-if="isCircleSearchActive"
    class="fixed inset-0 z-[999] select-none cursor-crosshair overflow-hidden circle-search-backdrop animate-fade-in"
    @mousedown="onMouseDown"
    @mousemove="onMouseMove"
    @mouseup="onMouseUp"
  >
    <!-- Galaxy AI 特有の虹色グラデーション発光外枠 -->
    <div class="absolute inset-0 pointer-events-none circle-search-border" />

    <!-- 上部ガイダンスフローティングバー -->
    <div class="absolute top-6 left-1/2 -translate-x-1/2 pointer-events-auto flex items-center gap-2.5 px-4 py-2 rounded-full bg-slate-900/90 text-white backdrop-blur-md shadow-2xl border border-white/20 animate-bounce-subtle">
      <div class="w-5 h-5 rounded-full bg-gradient-to-tr from-cyan-400 via-indigo-400 to-pink-500 flex items-center justify-center animate-spin-slow">
        <Sparkles class="w-3 h-3 text-white" />
      </div>
      <div class="flex items-center gap-1.5 text-xs font-bold tracking-wide">
        <span class="bg-gradient-to-r from-cyan-300 via-indigo-200 to-pink-300 bg-clip-text text-transparent">
          Galaxy AI かこって検索
        </span>
        <span class="text-white/70 font-normal">| 調べたい部分をドラッグで囲んでください</span>
      </div>
      <button
        type="button"
        class="ml-2 p-1 rounded-full hover:bg-white/20 text-white/80 hover:text-white transition-colors"
        title="キャンセル (Esc)"
        @click.stop="cancelCircleSearch"
      >
        <X class="w-3.5 h-3.5" />
      </button>
    </div>

    <!-- ドラッグ中の選択ボックス（Galaxy AI風の光彩枠） -->
    <div
      v-if="isDragging && (boxDimensions.width > 5 || boxDimensions.height > 5)"
      class="absolute pointer-events-none circle-search-selection rounded-xl"
      :style="boxStyle"
    >
      <!-- 四隅のグローインジケータ -->
      <div class="absolute -top-1 -left-1 w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#22d3ee]" />
      <div class="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-pink-400 shadow-[0_0_8px_#f472b6]" />
      <div class="absolute -bottom-1 -left-1 w-2.5 h-2.5 rounded-full bg-indigo-400 shadow-[0_0_8px_#818cf8]" />
      <div class="absolute -bottom-1 -right-1 w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#22d3ee]" />
    </div>
  </div>
</template>

<style scoped>
.circle-search-backdrop {
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(2px);
}

.circle-search-border {
  border: 4px solid transparent;
  background:
    linear-gradient(rgba(15, 23, 42, 0), rgba(15, 23, 42, 0)) padding-box,
    linear-gradient(135deg, #06b6d4, #6366f1, #ec4899, #3b82f6) border-box;
  animation: border-glow 3s linear infinite alternate;
}

.circle-search-selection {
  border: 2px dashed #ffffff;
  background: rgba(99, 102, 241, 0.15);
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.4),
    0 0 25px rgba(99, 102, 241, 0.6),
    inset 0 0 15px rgba(236, 72, 153, 0.2);
}

@keyframes border-glow {
  0% {
    filter: drop-shadow(0 0 8px rgba(6, 182, 212, 0.6));
  }
  50% {
    filter: drop-shadow(0 0 14px rgba(236, 72, 153, 0.8));
  }
  100% {
    filter: drop-shadow(0 0 8px rgba(99, 102, 241, 0.6));
  }
}

@keyframes spin-slow {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.animate-spin-slow {
  animation: spin-slow 8s linear infinite;
}
</style>
