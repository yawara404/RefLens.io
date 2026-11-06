<script setup lang="ts">
import { computed, watch } from 'vue'
import { FolderOpen, Compass, Layers, Menu, X, Info, Shield, FileText, HelpCircle, Keyboard } from 'lucide-vue-next'
import { useBoardStore } from '~/stores/boardStore'
import { useHelpStore } from '~/stores/helpStore'
import { useMobileNav } from '~/composables/useMobileNav'
import ThemeToggle from '~/components/ui/ThemeToggle.vue'
import AuthButton from '~/components/ui/AuthButton.vue'
import MobileNavLinks from '~/components/ui/MobileNavLinks.vue'

const route = useRoute()
const boardStore = useBoardStore()
const helpStore = useHelpStore()
const mobileNav = useMobileNav()

const NAV_ITEMS = [
  { key: 'manager', label: 'Manager', to: '/', icon: FolderOpen },
  { key: 'view', label: 'View (pixiv)', to: '/view', icon: Compass },
  { key: 'canvas', label: 'Canvas', to: '/canvas', icon: Layers },
] as const

const SITE_LINKS = [
  { to: '/about', label: 'このサイトについて', icon: Info },
  { to: '/privacy', label: 'プライバシーポリシー', icon: Shield },
  { to: '/terms', label: '利用上の注意', icon: FileText },
] as const

/** 現在地: Canvas は /canvas と /board/:id の両方 */
const currentSection = computed<'manager' | 'view' | 'canvas'>(() => {
  const path = route.path
  if (path.startsWith('/view')) return 'view'
  if (path.startsWith('/board') || path.startsWith('/canvas')) return 'canvas'
  return 'manager'
})

/** ページ独自のサイドメニューを持たないページ（/board, /account, /about 等）ではヘッダー側でモバイルナビドロワーを描画 */
const hasStandaloneDrawer = computed(() => {
  const path = route.path
  return path !== '/' && !path.startsWith('/view')
})

function handleMobileToggle() {
  mobileNav.toggle()
  if (mobileNav.isOpen.value) {
    boardStore.isBrowserOpen = false
  }
}

const navItems = computed(() =>
  NAV_ITEMS.map(item => ({
    ...item,
    // Canvas はアクティブなボードがあればそのボードへ直接遷移させる
    to: item.key === 'canvas' && boardStore.currentBoard
      ? `/board/${boardStore.currentBoard.id}`
      : item.to,
  }))
)

watch(() => route.fullPath, () => {
  mobileNav.close()
})
</script>

<template>
  <header class="h-14 border-b border-canvas-border bg-canvas-panel px-3 md:px-5 flex md:grid md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center justify-between gap-2 sticky top-0 z-40 select-none">
    <!-- 左: ハンバーガーメニュー（モバイル）+ ロゴ -->
    <div class="flex items-center gap-2 min-w-0 justify-self-start">
      <button
        type="button"
        class="md:hidden p-1.5 -ml-1 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors shrink-0"
        :aria-expanded="mobileNav.isOpen.value"
        :aria-label="mobileNav.isOpen.value ? 'メニューを閉じる' : 'メニューを開く'"
        @click="handleMobileToggle"
      >
        <X v-if="mobileNav.isOpen.value" class="w-5 h-5" />
        <Menu v-else class="w-5 h-5" />
      </button>

      <NuxtLink to="/" class="flex items-center gap-2 min-w-0" aria-label="RefLens.io ホーム" @click="mobileNav.close()">
        <div class="w-8 h-8 rounded-xl bg-brand text-brand-fg flex items-center justify-center shrink-0">
          <Compass class="w-4 h-4 stroke-[2.5]" />
        </div>
        <div class="flex flex-col leading-none min-w-0">
          <span class="text-sm font-bold tracking-tight text-ink truncate">
            RefLens<span class="text-pixiv">.io</span>
          </span>
          <span class="text-[9px] text-ink-subtle font-mono mt-0.5 hidden sm:block">
            Raindrop x pixiv x PureRef
          </span>
        </div>
      </NuxtLink>
    </div>

    <!-- 中央: 3構成ナビゲーション（PC・タブレット横向きで表示、モバイルはハンバーガーメニュー内に格納） -->
    <nav class="hidden md:grid grid-cols-3 gap-0.5 p-1 rounded-xl border border-canvas-border-strong bg-canvas-card justify-self-center" aria-label="メインナビゲーション">
      <NuxtLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="w-28 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-bold transition-colors whitespace-nowrap"
        :class="currentSection === item.key
          ? 'bg-brand text-brand-fg shadow-sm'
          : 'text-ink hover:text-brand hover:bg-canvas-hover'"
        :aria-current="currentSection === item.key ? 'page' : undefined"
      >
        <component :is="item.icon" class="w-3.5 h-3.5 shrink-0" />
        <span>{{ item.label }}</span>
      </NuxtLink>
    </nav>

    <!-- 右: アクション（ショートカットモーダル + テーマ切替 + 一番右にヘルプ専用ページ） -->
    <div class="flex items-center gap-1.5 sm:gap-2 justify-self-end shrink-0">
      <AuthButton />

      <!-- キーボードショートカット一覧モーダル呼び出し -->
      <button
        type="button"
        class="hidden sm:inline-flex p-2 rounded-xl text-ink hover:text-brand hover:bg-canvas-hover border border-canvas-border-strong bg-canvas-card transition-colors select-none"
        title="キーボードショートカット（?）"
        aria-label="キーボードショートカット一覧を開く"
        @click="helpStore.toggle()"
      >
        <Keyboard class="w-4 h-4" />
      </button>

      <ThemeToggle />

      <!-- ヘルプ（Tunedrop風の専用ページへの遷移ボタン: 一番右に配置） -->
      <NuxtLink
        to="/help"
        class="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-xl text-xs font-bold transition-colors border select-none"
        :class="route.path === '/help'
          ? 'bg-brand text-brand-fg border-brand shadow-sm'
          : 'text-ink hover:text-brand hover:bg-canvas-hover border-canvas-border-strong bg-canvas-card'"
        title="使い方・操作ガイド（ヘルプ）"
        aria-label="使い方・操作ガイド（ヘルプ）"
      >
        <HelpCircle class="w-4 h-4 shrink-0" :class="route.path === '/help' ? 'text-white' : 'text-brand'" />
        <span class="hidden sm:inline">ヘルプ</span>
      </NuxtLink>
    </div>
  </header>

  <!-- サイドバーを持たないページ（/account, /about 等）向けのモバイルハンバーガードロワー -->
  <template v-if="hasStandaloneDrawer && mobileNav.isOpen.value">
    <aside
      class="md:hidden fixed inset-x-0 top-14 bottom-0 z-40 w-full h-[calc(100dvh-3.5rem)] bg-canvas-panel border-t border-canvas-border p-4 flex flex-col gap-3 overflow-y-auto overscroll-contain shadow-pop"
      aria-label="モバイルメニュー"
    >
      <MobileNavLinks :show-site-links="true" />
    </aside>
  </template>
</template>
