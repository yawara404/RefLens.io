<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { Info, Lock, ChevronDown } from 'lucide-vue-next'
import { useAuthStore } from '~/stores/authStore'
import { useBackendUrl } from '~/composables/useBackendUrl'

const props = defineProps<{ mode: 'login' | 'link' }>()
const emit = defineEmits<{ completed: [] }>()
const auth = useAuthStore()
const { apiBase } = useBackendUrl()
const state = ref('')
const loginUrl = ref('')
const callback = ref('')
const busy = ref(false)
const error = ref('')
const callbackInput = ref<HTMLInputElement | null>(null)
/** コールバックURLのガイド（コピー対象のURLが何かを最初に分からせるため） */
const showGuide = ref(false)
const guideBody = ref<HTMLElement | null>(null)

/** 展開した直後、モーダル内スクロールでガイド本文が見える位置まで送る */
function toggleGuide() {
  showGuide.value = !showGuide.value
  if (!showGuide.value) return
  void nextTick(() => guideBody.value?.scrollIntoView({ block: 'nearest' }))
}

async function start() {
  busy.value = true
  error.value = ''
  try {
    const result = await $fetch<{ state: string; login_url: string }>(`${apiBase.value}/auth/pixiv/start`, {
      method: 'POST', body: { mode: props.mode },
    })
    state.value = result.state
    loginUrl.value = result.login_url
    window.open(result.login_url, '_blank', 'noopener,noreferrer')
  } catch (e: any) {
    error.value = e?.data?.detail || 'Pixivログインを開始できませんでした。'
  } finally {
    busy.value = false
  }
}

async function complete() {
  if (!state.value || !callback.value.trim() || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const result = await $fetch<{
      access_token: string; token_type: string; user_id: string; username: string
    }>(`${apiBase.value}/auth/pixiv/complete`, {
      method: 'POST',
      body: { state: state.value, callback_url_or_code: callback.value.trim() },
    })
    callback.value = ''
    state.value = ''
    await auth.adopt(result)
    emit('completed')
  } catch (e: any) {
    state.value = '' // One-time PKCE state is consumed even if code exchange fails.
    error.value = e?.data?.detail || 'Pixiv認証を完了できませんでした。最初からやり直してください。'
  } finally {
    busy.value = false
  }
}

/** 貼り付けた瞬間に自動で接続を試みる（開発者ツールからコピー → 貼るだけで完了） */
async function onPaste() {
  await nextTick()
  if (state.value && callback.value.trim()) void complete()
}
</script>

<template>
  <div class="space-y-3 text-xs">
    <p class="text-ink-muted leading-relaxed">
      Pixivの画面でログインするだけで接続できます。RefLensにPixivのパスワードを入力する必要はありません。
    </p>

    <ol class="space-y-1.5 text-ink-muted leading-relaxed">
      <li><span class="text-ink font-semibold">1.</span> 下のガイドを開き、開発者ツールの Network を用意する</li>
      <li><span class="text-ink font-semibold">2.</span> 「Pixivでログイン」でログインする</li>
      <li><span class="text-ink font-semibold">3.</span> <code class="font-mono">callback?</code> の Request URL をコピーして下に貼る（貼り付けだけで自動接続）</li>
    </ol>

    <!-- コールバックURLのガイド（モーダル内スクロール前提でコンパクトに保つ） -->
    <div class="rounded-xl border border-canvas-border bg-canvas-card">
      <button
        type="button"
        class="w-full flex items-center gap-2 px-2.5 py-1.5 text-left text-ink-muted hover:text-ink transition-colors"
        :aria-expanded="showGuide"
        @click="toggleGuide"
      >
        <Info class="w-3.5 h-3.5 shrink-0" />
        <span class="flex-1 text-[11px] font-semibold">コールバックURLの確認方法（開発者ツール）</span>
        <ChevronDown
          class="w-3.5 h-3.5 shrink-0 transition-transform"
          :class="showGuide ? 'rotate-180' : ''"
        />
      </button>

      <div
        v-if="showGuide"
        ref="guideBody"
        class="px-2.5 pb-2.5 pt-2 space-y-2 border-t border-canvas-border text-[11px] leading-relaxed"
      >
        <p class="text-ink-muted">
          ログイン時にRefLensへ渡す<strong class="text-ink">認可コード入りのURL</strong>へ飛びますが、
          アドレスバーには残らないため<strong class="text-ink">開発者ツールのネットワークログから確認</strong>します。
        </p>

        <!-- コピー対象の見本 -->
        <div class="flex items-start gap-1.5 rounded-lg border border-canvas-border bg-canvas-panel px-2 py-1.5 font-mono text-[9px] leading-relaxed break-all">
          <Lock class="w-3 h-3 shrink-0 text-ink-subtle" />
          <span class="min-w-0">
            <span class="text-ink-subtle">https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback?</span><span class="rounded bg-pixiv px-1 text-white">code=…</span><span class="text-ink-subtle">&amp;state=…</span>
          </span>
        </div>

        <ol class="space-y-1 text-ink-muted list-decimal pl-4">
          <li><kbd class="font-mono">⌘/⌥+I</kbd>（Windowsは <kbd class="font-mono">F12</kbd>）で開発者ツールを開き <strong class="text-ink">Network</strong> タブへ</li>
          <li><strong class="text-ink">Preserve log（ログを保持）</strong> を有効にしてから Pixiv でログイン</li>
          <li><code class="font-mono">callback</code> で検索し、出た Request URL を丸ごとコピー（<code class="font-mono">code=</code> の値だけでも可）</li>
        </ol>

        <p class="text-ink-subtle">
          認可コードは1回限り・600秒で失効します。切れたら「最初からやり直す」で取り直してください。Pixivのパスワードは入力しません。
        </p>
      </div>
    </div>

    <button type="button" class="w-full py-2 rounded-lg bg-pixiv text-white font-semibold disabled:opacity-50" :disabled="busy" @click="start">
      {{ state ? '最初からやり直す' : 'Pixivでログイン' }}
    </button>

    <template v-if="state">
      <p class="text-ink-subtle leading-relaxed">
        開発者ツールの Network で <code class="font-mono">callback?</code> の Request URL をコピーして貼り付けてください。
        <a :href="loginUrl" target="_blank" rel="noopener noreferrer" class="text-pixiv underline">画面が開かなかった場合はこちら</a>
      </p>
      <label class="block text-ink-muted" for="pixiv-callback">PixivのコールバックURLまたは認可コード</label>
      <input id="pixiv-callback" ref="callbackInput" v-model="callback" type="password" autocomplete="off" spellcheck="false"
        class="w-full rounded-lg border border-canvas-border bg-canvas-card px-3 py-2 text-ink" placeholder="callback?code=... を貼り付け"
        @paste="onPaste">
      <button type="button" class="w-full py-2 rounded-lg bg-brand text-brand-fg font-semibold disabled:opacity-50"
        :disabled="busy || !callback.trim()" @click="complete">{{ busy ? '確認中…' : 'RefLensに接続' }}</button>
    </template>

    <p v-if="error" role="alert" class="text-danger">{{ error }}</p>
  </div>
</template>
