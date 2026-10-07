<script setup lang="ts">
import SiteInfoPage from '~/components/ui/SiteInfoPage.vue'

useHead({ title: 'このサイトについて | RefLens.io' })
</script>

<template>
  <SiteInfoPage title="このサイトについて">
    <p>RefLens.ioは、画像やWeb上の参考資料をライブラリにまとめ、キャンバス上で並べて見られる制作支援ツールです。</p>
    <section class="space-y-2">
      <h2 class="text-base font-semibold text-ink">主な機能</h2>
      <p>Managerで資料を整理し、ViewでPixiv作品を閲覧し、Canvasで資料を配置できます。対応する画像には構図・光・色などのAI解析を表示できます。</p>
    </section>
    <section class="space-y-2">
      <h2 class="text-base font-semibold text-ink">外部サービスとの関係</h2>
      <p>Pixiv連携は非公式の機能であり、RefLens.ioはPixiv、Danbooru、Instagramの公式サービスではありません。各サービスの利用条件と作品の権利を尊重して利用してください。</p>
    </section>
    <p>データの扱いは<NuxtLink to="/privacy" class="text-brand hover:underline">プライバシーポリシー</NuxtLink>、利用時の注意点は<NuxtLink to="/terms" class="text-brand hover:underline">利用上の注意</NuxtLink>をご覧ください。</p>
  </SiteInfoPage>
</template>
