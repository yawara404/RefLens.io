<script setup lang="ts">
import { computed } from 'vue'
import { FolderOpen, Compass, Layers, HelpCircle } from 'lucide-vue-next'
import { useBoardStore } from '~/stores/boardStore'
import { useMobileNav } from '~/composables/useMobileNav'

withDefaults(defineProps<{
  showSiteLinks?: boolean
}>(), {
  showSiteLinks: false,
})

const emit = defineEmits<{
  (e: 'navigate'): void
}>()

const route = useRoute()
const boardStore = useBoardStore()
const mobileNav = useMobileNav()

const NAV_ITEMS = [
  { key: 'manager', label: 'Manager', to: '/', icon: FolderOpen },
  { key: 'view', label: 'View (pixiv)', to: '/view', icon: Compass },
  { key: 'canvas', label: 'Canvas', to: '/canvas', icon: Layers },
] as const

const currentSection = computed<'manager' | 'view' | 'canvas' | null>(() => {
  const path = route.path
  if (path === '/') return 'manager'
  if (path.startsWith('/view')) return 'view'
  if (path.startsWith('/board') || path.startsWith('/canvas')) return 'canvas'
  return null
})

const navItems = computed(() =>
  NAV_ITEMS.map(item => ({
    ...item,
    to: item.key === 'canvas' && boardStore.currentBoard
      ? `/board/${boardStore.currentBoard.id}`
      : item.to,
  }))
)

function handleSelect() {
  mobileNav.close()
  emit('navigate')
}

function openSiteInfoModal() {
  handleSelect()
  window.dispatchEvent(new CustomEvent('reflens:open-site-info', { detail: 'about' }))
}
</script>

<template>
  <div class="space-y-1.5">
    <nav class="space-y-1" aria-label="メインナビゲーション">
      <NuxtLink
        v-for="item in navItems"
        :key="item.key"
        :to="item.to"
        class="w-full flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm transition-colors"
        :class="currentSection === item.key
          ? 'text-brand font-bold bg-brand-soft ring-1 ring-inset ring-brand/30'
          : 'text-ink hover:bg-canvas-hover font-semibold'"
        :aria-current="currentSection === item.key ? 'page' : undefined"
        @click="handleSelect"
      >
        <component
          :is="item.icon"
          class="w-4 h-4 shrink-0"
          :class="currentSection === item.key ? 'text-brand' : 'text-ink-muted'"
        />
        <span class="truncate">{{ item.label }}</span>
      </NuxtLink>
    </nav>

    <!-- サイト情報3項目（概要・プライバシー・利用規約）を1ボタンからポップアップモーダルで表示 -->
    <button
      v-if="showSiteLinks"
      type="button"
      class="w-full flex items-center justify-between gap-2 rounded-xl px-3.5 py-2.5 text-xs font-bold text-ink bg-canvas-bg hover:bg-canvas-hover border border-canvas-border-strong transition-colors"
      @click="openSiteInfoModal"
    >
      <span class="flex items-center gap-2.5">
        <HelpCircle class="w-4 h-4 text-brand shrink-0" />
        <span>サイト情報・利用規約</span>
      </span>
      <span class="text-[10px] font-mono font-semibold text-ink-muted">詳細</span>
    </button>
  </div>
</template>
