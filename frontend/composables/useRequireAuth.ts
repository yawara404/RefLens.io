import { useAuthStore } from '~/stores/authStore'
import { useToast } from '~/composables/useToast'

interface RequireAuthOptions {
  /** 未ログイン時に開く UI（既定は `reflens:auth-switch` イベント） */
  onUnauthenticated?: () => void
}

/**
 * ログイン専用操作のガード。
 *
 * 同じ実装がページごとに散らばっていたため、通知とダイアログ起動を1か所にまとめた。
 * 使い方: `const requireAuth = useRequireAuth()` → `if (!requireAuth('保存')) return`
 */
export function useRequireAuth(options: RequireAuthOptions = {}) {
  const auth = useAuthStore()
  const toast = useToast()

  return function requireAuth(actionLabel = 'この操作'): boolean {
    if (auth.isAuthenticated) return true

    toast.info(`${actionLabel}はログイン専用です。新規登録またはログインしてご利用ください。`)

    if (options.onUnauthenticated) {
      options.onUnauthenticated()
    } else if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event('reflens:auth-switch'))
    }
    return false
  }
}
