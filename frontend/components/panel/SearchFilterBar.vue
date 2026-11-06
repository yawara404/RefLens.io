<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Search, X, Sparkles, Loader2, Tag } from 'lucide-vue-next'
import { useBoardStore } from '~/stores/boardStore'
import { useSearchSuggest } from '~/composables/useSearchSuggest'

const boardStore = useBoardStore()
const searchContainerRef = ref<HTMLElement | null>(null)
const isSuggestOpen = ref(false)

const {
  isPredicting,
  suggestions,
  predictionSource,
  queueQuery,
  clearSuggestions,
} = useSearchSuggest()

/** キャンバス上のアイテムから抽出したタグ（頻度順・最大12件） */
const availableTags = computed(() => {
  const counts = new Map<string, number>()
  for (const item of boardStore.items) {
    for (const tag of item.ai_analysis?.tags || []) {
      const t = tag.trim()
      if (t) counts.set(t, (counts.get(t) || 0) + 1)
    }
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 12)
    .map(([tag, count]) => ({ tag, count }))
})

/** クエリに合致するキャンバスタグ */
const matchingAvailableTags = computed(() => {
  const q = boardStore.searchQuery.toLowerCase().trim()
  if (!q) return availableTags.value
  return availableTags.value.filter(item => item.tag.toLowerCase().includes(q))
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

function selectSuggest(tag: string) {
  boardStore.searchQuery = tag
  isSuggestOpen.value = false
}

function clearSearch() {
  boardStore.searchQuery = ''
  clearSuggestions()
  boardStore.searchPredictedTags = []
  isSuggestOpen.value = false
}

function onDocumentClick(e: MouseEvent) {
  if (searchContainerRef.value && !searchContainerRef.value.contains(e.target as Node)) {
    isSuggestOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', onDocumentClick)
})

onUnmounted(() => {
  document.removeEventListener('click', onDocumentClick)
})
</script>

<template>
  <div ref="searchContainerRef" class="relative w-full">
    <!-- 検索入力 -->
    <div class="relative flex items-center w-full">
      <Search class="absolute left-3 w-3.5 h-3.5 text-ink-subtle pointer-events-none" />
      <input
        v-model="boardStore.searchQuery"
        type="search"
        placeholder="キャンバス内サジェスト検索 (タグ・構図・「女の子」など)..."
        class="w-full bg-canvas-bg border border-canvas-border-strong rounded-xl pl-8 pr-16 py-2 text-xs text-ink placeholder:text-ink-subtle focus:outline-none focus:border-brand transition-colors shadow-2xs"
        aria-label="キャンバス上の資料を検索"
        @focus="isSuggestOpen = true"
        @input="isSuggestOpen = true"
        @keydown.esc="isSuggestOpen = false"
      />

      <!-- 右端: 件数 + クリアボタン -->
      <div class="absolute right-2 flex items-center gap-1">
        <span
          v-if="isFiltering"
          class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-brand/10 text-brand font-bold shrink-0"
        >
          {{ matchCount }}/{{ boardStore.items.length }}
        </span>
        <button
          v-if="isFiltering"
          type="button"
          class="p-0.5 rounded-full text-ink-muted hover:text-ink transition-colors cursor-pointer"
          aria-label="検索をクリア"
          @click="clearSearch"
        >
          <X class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>

    <!-- 検索サジェスト ドロップダウン (タグ検索統合) -->
    <div
      v-if="isSuggestOpen"
      class="absolute top-full left-0 right-0 mt-1.5 z-50 bg-canvas-card border border-canvas-border shadow-2xl rounded-2xl overflow-hidden max-h-[320px] overflow-y-auto divide-y divide-canvas-border animate-in fade-in zoom-in-95 duration-100"
    >
      <!-- A. 入力がある時 -->
      <template v-if="boardStore.searchQuery.trim()">
        <!-- キャンバス上のタグ候補 -->
        <div v-if="matchingAvailableTags.length" class="p-2.5 space-y-1.5">
          <p class="text-[10px] font-bold uppercase tracking-wider text-brand flex items-center gap-1">
            <Tag class="w-3 h-3 text-brand" />
            <span>キャンバス上のタグ</span>
          </p>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="item in matchingAvailableTags"
              :key="'canvas-tag-' + item.tag"
              type="button"
              class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-brand text-brand-fg flex items-center gap-1 hover:brightness-110 active:scale-95 transition-all shadow-2xs cursor-pointer"
              @click="selectSuggest(item.tag)"
            >
              <span>#{{ item.tag }}</span>
              <span class="text-[10px] opacity-80 font-mono">({{ item.count }}枚)</span>
            </button>
          </div>
        </div>

        <!-- AI予測・関連キーワード -->
        <div v-if="suggestions.length" class="p-2.5 space-y-1.5">
          <div class="flex items-center justify-between">
            <p class="text-[10px] font-bold uppercase tracking-wider text-ink-muted flex items-center gap-1">
              <Sparkles class="w-3 h-3 text-brand" />
              <span>AI予測・関連キーワード</span>
            </p>
            <span v-if="isPredicting" class="text-[10px] text-brand flex items-center gap-1">
              <Loader2 class="w-2.5 h-2.5 animate-spin" />
              <span>推論中</span>
            </span>
          </div>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="sug in suggestions"
              :key="'canvas-sug-' + sug"
              type="button"
              class="px-2.5 py-1 rounded-lg text-xs font-medium border border-canvas-border hover:border-brand hover:text-brand bg-canvas-bg hover:bg-canvas-hover text-ink transition-all active:scale-95 cursor-pointer"
              @click="selectSuggest(sug)"
            >
              {{ sug }}
            </button>
          </div>
        </div>
      </template>

      <!-- B. 入力が空の時（フォーカス時クイックサジェスト） -->
      <template v-else>
        <!-- キャンバス上の主要タグ -->
        <div v-if="availableTags.length" class="p-2.5 space-y-1.5">
          <p class="text-[10px] font-bold uppercase tracking-wider text-ink-muted flex items-center gap-1">
            <Tag class="w-3 h-3 text-brand" />
            <span>キャンバス上のタグで絞り込み</span>
          </p>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="item in availableTags"
              :key="'canvas-init-tag-' + item.tag"
              type="button"
              class="px-2.5 py-1 rounded-full text-[11px] font-medium border border-canvas-border hover:border-brand bg-canvas-bg hover:bg-canvas-hover text-ink transition-all active:scale-95 cursor-pointer"
              @click="selectSuggest(item.tag)"
            >
              <span>#{{ item.tag }}</span>
              <span class="text-[10px] text-ink-muted font-mono">({{ item.count }})</span>
            </button>
          </div>
        </div>
        <div v-else class="p-3 text-center text-xs text-ink-muted">
          キャンバス上にAI解析済みタグ付きの資料がありません
        </div>
      </template>
    </div>
  </div>
</template>
