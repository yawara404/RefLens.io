<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'

// Tailwind とテーマトークンは nuxt.config.ts の css 配列で読み込む
// （srcDir: '.' の環境で二重登録すると module script としてCSSが読まれ、
//   "Expected a JavaScript module but got text/css" で起動しなくなるため）
import { themeInitScript, useTheme } from '~/composables/useTheme'
import { useHelpStore } from '~/stores/helpStore'
import ToastHost from '~/components/ui/ToastHost.vue'
import KeyboardHelpModal from '~/components/ui/KeyboardHelpModal.vue'
import PixivConnectDialog from '~/components/panel/PixivConnectDialog.vue'

const { init } = useTheme()
const helpStore = useHelpStore()

// テーマの初回適用（CSS 反映前のちらつき = FOUC を防ぐ）
useHead({
  script: [{ innerHTML: themeInitScript, tagPosition: 'head' }],
})

// `?` / F1 でショートカット一覧を表示（入力欄にフォーカス中は無効）
function onGlobalKey(e: KeyboardEvent) {
  if (helpStore.isOpen) {
    // 開いている間は Esc で閉じるだけ
    return
  }

  const target = e.target as HTMLElement | null
  if (target) {
    const tag = target.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
    if (target.isContentEditable) return
  }

  if (e.key === '?' || (e.key === '/' && e.shiftKey)) {
    e.preventDefault()
    helpStore.open()
  } else if (e.key === 'F1') {
    e.preventDefault()
    helpStore.open()
  }
}

onMounted(() => {
  init()
  window.addEventListener('keydown', onGlobalKey)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onGlobalKey)
})
</script>

<template>
  <div class="min-h-screen bg-canvas-bg text-ink antialiased">
    <NuxtRouteAnnouncer />
    <NuxtPage />

    <ToastHost />
    <KeyboardHelpModal />
    <PixivConnectDialog />
  </div>
</template>
