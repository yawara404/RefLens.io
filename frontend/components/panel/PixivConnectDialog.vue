<script setup lang="ts">
import { useBackendUrl } from '~/composables/useBackendUrl'
import { onMounted, onUnmounted, ref } from 'vue'
import { useAuthStore } from '~/stores/authStore'
import PixivLoginFlow from '~/components/ui/PixivLoginFlow.vue'

const { apiBase } = useBackendUrl()
const auth = useAuthStore()
const open = ref(false)
/** 既定は「Pixivでログイン」（Palleria の Web Login 相当） */
const usePixivLogin = ref(true)
/** Refresh Token 入力タブを出せるか。公開プレビューでは false。 */
const tokenConnectAvailable = ref(false)
const token = ref('')
const busy = ref(false)
const error = ref('')

async function show() {
  token.value = ''
  error.value = ''
  usePixivLogin.value = true
  open.value = true
  // 公開プレビューでは Refresh Token の平文入力を広めないため、タブの可否だけ確認する。
  try {
    const status = await $fetch<{ token_connect_available?: boolean }>(`${apiBase.value}/pixiv/status`)
    tokenConnectAvailable.value = !!status.token_connect_available
  } catch {
    tokenConnectAvailable.value = false
  }
  if (!tokenConnectAvailable.value) usePixivLogin.value = true
}

function close() {
  if (busy.value) return
  token.value = ''
  open.value = false
}

function finishPixivLogin() {
  window.location.reload()
}

async function submit() {
  if (!token.value.trim() || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await $fetch(`${apiBase.value}/pixiv/connect`, {
      method: 'POST',
      body: { refresh_token: token.value.trim() },
    })
    token.value = ''
    window.location.reload()
  } catch (e: any) {
    error.value = e?.data?.detail || '接続できませんでした。トークンと設定を確認してください。'
  } finally {
    busy.value = false
  }
}

onMounted(() => window.addEventListener('reflens:pixiv-connect', show))
onUnmounted(() => window.removeEventListener('reflens:pixiv-connect', show))
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-[100] scrim flex items-center justify-center p-4" @click.self="close">
      <form class="w-full max-w-md rounded-2xl border border-canvas-border bg-canvas-panel p-6 shadow-pop space-y-4 overflow-y-auto max-h-[85vh]" role="dialog" aria-modal="true" aria-labelledby="pixiv-connect-title" @submit.prevent="submit">
        <h2 id="pixiv-connect-title" class="text-lg font-semibold text-ink">Pixivに接続</h2>
        <div class="flex gap-3 text-xs">
          <button type="button" class="underline" :class="usePixivLogin ? 'text-pixiv font-semibold' : 'text-ink-muted'" @click="usePixivLogin = true">Pixivでログイン</button>
          <button v-if="tokenConnectAvailable" type="button" class="underline" :class="!usePixivLogin ? 'text-pixiv font-semibold' : 'text-ink-muted'" @click="usePixivLogin = false">Refresh Tokenを使う</button>
        </div>
        <PixivLoginFlow v-if="usePixivLogin" :mode="auth.isAuthenticated ? 'link' : 'login'" @completed="finishPixivLogin" />
        <template v-else>
          <p class="text-sm text-ink-muted">取得済みのRefresh Tokenを入力してください。Pixivのパスワードは入力しないでください。</p>
          <label class="block text-xs font-medium text-ink" for="pixiv-refresh-token">Refresh Token</label>
          <input id="pixiv-refresh-token" v-model="token" type="password" autocomplete="off" spellcheck="false"
            class="w-full rounded-lg border border-canvas-border bg-canvas-card px-3 py-2 text-sm text-ink"
            placeholder="Refresh Token">
          <p v-if="error" role="alert" class="text-xs text-danger">{{ error }}</p>
        </template>
        <div class="flex justify-end gap-2">
          <button type="button" class="px-4 py-2 text-sm text-ink-muted" :disabled="busy" @click="close">キャンセル</button>
          <button v-if="!usePixivLogin" type="submit" class="rounded-lg bg-pixiv px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" :disabled="busy || !token.trim()">
            {{ busy ? '接続中…' : '接続' }}
          </button>
        </div>
        <p class="text-xs text-ink-subtle">非公式接続です。Pixivの仕様変更で利用できなくなる場合があります。設定方法は PIXIV_SETUP.md を参照してください。</p>
      </form>
    </div>
  </Teleport>
</template>
