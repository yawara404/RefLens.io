<script setup lang="ts">
import { computed } from 'vue'
import type { NuxtError } from '#app'
import { ArrowLeft, Compass, Home, RefreshCw } from 'lucide-vue-next'
import { themeInitScript } from '~/composables/useTheme'

const props = defineProps<{ error: NuxtError }>()

// error.vue は app.vue を置き換えて描画されるため、テーマの初期化をここでも行う。
useHead(() => ({
  script: [{ innerHTML: themeInitScript, tagPosition: 'head' as const }],
  title: `${props.error?.statusCode || 500} | RefLens.io`,
  meta: [{ name: 'robots', content: 'noindex' }],
}))

const statusCode = computed(() => props.error?.statusCode || 500)
const isNotFound = computed(() => statusCode.value === 404)

const title = computed(() =>
  isNotFound.value ? 'このページは見つかりません' : 'ページを表示できませんでした'
)
const description = computed(() =>
  isNotFound.value
    ? 'URLが変更されたか、削除された可能性があります。下のボタンから戻ってください。'
    : '一時的な問題の可能性があります。再読み込みしても直らない場合は、少し時間をおいてからお試しください。'
)

function goHome() {
  void clearError({ redirect: '/' })
}

function goBack() {
  if (import.meta.server) return
  // 履歴が無い（直接開いた）場合はトップへ。
  if (window.history.length > 1) window.history.back()
  else goHome()
}

function reload() {
  if (import.meta.server) return
  window.location.reload()
}
</script>

<template>
  <div class="min-h-screen bg-canvas-bg text-ink antialiased flex items-center justify-center p-5">
    <main id="main-content" class="w-full max-w-md text-center space-y-5">
      <div class="mx-auto w-12 h-12 rounded-2xl bg-brand-soft text-brand flex items-center justify-center">
        <Compass class="w-6 h-6" />
      </div>

      <div class="space-y-1.5">
        <p class="text-[11px] font-mono font-bold tracking-widest text-ink-subtle">
          ERROR {{ statusCode }}
        </p>
        <h1 class="text-lg font-bold text-ink leading-snug">{{ title }}</h1>
        <p class="text-xs text-ink-muted leading-relaxed">{{ description }}</p>
      </div>

      <div class="flex flex-col sm:flex-row items-stretch justify-center gap-2">
        <button
          type="button"
          class="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl bg-brand text-brand-fg text-xs font-bold hover:bg-brand-hover transition-colors"
          @click="goHome"
        >
          <Home class="w-3.5 h-3.5" />
          トップへ戻る
        </button>
        <button
          type="button"
          class="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl border border-canvas-border bg-canvas-panel text-xs font-semibold text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          @click="goBack"
        >
          <ArrowLeft class="w-3.5 h-3.5" />
          前のページへ
        </button>
        <button
          type="button"
          class="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl border border-canvas-border bg-canvas-panel text-xs font-semibold text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          @click="reload"
        >
          <RefreshCw class="w-3.5 h-3.5" />
          再読み込み
        </button>
      </div>

      <p class="text-[11px] text-ink-subtle">
        問題が続く場合は
        <NuxtLink to="/help" class="text-brand underline underline-offset-2">ヘルプ</NuxtLink>
        をご確認ください。
      </p>
    </main>
  </div>
</template>
