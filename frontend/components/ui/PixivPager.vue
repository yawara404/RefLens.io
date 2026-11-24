<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight, ChevronsLeft, Loader2 } from 'lucide-vue-next'

const props = withDefaults(defineProps<{
  /** 現在のページ番号（1始まり） */
  page: number
  /** 次ページが存在するか */
  hasNext: boolean
  /** 読み込み中は二重送信を防ぐため操作を無効化する */
  isLoading?: boolean
  /** コンパクト表示（最初へ / 前へ / 現在ページ / 次へ のみ） */
  compact?: boolean
  /** ページ番号を直接指定できるか（オフセット方式のフィードのみ true） */
  canJump?: boolean
  /** aria-label 用のコンテキスト（例: おすすめ） */
  contextLabel?: string
  /** nav の aria-label を明示したい場合（同じ画面に複数ページャーを置くとき） */
  ariaLabel?: string
}>(), {
  isLoading: false,
  compact: false,
  canJump: false,
  contextLabel: 'pixiv',
  ariaLabel: '',
})

const emit = defineEmits<{
  (e: 'prev'): void
  (e: 'next'): void
  (e: 'first'): void
  (e: 'go', page: number): void
}>()

/** pixiv API の page パラメータ上限 */
const MAX_PAGE = 100

/** 進めることが確実な最大ページ（次ページがある場合のみ +1） */
const maxKnownPage = computed(() => Math.min(MAX_PAGE, props.page + (props.hasNext ? 1 : 0)))

/** ページ番号ボタンの並び（1, …, 現在±1, 既知の最終ページ） */
const pageItems = computed<(number | 'ellipsis')[]>(() => {
  const pages = new Set<number>([1, maxKnownPage.value])
  for (let p = props.page - 1; p <= props.page + 1; p += 1) {
    if (p >= 1 && p <= maxKnownPage.value) pages.add(p)
  }
  const sorted = [...pages].sort((a, b) => a - b)
  const items: (number | 'ellipsis')[] = []
  let prev = 0
  for (const p of sorted) {
    if (prev && p - prev > 1) items.push('ellipsis')
    items.push(p)
    prev = p
  }
  return items
})

const jumpValue = ref('')

// ページが変わったら入力欄をリセットする
watch(() => props.page, () => {
  jumpValue.value = ''
})

function submitJump() {
  const digits = jumpValue.value.replace(/[^\d]/g, '')
  if (!digits) return
  const parsed = Number.parseInt(digits, 10)
  if (!Number.isFinite(parsed)) return
  emit('go', Math.min(MAX_PAGE, Math.max(1, parsed)))
  jumpValue.value = ''
}
</script>

<template>
  <!--
    relative は必須:
    下の aria-live 用 .sr-only は position:absolute なので、位置指定された祖先が無いと
    初期包含ブロック（= ページ全体）基準で配置され、スクロール領域を押し広げて
    ページ最下部に不要な空白（謎の隙間）を作ってしまう。
  -->
  <nav
    class="relative flex flex-wrap items-center justify-center gap-1.5"
    :aria-label="ariaLabel || `${contextLabel}のページ送り`"
    :aria-busy="isLoading"
  >
    <!-- 最初へ -->
    <button
      v-if="!compact"
      type="button"
      class="h-8 w-8 inline-flex items-center justify-center rounded-lg border border-canvas-border bg-canvas-card text-ink-muted hover:text-ink hover:bg-canvas-hover hover:border-canvas-border-strong transition-colors disabled:opacity-40 disabled:pointer-events-none"
      :disabled="isLoading || page <= 1"
      title="最初のページへ"
      aria-label="最初のページへ"
      @click="emit('first')"
    >
      <ChevronsLeft class="w-4 h-4" />
    </button>

    <!-- 前へ -->
    <button
      type="button"
      class="h-8 px-2 sm:px-2.5 inline-flex items-center gap-0.5 rounded-lg border border-canvas-border bg-canvas-card text-xs font-semibold text-ink-muted hover:text-ink hover:bg-canvas-hover hover:border-canvas-border-strong transition-colors disabled:opacity-40 disabled:pointer-events-none"
      :disabled="isLoading || page <= 1"
      title="前のページへ"
      aria-label="前のページへ"
      @click="emit('prev')"
    >
      <ChevronLeft class="w-4 h-4 shrink-0" />
      <span class="hidden sm:inline">前へ</span>
    </button>

    <!-- ページ番号（コンパクト時は現在ページのみ） -->
    <template v-if="compact">
      <span
        class="h-8 min-w-8 px-2 inline-flex items-center justify-center rounded-lg border border-pixiv bg-pixiv text-white text-xs font-bold font-mono shadow-sm"
        aria-current="page"
        :aria-label="`${page} ページ目`"
      >
        <Loader2 v-if="isLoading" class="w-3.5 h-3.5 animate-spin" />
        <span v-else>{{ page }}</span>
      </span>
    </template>
    <template v-else>
      <template v-for="(item, index) in pageItems" :key="`${item}-${index}`">
        <span
          v-if="item === 'ellipsis'"
          class="px-0.5 text-xs text-ink-subtle select-none"
          aria-hidden="true"
        >…</span>
        <button
          v-else
          type="button"
          class="h-8 min-w-8 px-2 inline-flex items-center justify-center rounded-lg border text-xs font-mono transition-colors disabled:opacity-60"
          :class="item === page
            ? 'border-pixiv bg-pixiv text-white font-bold shadow-sm'
            : 'border-canvas-border bg-canvas-card text-ink-muted hover:text-ink hover:bg-canvas-hover hover:border-canvas-border-strong'"
          :disabled="isLoading"
          :aria-current="item === page ? 'page' : undefined"
          :aria-label="`${item} ページ目へ`"
          @click="emit('go', item)"
        >
          {{ item }}
        </button>
      </template>
    </template>

    <!-- 次へ -->
    <button
      type="button"
      class="h-8 px-2 sm:px-2.5 inline-flex items-center gap-0.5 rounded-lg border border-canvas-border bg-canvas-card text-xs font-semibold text-ink-muted hover:text-ink hover:bg-canvas-hover hover:border-canvas-border-strong transition-colors disabled:opacity-40 disabled:pointer-events-none"
      :disabled="isLoading || !hasNext"
      title="次のページへ"
      aria-label="次のページへ"
      @click="emit('next')"
    >
      <span class="hidden sm:inline">次へ</span>
      <ChevronRight class="w-4 h-4 shrink-0" />
    </button>

    <!-- ページ指定 -->
    <form
      v-if="!compact && canJump"
      class="flex items-center gap-1 sm:ml-1"
      @submit.prevent="submitJump"
    >
      <input
        v-model="jumpValue"
        type="text"
        inputmode="numeric"
        pattern="[0-9]*"
        placeholder="ページ"
        aria-label="移動するページ番号"
        class="h-8 w-16 rounded-lg border border-canvas-border-strong bg-canvas-bg px-2 text-xs font-mono text-ink placeholder:text-ink-subtle focus:outline-none focus:border-pixiv transition-colors disabled:opacity-40"
        :disabled="isLoading"
      >
      <button
        type="submit"
        class="h-8 px-2.5 rounded-lg border border-canvas-border-strong bg-canvas-bg text-xs font-semibold text-ink hover:bg-canvas-hover transition-colors disabled:opacity-40 disabled:pointer-events-none"
        :disabled="isLoading || !jumpValue"
      >
        移動
      </button>
    </form>

    <span class="sr-only" aria-live="polite">{{ page }} ページ目</span>
  </nav>
</template>

