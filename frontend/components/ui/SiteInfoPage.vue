<script setup lang="ts">
import AppHeader from '~/components/ui/AppHeader.vue'

// eyebrow は省略時も従来どおりサイト情報ページ向けの表記にする
defineProps<{ title: string; updated?: string; eyebrow?: string }>()
</script>

<template>
  <div class="min-h-screen bg-canvas-bg text-ink flex flex-col">
    <AppHeader />
    <main class="w-full max-w-3xl mx-auto flex-1 px-5 py-10 sm:py-14">
      <p class="text-[11px] font-mono uppercase tracking-widest text-brand">{{ eyebrow || 'RefLens.io / Site information' }}</p>
      <h1 class="mt-2 text-2xl sm:text-3xl font-bold tracking-tight">{{ title }}</h1>
      <p v-if="updated" class="mt-2 text-xs text-ink-subtle">更新日: {{ updated }}</p>
      <div class="mt-8 space-y-7 text-sm leading-7 text-ink-muted">
        <slot />
      </div>
    </main>
    <footer class="border-t border-canvas-border bg-canvas-panel px-5 py-5 text-xs text-ink-muted">
      <nav class="max-w-3xl mx-auto flex flex-wrap items-center gap-x-5 gap-y-2" aria-label="フッターナビゲーション">
        <span class="font-semibold text-ink">RefLens.io</span>
        <NuxtLink to="/about" class="hover:text-brand">このサイトについて</NuxtLink>
        <NuxtLink to="/privacy" class="hover:text-brand">プライバシー</NuxtLink>
        <NuxtLink to="/terms" class="hover:text-brand">利用上の注意</NuxtLink>
      </nav>
    </footer>
  </div>
</template>
