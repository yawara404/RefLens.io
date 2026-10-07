<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { UserPlus, LogIn, X, Sparkles } from 'lucide-vue-next'
import { useAuthStore } from '~/stores/authStore'
import PixivLoginFlow from '~/components/ui/PixivLoginFlow.vue'

const open = defineModel<boolean>({ default: false })

const auth = useAuthStore()

type Mode = 'login' | 'register' | 'pixiv'

const mode = ref<Mode>('login')
const email = ref('')
const username = ref('')
const password = ref('')

const isRegister = computed(() => mode.value === 'register')

/** 入力欄が1つでも空なら送信できない */
const canSubmit = computed(() => {
  if (!email.value.trim() || !password.value) return false
  if (isRegister.value && !username.value.trim()) return false
  return true
})

// 開くたびにフォームを空にする（前のユーザーの入力が残るのを防ぐ）
watch(open, (isOpen) => {
  if (!isOpen) return
  mode.value = 'login'
  email.value = ''
  username.value = ''
  password.value = ''
})

function close() {
  if (auth.isSubmitting) return
  open.value = false
}

async function submit() {
  if (mode.value === 'pixiv') return
  if (!canSubmit.value || auth.isSubmitting) return

  const ok = isRegister.value
    ? await auth.register(email.value, username.value, password.value)
    : await auth.login(email.value, password.value)

  if (ok) open.value = false
}

/** ゲストとして入り直す。既存アカウント的数据は看不到になる点だけ需要注意。 */
async function continueAsGuest() {
  if (auth.isSubmitting) return
  await auth.loginAsGuest()
  open.value = false
}

function isTypingTarget(target: EventTarget | null) {
  const el = target as HTMLElement | null
  if (!el) return false
  return ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName) || !!el.isContentEditable
}

function onKeyDown(e: KeyboardEvent) {
  if (!open.value) return
  if (e.key === 'Escape' && !isTypingTarget(e.target)) close()
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-[100] scrim flex items-center justify-center p-4"
      @click.self="close"
      @keydown="onKeyDown"
    >
      <form
        class="w-full max-w-sm rounded-2xl border border-canvas-border bg-canvas-panel p-6 shadow-pop space-y-4 overflow-y-auto max-h-[85vh]"
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-dialog-title"
        @submit.prevent="submit"
      >
        <!-- ヘッダー -->
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-center gap-2.5 min-w-0">
            <div class="w-8 h-8 rounded-xl bg-brand-soft text-brand flex items-center justify-center shrink-0">
              <component :is="isRegister ? UserPlus : LogIn" class="w-4 h-4" />
            </div>
            <div class="min-w-0">
              <h2 id="auth-dialog-title" class="text-sm font-bold text-ink leading-tight">
                {{ isRegister ? 'アカウントを作成' : 'ログイン' }}
              </h2>
              <p class="text-[11px] text-ink-subtle mt-0.5">
                {{ isRegister ? 'あなたのリファレンスを保存できます' : 'アカウントにログイン' }}
              </p>
            </div>
          </div>
          <button
            type="button"
            class="p-1 rounded text-ink-subtle hover:text-ink hover:bg-canvas-hover transition-colors shrink-0"
            aria-label="閉じる (Esc)"
            @click="close"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <!-- モード切替 -->
        <div class="flex items-center gap-1 p-1 rounded-xl border border-canvas-border bg-canvas-card">
          <button
            v-for="opt in ([['login', 'ログイン'], ['register', '新規登録'], ['pixiv', 'Pixivでログイン']] as const)"
            :key="opt[0]"
            type="button"
            class="flex-1 py-1.5 rounded-lg text-xs font-semibold transition-colors"
            :class="mode === opt[0]
              ? 'bg-brand text-brand-fg'
              : 'text-ink-muted hover:text-ink hover:bg-canvas-hover'"
            :aria-pressed="mode === opt[0]"
            @click="mode = opt[0]"
          >
            {{ opt[1] }}
          </button>
        </div>

        <!-- 入力欄 -->
        <div v-if="mode !== 'pixiv'" class="space-y-3">
          <div v-if="isRegister">
            <label class="block text-[11px] font-medium text-ink-muted" for="auth-username">
              表示名
            </label>
            <input
              id="auth-username"
              v-model="username"
              type="text"
              autocomplete="nickname"
              placeholder=" illustrator"
              class="w-full bg-canvas-card border border-canvas-border rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-subtle focus:outline-none focus:border-brand transition-colors"
            >
          </div>

          <div>
            <label class="block text-[11px] font-medium text-ink-muted" for="auth-email">
              メールアドレス
            </label>
            <input
              id="auth-email"
              v-model="email"
              type="email"
              autocomplete="email"
              placeholder="you@example.com"
              class="w-full bg-canvas-card border border-canvas-border rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-subtle focus:outline-none focus:border-brand transition-colors font-mono text-xs"
            >
          </div>

          <div>
            <label class="block text-[11px] font-medium text-ink-muted" for="auth-password">
              パスワード
            </label>
            <input
              id="auth-password"
              v-model="password"
              type="password"
              :autocomplete="isRegister ? 'new-password' : 'current-password'"
              placeholder="8文字以上"
              class="w-full bg-canvas-card border border-canvas-border rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-subtle focus:outline-none focus:border-brand transition-colors"
            >
          </div>
        </div>

        <!-- 送信 -->
        <PixivLoginFlow v-if="mode === 'pixiv'" mode="login" @completed="open = false" />

        <button
          v-if="mode !== 'pixiv'"
          type="submit"
          class="w-full py-2.5 rounded-xl bg-brand text-brand-fg text-xs font-bold hover:bg-brand-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5"
          :disabled="!canSubmit || auth.isSubmitting"
        >
          <component :is="isRegister ? UserPlus : LogIn" class="w-3.5 h-3.5" />
          {{ auth.isSubmitting ? '処理中...' : (isRegister ? 'アカウントを作成' : 'ログイン') }}
        </button>

        <!-- ゲスト -->
        <div class="pt-3 border-t border-canvas-border space-y-2">
          <button
            type="button"
            class="w-full py-2 rounded-xl border border-canvas-border bg-canvas-card text-xs font-medium text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
            :disabled="auth.isSubmitting"
            @click="continueAsGuest"
          >
            <Sparkles class="w-3.5 h-3.5" />
            ゲストとして使う
          </button>
          <p class="text-[10px] text-ink-subtle leading-relaxed text-center">
            ログインしない場合、共通のゲスト領域に保存されます。
          </p>
        </div>
      </form>
    </div>
  </Teleport>
</template>
