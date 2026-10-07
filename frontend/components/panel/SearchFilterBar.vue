<script setup lang="ts">
import { computed } from 'vue'
import { Search, X } from 'lucide-vue-next'
import { useBoardStore } from '~/stores/boardStore'

const boardStore = useBoardStore()

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

const matchCount = computed(() => boardStore.filteredItemIds.length)
const isFiltering = computed(() => !!boardStore.searchQuery.trim())

function toggleTag(tag: string) {
  boardStore.searchQuery = boardStore.searchQuery === tag ? '' : tag
}
</script>

<template>
  <!--
    min-w-0 を付け、子に shrink を指定する。
    これがないとヘッダーの左右（ナビゲーション / アクション）が
    狭い画面で重なってしまう。
  -->
  <div class="flex items-center gap-2 min-w-0">
    <!-- 検索入力 -->
    <div class="relative flex items-center shrink-0">
      <Search class="absolute left-3 w-3.5 h-3.5 text-ink-subtle pointer-events-none" />
      <input
        v-model="boardStore.searchQuery"
        type="search"
        placeholder="構図・ライティング・タグで検索"
        class="w-44 sm:w-64 bg-canvas-card border border-canvas-border rounded-full pl-8 pr-8 py-1.5 text-xs text-ink placeholder:text-ink-subtle focus:outline-none focus:border-brand transition-colors"
        aria-label="キャンバス上の資料を検索"
      />
      <button
        v-if="isFiltering"
        type="button"
        class="absolute right-2.5 p-0.5 rounded-full text-ink-muted hover:text-ink transition-colors"
        aria-label="検索をクリア"
        @click="boardStore.searchQuery = ''"
      >
        <X class="w-3.5 h-3.5" />
      </button>
    </div>

    <!-- タグクイックフィルター -->
    <div
      v-if="availableTags.length"
      class="hidden lg:flex items-center gap-1.5 overflow-x-auto min-w-0 max-w-sm no-scrollbar"
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