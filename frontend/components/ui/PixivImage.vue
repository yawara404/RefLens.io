<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import { useAuthStore } from '~/stores/authStore'

const props = defineProps<{ src: string; alt?: string }>()
const auth = useAuthStore()
const displayedSrc = ref('')
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
  <img :src="displayedSrc || undefined" :alt="alt || ''">
</template>
