<script setup lang="ts">
import { computed } from 'vue'
import { FolderOpen, Compass, Layers, Keyboard } from 'lucide-vue-next'
import { useBoardStore } from '~/stores/boardStore'
import { useHelpStore } from '~/stores/helpStore'
import ThemeToggle from '~/components/ui/ThemeToggle.vue'
import AuthButton from '~/components/ui/AuthButton.vue'
import SiteInfoMenu from '~/components/ui/SiteInfoMenu.vue'

const route = useRoute()
const boardStore = useBoardStore()
const helpStore = useHelpStore()

const NAV_ITEMS = [
  { key: 'manager', label: 'Manager', to: '/', icon: FolderOpen },
  { key: 'view', label: 'View (pixiv)', to: '/view', icon: Compass },
  { key: 'canvas', label: 'Canvas', to: '/canvas', icon: Layers },
] as const

/** 現在地: Canvas は /canvas と /board/:id の両方 */
const currentSection = computed<'manager' | 'view' | 'canvas'>(() => {
  const path = route.path
  if (path.startsWith('/view')) return 'view'
  if (path.startsWith('/board') || path.startsWith('/canvas')) return 'canvas'
  return 'manager'
})

const navItems = computed(() =>
  NAV_ITEMS.map(item => ({
    ...item,
    // Canvas はアクティブなボードがあればそのボードへ直接遷移させる
    to: item.key === 'canvas' && boardStore.currentBoard
      ? `/board/${boardStore.currentBoard.id}`
      : item.to,
  }))
)


</script>

<template>
  <header class="h-14 border-b border-canvas-border bg-canvas-panel px-3 md:px-5 grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 sticky top-0 z-40 select-none">
    <!-- 左: ロゴ -->
    <NuxtLink to="/" class="flex items-center gap-2.5 min-w-0 justify-self-start" aria-label="RefLens.io ホーム">
      <div class="w-8 h-8 rounded-xl bg-brand text-brand-fg flex items-center justify-center">
        <Compass class="w-4 h-4 stroke-[2.5]" />
      </div>
      <div class="hidden sm:flex flex-col leading-none">
        <span class="text-sm font-bold tracking-tight text-ink">
          RefLens<span class="text-pixiv">.io</span>
        </span>
        <span class="text-[9px] text-ink-subtle font-mono mt-0.5 hidden sm:block">
          Raindrop x pixiv x PureRef
        </span>
      </div>
    </NuxtLink>

    <!-- 中央: 3構成ナビゲーション -->
    <nav class="grid grid-cols-3 gap-0.5 p-1 rounded-xl border border-canvas-border bg-canvas-card justify-self-center" aria-label="メインナビゲーション">
      <NuxtLink v-for="item in navItems" :key="item.to" :to="item.to" class="w-10 sm:w-28 flex items-center justify-center gap-1.5 px-1 sm:px-2 py-1.5 rounded-lg text-xs font-semibold transition-colors whitespace-nowrap" :class="currentSection === item.key
        ? 'bg-brand text-brand-fg'
        : 'text-ink-muted hover:text-ink hover:bg-canvas-hover'" :aria-current="currentSection === item.key ? 'page' : undefined">
        <component :is="item.icon" class="w-3.5 h-3.5" />
        <span class="hidden sm:inline">{{ item.label }}</span>
      </NuxtLink>
    </nav>

    <!-- 右: アクション -->
    <div class="flex items-center gap-1 sm:gap-2 justify-self-end min-w-0">
      <AuthButton />

      <button type="button" class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors" title="キーボードショートカット（?）" aria-label="キーボードショートカット" @click="helpStore.toggle()">
        <Keyboard class="w-4 h-4" />
      </button>

      <ThemeToggle />
      <SiteInfoMenu />
    </div>
  </header>
</template>
