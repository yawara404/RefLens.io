/**
 * メディアURLの解決ヘルパー。
 *
 * DB の `file_path` は `/uploads/xxx.jpg` のようにルート絶対パスで、
 * `mediaBase` は ローカルなら `http://localhost:8080`、
 * サブパス配信（Cloudflare Tunnel）なら `/RefLens.io/` のような
 * 末尾スラッシュ付きの値になる。
 *
 * 素朴に `${mediaBase}${file_path}` と連結すると `/RefLens.io//uploads/...` の
 * 二重スラッシュになり、ingress の path ルールにマッチせず 404 になる。
 * ここでは区切りスラッシュを必ず1つに正規化して結合する。
 */
export function useMediaUrl() {
  const { mediaBase } = useBackendUrl()

  /**
   * media のパスをブラウザで引ける URL に変換する
   */
  function resolveMediaUrl(filePath?: string | null): string {
    if (!filePath) return ''

    // 既に絶対URLならそのまま（外部画像の Hotlink）
    if (/^https?:\/\//i.test(filePath)) return filePath

    const base = mediaBase.value
    // 結合するパス側の先頭スラッシュは1つだけ残す
    const path = filePath.startsWith('/') ? filePath : `/${filePath}`

    return `${base}${path}`
  }

  return { resolveMediaUrl }
}