<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import { useAuthStore } from '~/stores/authStore'

const props = defineProps<{ src: string; alt?: string }>()
const auth = useAuthStore()
const displayedSrc = ref('')
/** 読み込み中はプレースホルダー、失敗時は代替アイコンを出す（真っ白な枠を減らす） */
const loadState = ref<'loading' | 'ready' | 'error'>('loading')
let controller: AbortController | null = null
let objectUrl: string | null = null
let requestId = 0

function release() {
  controller?.abort()
  controller = null
  if (objectUrl) URL.revokeObjectURL(objectUrl)
  objectUrl = null
}

watch(() => [props.src, auth.token], async () => {
  if (import.meta.server) return
  const currentRequest = ++requestId
  release()
  displayedSrc.value = ''
  loadState.value = 'loading'

  if (!props.src) {
    loadState.value = 'error'
    return
  }

  if (!props.src.includes('/pixiv/image?')) {
    displayedSrc.value = props.src
    return
  }

  // <img> cannot attach the bearer token required by the Pixiv image proxy.
  // Fetch the image as a blob, then give the browser a local object URL.
  controller = new AbortController()
  try {
    const response = await fetch(props.src, {
      headers: auth.authHeaders(),
      signal: controller.signal,
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const blob = await response.blob()
    if (!blob.type.startsWith('image/')) throw new Error('Invalid image response')
    if (currentRequest !== requestId) return
    objectUrl = URL.createObjectURL(blob)
    displayedSrc.value = objectUrl
  } catch (error) {
    if (currentRequest === requestId && !(error instanceof DOMException && error.name === 'AbortError')) {
      loadState.value = 'error'
      console.warn('Pixiv image could not be loaded', error)
    }
  }
}, { immediate: true })

onUnmounted(() => {
  requestId++
  release()
})
</script>

<template>
  <img
    :src="displayedSrc || undefined"
    :alt="alt || ''"
    decoding="async"
    :class="{
      'pixiv-image-loading': loadState === 'loading',
      'pixiv-image-error': loadState === 'error',
    }"
    @load="loadState = 'ready'"
    @error="loadState = 'error'"
  >
</template>

<style scoped>
/* 読み込み中: 枠が真っ白/真っ黒のまま待たされないよう、淡いシマーを流す */
.pixiv-image-loading {
  background-color: var(--surface-hover);
  background-image: linear-gradient(
    100deg,
    var(--surface-card) 25%,
    var(--surface-hover) 45%,
    var(--surface-card) 65%
  );
  background-size: 220% 100%;
  animation: pixiv-image-shimmer 1.4s ease-in-out infinite;
}

/* 失敗時: 破れた画像アイコンを背景に置く（alt テキストはそのまま読ませる） */
.pixiv-image-error {
  background-color: var(--surface-hover);
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'><rect x='3' y='3' width='18' height='18' rx='2'/><path d='M3 16l5-5 4 4 3-3 6 6'/><circle cx='9' cy='9' r='1.5'/></svg>");
  background-repeat: no-repeat;
  background-position: center;
  background-size: 22px 22px;
}

@keyframes pixiv-image-shimmer {
  from { background-position: 120% 0; }
  to { background-position: -120% 0; }
}
</style>
