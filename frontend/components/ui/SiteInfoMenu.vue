<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { MoreHorizontal, Info, Shield, FileText } from 'lucide-vue-next'

const route = useRoute()
const root = ref<HTMLElement | null>(null)
const isOpen = ref(false)

const links = [
  { to: '/about', label: 'このサイトについて', icon: Info },
  { to: '/privacy', label: 'プライバシーポリシー', icon: Shield },
  { to: '/terms', label: '利用上の注意', icon: FileText },
]

function close() { isOpen.value = false }

function onOutsideClick(event: MouseEvent) {
  if (root.value && !root.value.contains(event.target as Node)) close()
}

function onEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') close()
}

watch(isOpen, open => {
  if (open) {
    document.addEventListener('pointerdown', onOutsideClick)
    document.addEventListener('keydown', onEscape)
  } else {
    document.removeEventListener('pointerdown', onOutsideClick)
    document.removeEventListener('keydown', onEscape)
  }
})

watch(() => route.fullPath, close)

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onOutsideClick)
  document.removeEventListener('keydown', onEscape)
})
</script>

<template>
  <div ref="root" class="relative shrink-0">
    <button
      type="button"
      class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
      aria-label="サイト情報メニュー"
      aria-haspopup="menu"
      :aria-expanded="isOpen"
      @click="isOpen = !isOpen"
    >
      <MoreHorizontal class="w-4 h-4" />
    </button>

    <nav
      v-if="isOpen"
      class="absolute right-0 top-full mt-2 w-56 max-w-[calc(100vw-1rem)] rounded-xl border border-canvas-border bg-canvas-panel p-1.5 shadow-pop z-50"
      aria-label="サイト情報"
    >
      <NuxtLink
        v-for="link in links"
        :key="link.to"
        :to="link.to"
        class="flex items-center gap-2 rounded-lg px-3 py-2 text-xs text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
        :aria-current="route.path === link.to ? 'page' : undefined"
        @click="close"
      >
        <component :is="link.icon" class="w-4 h-4 shrink-0" />
        {{ link.label }}
      </NuxtLink>
      <div class="mt-1 border-t border-canvas-border px-3 py-2 text-[10px] text-ink-subtle">RefLens.io</div>
    </nav>
  </div>
</template>
