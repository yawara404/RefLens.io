<script setup lang="ts">
import { computed, watch } from 'vue'
import { Search, X, Sparkles, Loader2 } from 'lucide-vue-next'
import { useBoardStore } from '~/stores/boardStore'
import { useSearchSuggest } from '~/composables/useSearchSuggest'

const boardStore = useBoardStore()
const {
  isPredicting,
  suggestions,
  predictionSource,
  queueQuery,
  clearSuggestions,
} = useSearchSuggest()

/** キャンバス上のアイテムから抽出したタグ（頻度順・最大10件） */
const availableTags = computed(() => {
  const counts = new Map<string, number>()
  for (const item of boardStore.items) {
    for (const tag of item.ai_analysis?.tags || []) {
      counts.set(tag, (counts.get(tag) || 0) + 1)
    }
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([tag]) => tag)
})

watch(
  () => boardStore.searchQuery,
  (newVal) => {
    if (newVal.trim()) {
      queueQuery(newVal)
    } else {
      clearSuggestions()
      boardStore.searchPredictedTags = []
    }
  }
)

watch(suggestions, (newSug) => {
  boardStore.searchPredictedTags = newSug
})

const matchCount = computed(() => boardStore.filteredItemIds.length)
const isFiltering = computed(() => !!boardStore.searchQuery.trim())

function toggleTag(tag: string) {
  boardStore.searchQuery = boardStore.searchQuery === tag ? '' : tag
}

function applySuggestion(tag: string) {
  boardStore.searchQuery = tag
}
</script>

<template>
  <div class="flex flex-col xl:flex-row xl:items-center gap-2 min-w-0 w-full">
    <!-- 検索入力 -->
    <div class="relative flex items-center w-full xl:w-64 shrink-0">
      <Search class="absolute left-3 w-3.5 h-3.5 text-ink-subtle pointer-events-none" />
      <input
        v-model="boardStore.searchQuery"
        type="search"
        placeholder="構図・ライティング・タグで検索（例: 女の子）"
        class="w-full bg-canvas-bg xl:bg-canvas-card border border-canvas-border-strong xl:border-canvas-border rounded-xl xl:rounded-full pl-8 pr-8 py-2 xl:py-1.5 text-xs text-ink placeholder:text-ink-subtle focus:outline-none focus:border-brand transition-colors"
        aria-label="キャンバス上の資料を検索"
      />
      <button
        v-if="isFiltering"
        type="button"
        class="absolute right-2.5 p-0.5 rounded-full text-ink-muted hover:text-ink transition-colors"
        aria-label="検索をクリア"
        @click="boardStore.searchQuery = ''; clearSuggestions(); boardStore.searchPredictedTags = []"
      >
        <X class="w-3.5 h-3.5" />
      </button>
    </div>

    <!-- AI予測候補タグ（検索入力がある時） -->
    <div
      v-if="isFiltering && (suggestions.length || isPredicting)"
      class="flex items-center gap-1.5 overflow-x-auto min-w-0 max-w-full xl:max-w-md no-scrollbar py-0.5"
    >
      <span class="text-[10px] font-semibold text-brand flex items-center gap-0.5 shrink-0 px-1.5 py-0.5 rounded bg-brand/10">
        <Sparkles class="w-2.5 h-2.5" :class="{ 'animate-pulse': isPredicting }" />
        <span>AI予測:</span>
      </span>
      <span v-if="isPredicting && !suggestions.length" class="text-[10px] text-ink-muted flex items-center gap-1 shrink-0">
        <Loader2 class="w-2.5 h-2.5 animate-spin text-brand" />
        <span>推論中...</span>
      </span>
      <button
        v-for="sug in suggestions"
        :key="sug"
        type="button"
        class="px-2 py-0.5 rounded-full text-[10px] whitespace-nowrap transition-colors border shrink-0"
        :class="boardStore.searchQuery.toLowerCase() === sug.toLowerCase()
          ? 'bg-brand border-brand text-brand-fg font-bold'
          : 'bg-canvas-card border-brand/30 text-ink hover:border-brand hover:text-brand hover:bg-canvas-hover'"
        :title="`「${sug}」で検索`"
        @click="applySuggestion(sug)"
      >
        {{ sug }}
      </button>
    </div>

    <!-- キャンバスタグクイックフィルター（入力がない時） -->
    <div
      v-else-if="availableTags.length"
      class="flex flex-wrap xl:flex-nowrap items-center gap-1.5 xl:overflow-x-auto min-w-0 max-w-full xl:max-w-sm no-scrollbar"
    >
      <button
        v-for="tag in availableTags"
        :key="tag"
        type="button"
        class="px-2.5 py-1 rounded-full text-[11px] whitespace-nowrap transition-colors border"
        :class="boardStore.searchQuery === tag
          ? 'bg-brand border-brand text-brand-fg'
          : 'bg-canvas-card border-canvas-border text-ink-muted hover:text-ink hover:bg-canvas-hover'"
        :aria-pressed="boardStore.searchQuery === tag"
        @click="toggleTag(tag)"
      >
        #{{ tag }}
      </button>
    </div>

    <!-- ヒット件数 -->
    <span
      v-if="isFiltering"
      class="text-[11px] font-mono text-ink-subtle whitespace-nowrap"
    >
      {{ matchCount }}/{{ boardStore.items.length }}
    </span>
  </div>
</template>
