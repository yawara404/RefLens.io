<script setup lang="ts">
import SiteInfoPage from '~/components/ui/SiteInfoPage.vue'
import { useSeo } from '~/composables/useSeo'

useSeo({
  title: '利用上の注意 | RefLens.io',
  description: 'RefLens.ioを利用するときの注意事項。作品の権利、外部サービスとの関係、AI解析と公開環境の扱いについてまとめています。',
  path: '/terms',
})
</script>

<template>
  <SiteInfoPage title="利用上の注意" updated="2026年11月12日">
    <p>RefLens.ioは参考資料の整理・閲覧を支援するツールです。利用する画像やリンクの権利、公開範囲、外部サービスの条件を確認して使用してください。</p>
    <section class="space-y-2">
      <h2 class="text-base font-semibold text-ink">作品と外部サービス</h2>
      <p>作品の権利は各権利者に帰属します。Pixiv連携は非公式で、Pixivによる承認・保証を意味しません。画像の保存、再配布、二次利用については、作者の意思と各サービスの利用条件に従ってください。</p>
    </section>
    <section class="space-y-2">
      <h2 class="text-base font-semibold text-ink">AI解析</h2>
      <p>AI解析は作品の利用許諾を判断する機能ではありません。RefLens.ioのAI解析は、取り込んだ画像をモデルの学習（追加トレーニング）に利用しない、推論専用の情報解析（構図・光・ポーズ・衣装・配色の読み取りと自動タグ付け）です。取り込んだ作品はすべて解析の対象となり、作品側のAI学習禁止などの表記によって解析を停止することはありません。自動AIタグ付けはアカウント設定から停止できます。解析結果は誤ることがあります。</p>
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
