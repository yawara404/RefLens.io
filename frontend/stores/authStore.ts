import { defineStore } from 'pinia'
import type { AuthUser } from '~/types'
import { useBackendUrl } from '~/composables/useBackendUrl'
import { useToast } from '~/composables/useToast'

const STORAGE_KEY = 'reflens-auth-token'

/** ゲストアカウントはパスワードを持たないため、ログイン済み表示の判定から除外する */
const GUEST_EMAIL = 'creator@reflens.io'

interface TokenResponse {
  access_token: string
  token_type: string
  user_id: string
  username: string
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: '',
    user: null as AuthUser | null,
    /** クライアント起動時に一度だけトークンを復元する */
    isReady: false,
    restoreRetryScheduled: false,
    isSubmitting: false,
  }),

  getters: {
    /** トークンを保持し、バックエンドでも認識された状態か */
    isAuthenticated(state): boolean {
      return !!state.token && !!state.user && state.user.email !== GUEST_EMAIL
    },

    /** ゲストとしてアプリを使っている状態か */
    isGuest(state): boolean {
      return !state.token || state.user?.email === GUEST_EMAIL
    },

    /** ヘッダー等に表示する名前 */
    displayName(state): string {
      return state.user?.username || ''
    },

    /** アバターが無い場合のイニシャル（最大2文字） */
    initials(state): string {
      const name = state.user?.username?.trim()
      if (!name) return '?'
      return name.slice(0, 2).toUpperCase()
    },
  },

  actions: {
    /** API のベースURL（authStore からは composable 経由でしか取れないため関数を渡す） */
    api(path: string) {
      const { apiBase } = useBackendUrl()
      return `${apiBase.value}${path}`
    },

    /** Authorization ヘッダー。トークンが無ければ undefined。 */
    authHeaders(): Record<string, string> | undefined {
      if (!this.token) return undefined
      return { Authorization: `Bearer ${this.token}` }
    },

    persist(token: string) {
      this.token = token
      if (typeof window === 'undefined') return
      try {
        window.localStorage.setItem(STORAGE_KEY, token)
      } catch {
        /* localStorage 無効時はセッション内のみ保持 */
      }
    },

    clear() {
      this.token = ''
      this.user = null
      if (typeof window === 'undefined') return
      try {
        window.localStorage.removeItem(STORAGE_KEY)
      } catch {
        /* ignore */
      }
    },

    /** 保存済みトークンを検証する。通信障害では消さず、復旧後に再試行する。 */
    async restoreSavedSession() {
      const token = this.token
      if (!token) return

      try {
        const user = await $fetch<AuthUser>(this.api('/auth/me'), {
          headers: this.authHeaders(),
          timeout: 8000,
        })
        if (this.token !== token) return
        // /auth/me は無効なトークンでもゲストを返す。
        if (user.email === GUEST_EMAIL) {
          this.clear()
        } else {
          this.user = user
          this.notifyChanged()
        }
      } catch (error: any) {
        if (this.token !== token) return
        if (error?.statusCode === 401 || error?.statusCode === 403) {
          this.clear()
          return
        }
        if (typeof window !== 'undefined' && !this.restoreRetryScheduled) {
          this.restoreRetryScheduled = true
          window.setTimeout(() => {
            this.restoreRetryScheduled = false
            if (this.token === token) void this.restoreSavedSession()
          }, 5000)
        }
      }
    },

    /** 保存済みトークンでユーザー情報を復元する。 */
    async init() {
      if (this.isReady) return

      if (typeof window !== 'undefined') {
        try {
          this.token = window.localStorage.getItem(STORAGE_KEY) || ''
        } catch {
          this.token = ''
        }
      }

      if (this.token) {
        await this.restoreSavedSession()
      }

      this.isReady = true
    },

    async login(email: string, password: string) {
      this.isSubmitting = true
      try {
        const res = await $fetch<TokenResponse>(this.api('/auth/login'), {
          method: 'POST',
          body: { email: email.trim(), password },
        })
        await this.adopt(res)
        return true
      } catch (e: any) {
        useToast().error('ログインに失敗しました', e?.data?.detail || e?.message || '認証サーバーを確認してください')
        return false
      } finally {
        this.isSubmitting = false
      }
    },

    async register(email: string, username: string, password: string) {
      this.isSubmitting = true
      try {
        const res = await $fetch<TokenResponse>(this.api('/auth/register'), {
          method: 'POST',
          body: {
            email: email.trim(),
            username: username.trim(),
            password,
          },
        })
        await this.adopt(res)
        return true
      } catch (e: any) {
        useToast().error('登録に失敗しました', e?.data?.detail || e?.message || '入力内容を確認してください')
        return false
      } finally {
        this.isSubmitting = false
      }
    },

    /** ゲストモードで入り直す */
    async loginAsGuest() {
      this.isSubmitting = true
      try {
        const res = await $fetch<TokenResponse>(this.api('/auth/guest'), { method: 'POST' })
        await this.adopt(res)
        return true
      } catch (e: any) {
        useToast().error('ゲストログインに失敗しました', e?.data?.detail || e?.message)
        return false
      } finally {
        this.isSubmitting = false
      }
    },

    /** トークンを保存して /auth/me で本人情報を確定させる */
    async adopt(res: TokenResponse) {
      this.persist(res.access_token)
      try {
        this.user = await $fetch<AuthUser>(this.api('/auth/me'), {
          headers: this.authHeaders(),
        })
      } catch {
        // /me が取れなくてもトークンは有効なので、表示名だけ埋めて続行する
        this.user = {
          id: res.user_id,
          email: '',
          username: res.username,
          avatar_url: null,
          instagram_connected: false,
          pixiv_connected: false,
          pixiv_username: null,
        }
      }
      this.notifyChanged()
    },

    logout() {
      this.clear()
      this.notifyChanged()
      useToast().info('ログアウトしました', 'ゲストモードに戻りました')
    },

    /** 表示名を変更する。成功時は /auth/me の結果でユーザー情報を差し替える。 */
    async updateUsername(username: string) {
      const res = await $fetch<AuthUser>(this.api('/auth/me'), {
        method: 'PUT',
        body: { username },
        headers: this.authHeaders(),
      })
      this.user = res
      this.notifyChanged()
      return res
    },

    /** /auth/me で表示名・連携状態を取り直す。失敗しても変更通知は出す。 */
    async refreshUser() {
      try {
        const user = await $fetch<AuthUser>(this.api('/auth/me'), {
          headers: this.authHeaders(),
          timeout: 8000,
        })
        // /auth/me は無効なトークンでもゲストを返す
        if (user.email === GUEST_EMAIL) {
          this.clear()
        } else {
          this.user = user
        }
      } finally {
        this.notifyChanged()
      }
    },

    /** pixiv の連携を解除する（トークンはサーバー側で削除） */
    async disconnectPixiv() {
      await $fetch(this.api('/pixiv/disconnect'), {
        method: 'POST',
        headers: this.authHeaders(),
      })
      await this.refreshUser()
    },

    /** Instagram の連携を解除する */
    async disconnectInstagram() {
      await $fetch(this.api('/instagram/disconnect'), {
        method: 'POST',
        headers: this.authHeaders(),
      })
      await this.refreshUser()
    },

    /**
     * ユーザーは変わったので、依存する表示側へ再取得を促す。
     *
     * boardStore は Pinia で共有されているためプラグインから再取得できるが、
     * usePixiv は composable ごとに ref を持つため参照できない。
     * /view 側は自前でこのイベントを購読して pixiv の接続状態を取り直す。
     */
    notifyChanged() {
      if (typeof window === 'undefined') return
      window.dispatchEvent(new Event('reflens:auth-changed'))
    },
  },
})
