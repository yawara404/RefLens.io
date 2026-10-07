<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import {
  LogIn, LogOut, Pencil, Unlink, Check, Save, AlertCircle, ExternalLink,
  User, Instagram, Compass, ChevronRight
} from 'lucide-vue-next'
import { useAuthStore } from '~/stores/authStore'
import { useToast } from '~/composables/useToast'
import SiteInfoPage from '~/components/ui/SiteInfoPage.vue'
import AuthDialog from '~/components/ui/AuthDialog.vue'

const auth = useAuthStore()
const toast = useToast()

useHead({ title: '管理ページ | RefLens.io' })

/** 認証状態が確定するまで描画しない（ハイドレーション不一致の回避） */
const isMounted = ref(false)
onMounted(() => { isMounted.value = true })
const canRender = computed(() => isMounted.value && auth.isReady)

const isDialogOpen = ref(false)
const savingName = ref(false)
const disconnecting = ref(false)

const confirmTarget = ref<'pixiv' | 'instagram' | null>(null)
const confirmText = ref('')

/** 表示名フォームの下書き。/auth/me が返ってきたらその値で上書きする。 */
const usernameDraft = ref('')
watch(
  () => auth.user?.username,
  (name) => { usernameDraft.value = name ?? '' },
  { immediate: true },
)

const canSaveUsername = computed(() => {
  const next = usernameDraft.value.trim()
  return next.length > 0 && next.length <= 100 && next !== (auth.user?.username ?? '')
})

function openDisconnectDialog(service: 'pixiv' | 'instagram') {
  confirmTarget.value = service
  if (service === 'pixiv') {
    confirmText.value = 'pixiv の連携を解除しますか？\n保存済みトークンはサーバーから削除されます。'
  } else {
    confirmText.value = 'Instagram の連携を解除しますか？\n保存済みトークンはサーバーから削除されます。'
  }
}

async function confirmDisconnect(service: 'pixiv' | 'instagram') {
  if (disconnecting.value) return
  disconnecting.value = true
  try {
    if (service === 'pixiv') await auth.disconnectPixiv()
    else await auth.disconnectInstagram()
    confirmTarget.value = null
    toast.success(service === 'pixiv' ? 'pixiv の連携を解除しました' : 'Instagram の連携を解除しました')
  } catch (e: any) {
    toast.error('連携解除に失敗しました', e?.data?.detail || e?.message || '連携を解除できませんでした。')
  } finally {
    disconnecting.value = false
  }
}

async function saveUsername() {
  if (!canSaveUsername.value || savingName.value) return
  savingName.value = true
  try {
    await auth.updateUsername(usernameDraft.value.trim())
    toast.success('表示名を変更しました')
  } catch (e: any) {
    toast.error('表示名の変更に失敗しました', e?.data?.detail || e?.message || '時間をおいて再度お試しください')
  } finally {
    savingName.value = false
  }
}

/** PixivConnectDialog（app.vue に配置済み）を開く */
function connectPixiv() {
  window.dispatchEvent(new Event('reflens:pixiv-connect'))
}

/** ログインし直して別アカウントで使う（AuthDialog を開く） */
function openAccountSwitcher() {
  isDialogOpen.value = true
}

/** ログアウトして共通のゲスト領域へ戻る（トーストは store 側で出している） */
function handleLogout() {
  auth.logout()
  navigateTo('/')
}

/** 保存ボタンを form submit にしてあるので、未入力・記号混入はブラウザの validity で弾かれる。 */
function handleUsernameChange(e: Event) {
  const target = e.target as HTMLInputElement
  if (!/^[a-zA-Z0-9_一-鿿ぁ-ゔァ-ヴー々〆ヵヶー]*$/.test(target.value)) {
    target.setCustomValidity('半角英数字・アンダースコア・日本語のみ利用可能です。')
  } else {
    target.setCustomValidity('')
  }
}
</script>

<template>
  <SiteInfoPage title="管理ページ" eyebrow="RefLens.io / Account">
    <!-- 認証状態が確定するまでスケルトン -->
    <div v-if="!canRender" class="space-y-7" aria-hidden="true">
      <div class="h-44 rounded-2xl border border-canvas-border bg-canvas-card animate-pulse" />
      <div class="h-56 rounded-2xl border border-canvas-border bg-canvas-card animate-pulse" />
    </div>

    <!-- 未ログイン / ゲスト -->
    <div
      v-else-if="!auth.isAuthenticated"
      class="rounded-2xl border border-canvas-border bg-canvas-panel p-6 sm:p-8 text-center space-y-3"
    >
      <div class="mx-auto w-11 h-11 rounded-xl bg-brand-soft text-brand flex items-center justify-center">
        <User class="w-5 h-5" />
      </div>
      <h2 class="text-base font-bold text-ink">アカウントにログインしてください</h2>
      <p class="text-sm text-ink-muted leading-relaxed">
        管理ページでは、表示名や外部サービスとの連携を管理できます。
      </p>
      <p class="text-xs text-ink-subtle">ログインしないままだと、共通のゲスト領域が使われます。</p>
      <button
        type="button"
        class="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-brand text-brand-fg text-xs font-bold hover:bg-brand-hover transition-colors"
        @click="isDialogOpen = true"
      >
        <LogIn class="w-3.5 h-3.5" />
        ログイン / アカウント作成
      </button>
    </div>

    <template v-else>
      <!-- プロフィール -->
      <section
        class="rounded-2xl border border-canvas-border bg-canvas-panel p-5 sm:p-6"
        aria-labelledby="account-profile-heading"
      >
        <h2 id="account-profile-heading" class="text-sm font-bold text-ink">プロフィール</h2>

        <div class="mt-4 flex items-center gap-3 min-w-0">
          <img
            v-if="auth.user?.avatar_url"
            :src="auth.user.avatar_url"
            :alt="auth.displayName"
            class="w-11 h-11 rounded-full object-cover shrink-0"
          >
          <span
            v-else
            class="w-11 h-11 rounded-full bg-brand-soft text-brand flex items-center justify-center text-sm font-bold shrink-0"
          >
            {{ auth.initials }}
          </span>
          <div class="min-w-0">
            <p class="text-sm font-bold text-ink truncate">{{ auth.displayName }}</p>
            <p class="text-xs font-mono text-ink-subtle truncate">{{ auth.user?.email || '—' }}</p>
          </div>
        </div>

        <div class="mt-5 pt-5 border-t border-canvas-border space-y-2">
          <label for="account-username" class="flex items-center gap-1.5 text-xs font-semibold text-ink">
            <Pencil class="w-3.5 h-3.5" />
            表示名
          </label>

          <form class="flex flex-col sm:flex-row gap-2" @submit.prevent="saveUsername">
            <input
              id="account-username"
              v-model="usernameDraft"
              type="text"
              maxlength="100"
              autocomplete="nickname"
              placeholder="表示名を入力"
              class="flex-1 min-w-0 bg-canvas-card border border-canvas-border rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-subtle focus:outline-none focus:border-brand transition-colors"
              @input="handleUsernameChange"
            >
            <button
              type="submit"
              class="shrink-0 inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-brand text-brand-fg text-xs font-bold hover:bg-brand-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="!canSaveUsername || savingName"
            >
              <Save class="w-3.5 h-3.5" />
              {{ savingName ? '保存中…' : '保存' }}
            </button>
          </form>

          <p class="text-[11px] leading-relaxed text-ink-subtle">
            半角英数字・アンダースコア・日本語のみ利用できます（100文字まで）。
          </p>
        </div>
      </section>

      <!-- 連携サービス -->
      <section
        class="rounded-2xl border border-canvas-border bg-canvas-panel p-5 sm:p-6"
        aria-labelledby="account-services-heading"
      >
        <h2 id="account-services-heading" class="text-sm font-bold text-ink">連携サービス</h2>
        <p class="mt-1 text-[11px] text-ink-subtle">解除すると、サーバーに保存された認証情報は削除されます。</p>

        <ul class="mt-4 space-y-3">
          <!-- pixiv -->
          <li class="flex flex-wrap items-center gap-3 rounded-xl border border-canvas-border bg-canvas-card px-4 py-3">
            <div
              class="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
              :class="auth.user?.pixiv_connected ? 'bg-pixiv-soft text-pixiv' : 'bg-canvas-hover text-ink-subtle'"
            >
              <Compass class="w-4 h-4" />
            </div>
            <div class="min-w-0 flex-1">
              <p class="text-xs font-bold text-ink">pixiv</p>
              <p
                class="text-[11px] truncate"
                :class="auth.user?.pixiv_connected ? 'text-ink-muted' : 'text-ink-subtle'"
              >
                <template v-if="auth.user?.pixiv_connected">
                  接続済み<template v-if="auth.user.pixiv_username">：{{ auth.user.pixiv_username }}</template>
                </template>
                <template v-else>未接続</template>
              </p>
            </div>
            <button
              v-if="!auth.user?.pixiv_connected"
              type="button"
              class="px-3 py-1.5 rounded-lg bg-pixiv text-white text-xs font-semibold hover:bg-pixiv-hover transition-colors"
              @click="connectPixiv"
            >
              接続する
            </button>
            <button
              v-else
              type="button"
              class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-canvas-border bg-canvas-panel text-xs font-semibold text-ink-muted hover:text-danger hover:border-danger transition-colors disabled:opacity-50"
              :disabled="disconnecting"
              @click="openDisconnectDialog('pixiv')"
            >
              <Unlink class="w-3.5 h-3.5" />
              解除
            </button>
          </li>

          <!-- Instagram -->
          <li class="flex flex-wrap items-center gap-3 rounded-xl border border-canvas-border bg-canvas-card px-4 py-3">
            <div
              class="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
              :class="auth.user?.instagram_connected ? 'bg-instagram-soft text-instagram' : 'bg-canvas-hover text-ink-subtle'"
            >
              <Instagram class="w-4 h-4" />
            </div>
            <div class="min-w-0 flex-1">
              <p class="text-xs font-bold text-ink">Instagram</p>
              <p
                class="text-[11px] truncate"
                :class="auth.user?.instagram_connected ? 'text-ink-muted' : 'text-ink-subtle'"
              >
                {{ auth.user?.instagram_connected ? '接続済み' : '未接続' }}
              </p>
            </div>
            <span
              v-if="auth.user?.instagram_connected"
              class="hidden sm:flex items-center gap-1 text-[11px] font-semibold text-ok"
              aria-hidden="true"
            >
              <Check class="w-3.5 h-3.5" />
            </span>
            <button
              v-if="auth.user?.instagram_connected"
              type="button"
              class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-canvas-border bg-canvas-panel text-xs font-semibold text-ink-muted hover:text-danger hover:border-danger transition-colors disabled:opacity-50"
              :disabled="disconnecting"
              @click="openDisconnectDialog('instagram')"
            >
              <Unlink class="w-3.5 h-3.5" />
              解除
            </button>
          </li>
        </ul>

        <p class="mt-3 text-[11px] leading-relaxed text-ink-subtle">
          Instagram に接続するときは、ボード画面の取り込みダイアログから行ってください。
        </p>

        <!-- 連携解除の確認 -->
        <div
          v-if="confirmTarget"
          class="mt-4 rounded-xl border border-danger bg-danger-soft p-4 space-y-3"
          role="alertdialog"
          aria-labelledby="disconnect-heading"
          aria-describedby="disconnect-description"
        >
          <div class="flex items-start gap-2.5">
            <AlertCircle class="w-4 h-4 text-danger shrink-0 mt-0.5" />
            <div class="min-w-0">
              <p id="disconnect-heading" class="text-sm font-bold text-ink">
                {{ confirmTarget === 'pixiv' ? 'pixiv の連携を解除' : 'Instagram の連携を解除' }}
              </p>
              <p id="disconnect-description" class="mt-1 text-xs leading-relaxed text-ink-muted whitespace-pre-line">
                {{ confirmText }}
              </p>
            </div>
          </div>
          <div class="flex gap-2 pl-6">
            <button
              type="button"
              class="flex-1 rounded-lg bg-danger px-3 py-1.5 text-xs font-semibold text-white transition-colors disabled:opacity-50"
              :disabled="disconnecting"
              @click="confirmDisconnect(confirmTarget)"
            >
              {{ disconnecting ? '解除中…' : '解除する' }}
            </button>
            <button
              type="button"
              class="flex-1 rounded-lg border border-canvas-border bg-canvas-raised px-3 py-1.5 text-xs text-ink-muted hover:text-ink transition-colors disabled:opacity-50"
              :disabled="disconnecting"
              @click="confirmTarget = null"
            >
              戻る
            </button>
          </div>
        </div>
      </section>

      <!-- アカウント -->
      <section
        class="rounded-2xl border border-canvas-border bg-canvas-panel p-5 sm:p-6"
        aria-labelledby="account-session-heading"
      >
        <h2 id="account-session-heading" class="text-sm font-bold text-ink">アカウント</h2>

        <div class="mt-4 space-y-3">
          <button
            type="button"
            class="w-full flex items-center gap-3 rounded-xl border border-canvas-border bg-canvas-card px-4 py-3 text-left hover:bg-canvas-hover transition-colors"
            @click="openAccountSwitcher"
          >
            <ExternalLink class="w-4 h-4 shrink-0 text-ink-subtle" />
            <span class="min-w-0 flex-1">
              <span class="block text-xs font-bold text-ink">別のアカウントに切り替える</span>
              <span class="block mt-0.5 text-[11px] text-ink-subtle">
                ログイン画面を開いて、他のアカウントで入り直します
              </span>
            </span>
            <ChevronRight class="w-4 h-4 shrink-0 text-ink-subtle" />
          </button>

          <button
            type="button"
            class="w-full flex items-center gap-3 rounded-xl border border-canvas-border bg-canvas-card px-4 py-3 text-left text-danger hover:border-danger hover:bg-danger-soft transition-colors"
            @click="handleLogout"
          >
            <LogOut class="w-4 h-4 shrink-0" />
            <span class="min-w-0 flex-1">
              <span class="block text-xs font-bold">ログアウト</span>
              <span class="block mt-0.5 text-[11px] text-ink-subtle">共通のゲスト領域に戻ります</span>
            </span>
          </button>
        </div>
      </section>
    </template>

    <AuthDialog v-model="isDialogOpen" />
  </SiteInfoPage>
</template>
