<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { LogIn, LogOut, Settings2, ChevronDown, ChevronRight } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import { useAuthStore } from '~/stores/authStore'
import AuthDialog from '~/components/ui/AuthDialog.vue'

const auth = useAuthStore()
const route = useRoute()

const isDialogOpen = ref(false)
const isMenuOpen = ref(false)
const rootRef = ref<HTMLElement | null>(null)

const isMounted = ref(false)
onMounted(() => { isMounted.value = true })

/** 認証状態が確定するまで描画しない（ハイドレーション不一致の回避） */
const canRenderAuthUi = computed(() => isMounted.value && auth.isReady)

function closeMenu() {
  isMenuOpen.value = false
}

function toggleMenu() {
  isMenuOpen.value = !isMenuOpen.value
}

function onDocumentClick(e: MouseEvent) {
  if (isMenuOpen.value && rootRef.value && !rootRef.value.contains(e.target as Node)) {
    closeMenu()
  }
}

function onKeyDown(e: KeyboardEvent) {
  if (e.key !== 'Escape') return
  if (isMenuOpen.value) closeMenu()
  else if (isDialogOpen.value) isDialogOpen.value = false
}

/** `reflens:auth-switch` で開く、アカウント切り替え用ダイアログ */
function openAccountSwitcher() {
  closeMenu()
  isDialogOpen.value = true
}

/** メニューからログアウトしてトップへ戻る（共通のゲスト領域に戻る） */
function handleLogout() {
  closeMenu()
  auth.logout()
  navigateTo('/')
}

// ページ遷移でもメニューを開いたままにしない
watch(() => route.fullPath, closeMenu)

onMounted(() => {
  document.addEventListener('mousedown', onDocumentClick)
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('reflens:auth-switch', openAccountSwitcher)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', onDocumentClick)
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('reflens:auth-switch', openAccountSwitcher)
})
</script>

<template>
  <div ref="rootRef" class="relative">
    <!-- 認証状態が確定するまではスケルトン（ハイドレーション不一致の回避）-->
    <div
      v-if="!canRenderAuthUi"
      class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-canvas-card border border-canvas-border text-ink-subtle"
      aria-hidden="true"
    >
      <LogIn class="w-3.5 h-3.5" />
      <span class="hidden md:inline w-14 h-3 rounded bg-canvas-hover" />
    </div>

    <!-- 未ログイン: ログインボタン -->
    <button
      v-else-if="!auth.isAuthenticated"
      type="button"
      class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-brand text-brand-fg hover:bg-brand-hover transition-colors"
      title="ログイン / アカウント作成"
      @click="isDialogOpen = true"
    >
      <LogIn class="w-3.5 h-3.5" />
      <span class="hidden md:inline">ログイン</span>
    </button>

    <!-- ログイン済み: アバター + アカウントメニュー -->
    <template v-else>
      <button
        type="button"
        class="flex items-center gap-1.5 border border-canvas-border rounded-lg px-1.5 py-1 hover:bg-canvas-hover transition-colors"
        title="アカウントメニュー"
        aria-label="アカウントメニュー"
        aria-haspopup="menu"
        aria-controls="account-menu"
        :aria-expanded="isMenuOpen"
        @click="toggleMenu"
      >
        <img
          v-if="auth.user?.avatar_url"
          :src="auth.user.avatar_url"
          :alt="auth.displayName"
          class="w-6 h-6 rounded-full object-cover shrink-0"
        >
        <span
          v-else
          class="w-6 h-6 rounded-full bg-brand-soft text-brand flex items-center justify-center text-[10px] font-bold shrink-0"
        >
          {{ auth.initials }}
        </span>
        <span class="hidden lg:inline text-sm font-medium text-ink-muted max-w-[140px] truncate">
          {{ auth.displayName }}
        </span>
        <ChevronDown
          class="w-3.5 h-3.5 shrink-0 transition-transform"
          :class="isMenuOpen ? 'rotate-180 text-ink' : 'text-ink-subtle'"
        />
      </button>

      <nav
        v-if="isMenuOpen"
        id="account-menu"
        role="menu"
        aria-label="アカウントメニュー"
        class="absolute right-0 top-full mt-2 w-60 max-w-[calc(100vw-1rem)] rounded-xl border border-canvas-border bg-canvas-panel p-1.5 shadow-pop z-50"
      >
        <!-- 現在のアカウント -->
        <div class="px-3 py-2 mb-1 border-b border-canvas-border min-w-0">
          <p class="text-xs font-semibold text-ink truncate">{{ auth.displayName }}</p>
          <p class="text-[10px] font-mono text-ink-subtle truncate">{{ auth.user?.email }}</p>
        </div>

        <!-- 管理ページ -->
        <NuxtLink
          to="/account"
          role="menuitem"
          class="flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          :aria-current="route.path === '/account' ? 'page' : undefined"
          @click="closeMenu"
        >
          <Settings2 class="w-4 h-4 shrink-0" />
          <span class="flex-1">管理ページ</span>
          <ChevronRight class="w-3.5 h-3.5 shrink-0 text-ink-subtle" />
        </NuxtLink>

        <div class="my-1 border-t border-canvas-border" />

        <button
          type="button"
          role="menuitem"
          class="w-full flex items-center gap-2 rounded-lg px-3 py-2 text-xs text-ink-muted hover:text-danger hover:bg-danger-soft transition-colors"
          @click="handleLogout"
        >
          <LogOut class="w-4 h-4 shrink-0" />
          ログアウト
        </button>
      </nav>
    </template>

    <AuthDialog v-model="isDialogOpen" />
  </div>
</template>
