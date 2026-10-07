import { computed } from 'vue'

/**
 * バックエンド URL の解決。
 *
 * `runtimeConfig.public.apiBase` / `mediaBase` には「ベースパスを除いた値」を入れる。
 * 絶対URL（http:// から始まる）ならそのまま使い、相対パスなら app.baseURL を重ねる。
 * これによりローカル開発とサブパス配信（Cloudflare Tunnel）の両方で
 * 二重スラッシュが起きないようにする。
 *
 * 注意: `useAppConfig` は Nuxt 内部の自動インポートと名前が衝突するため、
 * この composable は `useBackendUrl` という名前で公開している。
 */
export function useBackendUrl() {
  const config = useRuntimeConfig()

  /** app.baseURL（必ず先頭・末尾スラッシュ付き）。例: "/" / "/RefLens.io/" */
  const appBase = computed<string>(() => {
    // public.appBase を優先し、無ければ Nuxt が注入した app.baseURL を使う
    const raw = (config.public.appBase as string) || '/'
    const withLeading = raw.startsWith('/') ? raw : `/${raw}`
    return withLeading.endsWith('/') ? withLeading : `${withLeading}/`
  })

  /**
   * app.baseURL を前方のパスに重ねる（絶対URLはそのまま返す）
   *
   * appBase が既に先頭に含まれている場合は重ねない。
   * baseURL 付きでビルドした場合、NUXT_PUBLIC_API_BASE=/RefLens.io/api/v1 のように
   * 渡した値は既に appBase を含むため、ここで重ねると /RefLens.io/RefLens.io/... になる。
   */
  function joinBase(raw: string): string {
    if (!raw) return appBase.value
    if (/^https?:\/\//i.test(raw)) return raw

    const base = appBase.value
    const trimmed = raw.replace(/^\/+/, '')
    if (!trimmed) return base

    // すでに appBase を含むならそのまま使う
    if (base !== '/' && (trimmed === base.replace(/^\/|\/$/g, '') || trimmed.startsWith(base))) {
      return `/${trimmed}`
    }

    return `${base}${trimmed}`
  }

  /** API のベースURL（末尾スラッシュなし） */
  const apiBase = computed<string>(() =>
    joinBase((config.public.apiBase as string) || '').replace(/\/+$/, '')
  )

  /** メディア（/uploads 配下）のベースURL（末尾スラッシュなし） */
  const mediaBase = computed<string>(() =>
    joinBase((config.public.mediaBase as string) || '').replace(/\/+$/, '')
  )

  return { appBase, apiBase, mediaBase }
}