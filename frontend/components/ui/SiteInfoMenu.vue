<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { MoreVertical, HelpCircle, Info, Shield, FileText, Keyboard, ExternalLink } from 'lucide-vue-next'
import { useHelpStore } from '~/stores/helpStore'

const helpStore = useHelpStore()
const isOpen = ref(false)
const menuRef = ref<HTMLElement | null>(null)

function close() {
  isOpen.value = false
}

function toggle() {
  isOpen.value = !isOpen.value
}

function onEscape(event: KeyboardEvent) {
  if (event.key === 'Escape' && isOpen.value) close()
}

function onClickOutside(event: MouseEvent) {
  if (!isOpen.value) return
  const target = event.target as Node | null
  if (menuRef.value && !menuRef.value.contains(target)) {
    close()
  }
}

function openShortcuts() {
  close()
  helpStore.toggle()
}

onMounted(() => {
  window.addEventListener('keydown', onEscape)
  document.addEventListener('click', onClickOutside)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onEscape)
  document.removeEventListener('click', onClickOutside)
})
</script>

<template>
  <div ref="menuRef" class="relative shrink-0 select-none">
    <!-- 三点リーダーボタン（ピクセルデザイン・レトロ枠） -->
    <button
      type="button"
      class="p-2 rounded-xl text-ink hover:text-brand hover:bg-canvas-hover border border-canvas-border-strong transition-colors flex items-center justify-center"
      :class="isOpen ? 'bg-canvas-hover border-brand text-brand ring-2 ring-brand/20' : ''"
      title="その他メニュー・ヘルプ"
      aria-label="その他メニュー・ヘルプを開く"
      aria-haspopup="menu"
      :aria-expanded="isOpen"
      @click="toggle"
    >
      <MoreVertical class="w-4 h-4" />
    </button>

    <!-- ドロップダウンポップオーバーメニュー（モーダルではなくTunedropのようにページ遷移） -->
    <div
      v-if="isOpen"
      class="absolute right-0 top-full mt-1.5 w-60 rounded-2xl border border-canvas-border-strong bg-canvas-panel shadow-pop p-1.5 flex flex-col gap-0.5 text-xs z-50 animate-scale-in"
      role="menu"
      aria-label="サイト設定・ヘルプメニュー"
    >
      <div class="px-3 py-1.5 border-b border-canvas-border text-[10px] font-mono font-bold tracking-wider text-ink-subtle uppercase">
        RefLens.io メニュー
      </div>

      <NuxtLink
        to="/help"
        class="flex items-center gap-2.5 px-3 py-2 rounded-xl font-bold text-ink hover:bg-brand-soft hover:text-brand transition-colors"
        role="menuitem"
        @click="close"
      >
        <HelpCircle class="w-4 h-4 text-brand shrink-0" />
        <span class="truncate">使い方・操作ガイド</span>
      </NuxtLink>

      <button
        type="button"
        class="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl font-semibold text-ink hover:bg-canvas-hover transition-colors text-left"
        role="menuitem"
        @click="openShortcuts"
      >
        <Keyboard class="w-4 h-4 text-ink-muted shrink-0" />
        <span class="truncate">ショートカット（?）</span>
      </button>

      <div class="h-px bg-canvas-border mx-1 my-1" />

      <NuxtLink
        to="/about"
        class="flex items-center gap-2.5 px-3 py-2 rounded-xl font-semibold text-ink hover:bg-canvas-hover transition-colors"
        role="menuitem"
        @click="close"
      >
        <Info class="w-4 h-4 text-ink-muted shrink-0" />
        <span class="truncate">このサイトについて</span>
      </NuxtLink>

      <NuxtLink
        to="/privacy"
        class="flex items-center gap-2.5 px-3 py-2 rounded-xl font-semibold text-ink hover:bg-canvas-hover transition-colors"
        role="menuitem"
        @click="close"
      >
        <Shield class="w-4 h-4 text-ink-muted shrink-0" />
        <span class="truncate">プライバシーポリシー</span>
      </NuxtLink>

      <NuxtLink
        to="/terms"
        class="flex items-center gap-2.5 px-3 py-2 rounded-xl font-semibold text-ink hover:bg-canvas-hover transition-colors"
        role="menuitem"
        @click="close"
      >
        <FileText class="w-4 h-4 text-ink-muted shrink-0" />
        <span class="truncate">利用上の注意</span>
      </NuxtLink>
    </div>
  </div>
</template>
