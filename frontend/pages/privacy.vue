<script setup lang="ts">
import SiteInfoPage from '~/components/ui/SiteInfoPage.vue'
import { useSeo } from '~/composables/useSeo'

useSeo({
  title: 'プライバシーポリシー | RefLens.io',
  description: 'RefLens.ioが取得・保存する情報、外部サービスへの送信、Cookieとログイン情報の扱いについてまとめています。',
  path: '/privacy',
})
</script>

<template>
  <SiteInfoPage title="プライバシーポリシー" updated="2026年11月17日">
    <p>このページは、現行のRefLens.ioで扱うデータと、その利用方法を説明します。公開運用に必要な運営者情報・問い合わせ窓口は、運営者による確認が必要です。</p>
    <section class="space-y-2">
      <h2 class="text-base font-semibold text-ink">取得・保存する情報</h2>
      <p>アカウント登録時のメールアドレス、ユーザー名、パスワードのハッシュ値、ログイン情報を扱います。保存した画像・参照元URL・ブックマーク・ボード・AI解析結果もサーバーに保存されます。Pixiv連携を行った場合は、連携に必要な認証情報と作品情報をサーバーで扱います。</p>
      <p>ブラウザにはログイン用トークンとテーマ設定を保存します。テーマ設定はCookieにも保存します。</p>
    </section>
    <section class="space-y-2">
      <h2 class="text-base font-semibold text-ink">利用目的</h2>
      <p>ログイン状態の維持、ライブラリ・キャンバスの表示と保存、外部サービス連携、画像の取得・キャッシュ、AI解析、および不具合対応のために利用します。</p>
    </section>
    <section class="space-y-2">
      <h2 class="text-base font-semibold text-ink">外部サービスとの通信</h2>
      <p>Pixiv作品の取得にはPixivとの通信が発生します。AI解析の設定によっては、画像がGoogle Gemini APIへ送信される場合があります。ローカルのOllamaまたは画像特徴量による解析を使用する場合もあります。画面表示時にはGoogle Fonts等の外部リソースを読み込む場合があります。</p>
      <p>画像の保管にはCloudflare R2を利用します。画像はバックエンドを通して配信し、設定によってサーバーにもキャッシュを保存します。</p>
    </section>
    <section class="space-y-2">
      <h2 class="text-base font-semibold text-ink">保存と削除</h2>
      <p>画像や解析結果はサーバーおよびCloudflare R2に保持されます。ライブラリのブックマークは画面から削除できます。他の資料や環境から参照されている画像、デモ用の共通画像、移行前のローカル画像やキャッシュは保持される場合があります。アカウント全体の削除機能や一律の保存期間は現在設けていません。</p>
    </section>
    <section class="space-y-2">
      <h2 class="text-base font-semibold text-ink">ゲスト利用に関する注意</h2>
      <p>未ログイン時は共通のゲストアカウントが使われます。共用環境ではゲスト領域に個人情報や非公開資料を保存しないでください。Pixiv連携の公開プレビューでの扱いは<NuxtLink to="/terms" class="text-brand hover:underline">利用上の注意</NuxtLink>も確認してください。</p>
    </section>
  </SiteInfoPage>
</template>
