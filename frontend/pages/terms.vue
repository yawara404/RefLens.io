<script setup lang="ts">
import SiteInfoPage from '~/components/ui/SiteInfoPage.vue'

useHead({ title: '利用上の注意 | RefLens.io' })
</script>

<template>
  <SiteInfoPage title="利用上の注意" updated="2026年10月7日">
    <p>RefLens.ioは参考資料の整理・閲覧を支援するツールです。利用する画像やリンクの権利、公開範囲、外部サービスの条件を確認して使用してください。</p>
    <section class="space-y-2">
      <h2 class="text-base font-semibold text-ink">作品と外部サービス</h2>
      <p>作品の権利は各権利者に帰属します。Pixiv連携は非公式で、Pixivによる承認・保証を意味しません。画像の保存、再配布、二次利用については、作者の意思と各サービスの利用条件に従ってください。</p>
    </section>
    <section class="space-y-2">
      <h2 class="text-base font-semibold text-ink">AI解析</h2>
      <p>AI解析は作品の利用許諾を判断する機能ではありません。Pixiv作品に明示的なAI学習禁止の記載がある場合は解析を停止します。記載がない場合でも、Danbooruで同じPixiv作品IDの掲載を確認できたときだけ解析します。Danbooruへの掲載は作者の許諾の証明ではありません。解析結果は誤ることがあります。</p>
    </section>
    <section class="space-y-2">
      <h2 class="text-base font-semibold text-ink">ゲスト・公開環境</h2>
      <p>未ログイン時は共通のゲスト領域を使用します。共通ゲストにPixivのセッションは渡しません。公開プレビューではRefresh Tokenの手入力接続を無効にしており、接続は「Pixivでログイン」から行います。名指しされた管理者アカウントは公開URLでも既存の連携を引き継いで実データを表示します。公開サーバーを運用する場合は、個別のアクセス制御と保存先の分離を確認してください。</p>
    </section>
    <section class="space-y-2">
      <h2 class="text-base font-semibold text-ink">動作について</h2>
      <p>外部サービスの仕様変更や通信障害により、閲覧・取り込み・解析が利用できない場合があります。重要な資料は、必要に応じて元サービスや手元の環境でも管理してください。</p>
    </section>
  </SiteInfoPage>
</template>
