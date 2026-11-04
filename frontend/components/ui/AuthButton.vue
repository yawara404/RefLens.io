<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { LogIn, LogOut, Settings2, ChevronDown, ChevronRight, X, User } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import { useAuthStore } from '~/stores/authStore'
import AuthDialog from '~/components/ui/AuthDialog.vue'

const auth = useAuthStore()
const route = useRoute()

const isDialogOpen = ref(false)
const isMenuOpen = ref(false)

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
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('reflens:auth-switch', openAccountSwitcher)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('reflens:auth-switch', openAccountSwitcher)
})
</script>

<template>
  <div class="relative shrink-0">
    <!-- 認証状態が確定するまではスケルトン（ハイドレーション不一致の回避）-->
    <div
      v-if="!canRenderAuthUi"
      class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-semibold bg-canvas-card border border-canvas-border text-ink-subtle"
      aria-hidden="true"
    >
      <LogIn class="w-3.5 h-3.5" />
      <span class="hidden md:inline w-14 h-3 rounded bg-canvas-hover" />
    </div>

    <!-- 未ログイン: ログインボタン -->
    <button
      v-else-if="!auth.isAuthenticated"
      type="button"
      class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-semibold bg-brand text-brand-fg hover:bg-brand-hover transition-colors"
      title="ログイン / アカウント作成"
      @click="isDialogOpen = true"
    >
      <LogIn class="w-3.5 h-3.5" />
      <span class="hidden md:inline">ログイン</span>
    </button>

    <!-- ログイン済み: アバター + アカウントポップアップモーダル -->
    <template v-else>
      <button
        type="button"
        class="flex items-center gap-1.5 border border-canvas-border-strong rounded-xl px-2 py-1 hover:bg-canvas-hover transition-colors"
        title="アカウントメニュー"
        aria-label="アカウントメニューを開く"
        aria-haspopup="dialog"
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
        <span class="hidden lg:inline text-xs font-bold text-ink max-w-[140px] truncate">
          {{ auth.displayName }}
        </span>
        <ChevronDown
          class="w-3.5 h-3.5 shrink-0 transition-transform"
          :class="isMenuOpen ? 'rotate-180 text-ink' : 'text-ink-muted'"
        />
      </button>

      <Teleport to="body">
        <div
          v-if="isMenuOpen"
          class="fixed inset-0 z-[85] flex items-end sm:items-center justify-center p-2 sm:p-4 scrim animate-fade-in"
          @click.self="closeMenu"
        >
          <div
            class="w-full max-w-xs rounded-2xl border border-canvas-border bg-canvas-panel shadow-pop overflow-hidden animate-scale-in"
            role="dialog"
            aria-modal="true"
            aria-label="アカウントメニュー"
          >
            <div class="px-4 py-3 border-b border-canvas-border flex items-center justify-between gap-2">
              <div class="flex items-center gap-2.5 min-w-0">
                <div class="w-8 h-8 rounded-full bg-brand-soft text-brand flex items-center justify-center text-xs font-bold shrink-0">
                  {{ auth.initials || 'U' }}
                </div>
                <div class="min-w-0">
                  <p class="text-xs font-bold text-ink truncate">{{ auth.displayName }}</p>
                  <p class="text-[11px] font-mono text-ink-muted truncate">{{ auth.user?.email }}</p>
                </div>
              </div>
              <button
                type="button"
                class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors shrink-0"
                aria-label="閉じる"
                @click="closeMenu"
              >
                <X class="w-4 h-4" />
              </button>
            </div>

            <div class="p-3 space-y-1.5">
              <NuxtLink
                to="/account"
                class="flex items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-xs font-bold text-ink bg-canvas-bg hover:bg-canvas-hover border border-canvas-border-strong transition-colors"
                :aria-current="route.path === '/account' ? 'page' : undefined"
                @click="closeMenu"
              >
                <Settings2 class="w-4 h-4 text-brand shrink-0" />
                <span class="flex-1">アカウント管理ページ</span>
                <ChevronRight class="w-4 h-4 shrink-0 text-ink-muted" />
              </NuxtLink>

              <button
                type="button"
                class="w-full flex items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-xs font-bold text-danger bg-danger-soft/60 hover:bg-danger-soft transition-colors"
                @click="handleLogout"
              >
                <LogOut class="w-4 h-4 shrink-0" />
                <span>ログアウト</span>
              </button>
            </div>
          </div>
        </div>
      </Teleport>
    </template>

    <AuthDialog v-model="isDialogOpen" />
  </div>
</template>
