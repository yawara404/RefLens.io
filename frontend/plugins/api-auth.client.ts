import { useAuthStore } from '~/stores/authStore'
import { useBackendUrl } from '~/composables/useBackendUrl'

/**
 * バックエンド API へのリクエストに Authorization ヘッダーを付けるプラグイン。
 *
 * バックエンドはトークン無しでもゲストユーザーを自動生成して返すため、
 * 未ログイン時は従来どおりヘッダーを付けない（＝従来挙動が保たれる）。
 * 一方ログイン後は各 API がそのユーザーのデータだけを返すようになる。
 *
 * 呼び出し側（boardStore / usePixiv / 各モーダルなど）個別に
 * ヘッダーを渡すと漏れる箇所が出るため、ここだけ一元的に差し込む。
 */
export default defineNuxtPlugin({
  name: 'api-auth',
  // ファイル名に .client を付けると SSR では読み込まれない。
  // SSR では localStorage もトークンも無いため、認証はクライアントだけでよい。
  async setup() {
    const auth = useAuthStore()
    const { apiBase } = useBackendUrl()

    // 保存済みトークンを先に復元する（初回リクエストから認証を効かせる）
    await auth.init()

    // 画像プロキシや内部 API にはトークンを付けない。
    // バックエンドAPI の_BASE_ URL だけを判定の基準にする。
    const apiPrefix = apiBase.value.replace(/\/+$/, '')
    const isBackendApi = (request: unknown): boolean => {
      if (typeof request !== 'string') return false
      // backend の絶対URL、またはベースパス付きの相対パス
      return request.startsWith(apiPrefix) || request.includes('/api/v1/')
    }

    const original = globalThis.$fetch

    // $fetch は baseURL を持つインスタンスなので、create で派生させ onRequest を差す。
    globalThis.$fetch = original.create({
      onRequest(ctx) {
        const headers = auth.authHeaders()
        if (!headers) return
        if (!isBackendApi(ctx.request)) return

        const existing = new Headers((ctx.options.headers as HeadersInit) || {})
        // 明示指定された Authorization を優先（テスト・デバッグ用）
        if (existing.has('Authorization')) return

        existing.set('Authorization', headers.Authorization)
        ctx.options.headers = existing
      },
    })
  },
})