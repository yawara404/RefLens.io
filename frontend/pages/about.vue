<script setup lang="ts">
import SiteInfoPage from '~/components/ui/SiteInfoPage.vue'
import { useSeo } from '~/composables/useSeo'

useSeo({
  title: 'RefLens.io とは？イラストの参考資料整理ツール',
  description: 'RefLens.ioは、画像やWeb上の参考資料をライブラリにまとめ、無限キャンバスで見比べられる、イラストやデザイン向けの制作支援ツールです。',
  path: '/about',
})
</script>

<template>
  <SiteInfoPage title="RefLens.io でできること">
    <p>RefLens.io は、イラストやデザインの参考資料を、集めるところから作業中に見比べるところまでブラウザで扱えるツールです。</p>
    <section class="space-y-2">
      <h2 class="text-base font-semibold text-ink">画像とリンクをフォルダ・タグで整理</h2>
      <p>手持ちの画像をドラッグ＆ドロップしたり、WebページのURLを貼り付けたりして、Managerに資料を集めます。作品ごとにフォルダを作り、「衣装」「ポーズ」「背景」などのタグを付けておくと、別の制作でも資料を探し直せます。</p>
    </section>
    <section class="space-y-2">
      <h2 class="text-base font-semibold text-ink">無限キャンバスで構図や配色を見比べる</h2>
      <p>Canvasでは、集めた画像を自由に配置・拡大縮小・回転できます。たとえば、キャラクターのポーズと衣装の資料を横に並べ、背景に使いたい色を近くに置いて、ラフを描く前に全体を確認できます。</p>
      <p>画像の取り込みから配置までの操作は、<NuxtLink to="/help" class="text-brand hover:underline">RefLens.io の使い方</NuxtLink>で確認できます。</p>
    </section>
    <section class="space-y-2">
      <h2 class="text-base font-semibold text-ink">外部サービスとの関係</h2>
      <p>Pixiv連携は非公式の機能であり、RefLens.ioはPixiv、Danbooru、Instagramの公式サービスではありません。各サービスの利用条件と作品の権利を尊重して利用してください。</p>
    </section>
    <p>データの扱いは<NuxtLink to="/privacy" class="text-brand hover:underline">プライバシーポリシー</NuxtLink>、利用時の注意点は<NuxtLink to="/terms" class="text-brand hover:underline">利用上の注意</NuxtLink>をご覧ください。</p>
  </SiteInfoPage>
</template>
