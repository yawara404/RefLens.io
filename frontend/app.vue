<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'

// Tailwind とテーマトークンは nuxt.config.ts の css 配列で読み込む
// （srcDir: '.' の環境で二重登録すると module script としてCSSが読まれ、
//   "Expected a JavaScript module but got text/css" で起動しなくなるため）
import { themeInitScript, useTheme } from '~/composables/useTheme'
import { useHelpStore } from '~/stores/helpStore'
import { useMobileNav } from '~/composables/useMobileNav'
import ToastHost from '~/components/ui/ToastHost.vue'
import KeyboardHelpModal from '~/components/ui/KeyboardHelpModal.vue'
import PixivConnectDialog from '~/components/panel/PixivConnectDialog.vue'

const { init } = useTheme()
const helpStore = useHelpStore()
const mobileNav = useMobileNav()

// テーマの初回適用（CSS 反映前のちらつき = FOUC を防ぐ）
useHead({
  script: [{ innerHTML: themeInitScript, tagPosition: 'head' }],
})

// `?` / F1 でショートカット一覧を表示、`/` で検索欄へフォーカス（入力欄にフォーカス中は無効）
function onGlobalKey(e: KeyboardEvent) {
  if (helpStore.isOpen) {
    // 開いている間は Esc で閉じるだけ
    return
  }

  if (e.key === 'Escape' && mobileNav.isOpen.value) {
    mobileNav.close()
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
  } else if (e.key === '/' && !e.shiftKey && !e.metaKey && !e.ctrlKey && !e.altKey) {
    if (document.querySelector('[aria-modal="true"]')) return
    const searchInputs = Array.from(
      document.querySelectorAll<HTMLInputElement>('main input[type="search"], header input[type="search"], aside input[type="search"]')
    )
    const visibleInput = searchInputs.find(el => el.offsetParent !== null)
    if (visibleInput) {
      e.preventDefault()
      visibleInput.focus()
      visibleInput.select()
    }
  }
}

function skipToMain() {
  const main = document.getElementById('main-content') || document.querySelector<HTMLElement>('main')
  if (main) {
    if (!main.hasAttribute('tabindex')) main.setAttribute('tabindex', '-1')
    main.focus({ preventScroll: false })
  }
}

/** 作品画像の右クリックコピー・ブラウザ外へのドラッグ持ち出しを抑止 */
function onProtectMediaContext(e: MouseEvent) {
  const target = e.target as HTMLElement | null
  if (target?.tagName === 'IMG') {
    e.preventDefault()
  }
}

function onProtectMediaDrag(e: DragEvent) {
  const target = e.target as HTMLElement | null
  if (target?.tagName === 'IMG') {
    e.preventDefault()
  }
}

onMounted(() => {
  init()
  window.addEventListener('keydown', onGlobalKey)
  window.addEventListener('contextmenu', onProtectMediaContext)
  window.addEventListener('dragstart', onProtectMediaDrag)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onGlobalKey)
  window.removeEventListener('contextmenu', onProtectMediaContext)
  window.removeEventListener('dragstart', onProtectMediaDrag)
})
</script>

<template>
  <div class="min-h-screen bg-canvas-bg text-ink antialiased">
    <a
      href="#main-content"
      class="skip-link"
      @click.prevent="skipToMain"
    >
      メインコンテンツへ移動
    </a>
    <NuxtRouteAnnouncer />
    <NuxtPage />

    <ToastHost />
    <KeyboardHelpModal />
    <PixivConnectDialog />
  </div>
</template>
