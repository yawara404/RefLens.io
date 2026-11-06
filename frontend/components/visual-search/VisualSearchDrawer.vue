<script setup lang="ts">
import { computed } from 'vue'
import {
  Sparkles,
  X,
  Plus,
  Eye,
  Folder,
  Layers,
  Palette,
  Loader2,
  Check,
  ExternalLink,
} from 'lucide-vue-next'
import { useVisualSearch, type VisualSearchMatch } from '~/composables/useVisualSearch'
import { useBoardStore } from '~/stores/boardStore'
import { useMediaUrl } from '~/composables/useMediaUrl'

const {
  isDrawerOpen,
  isSearching,
  searchResult,
  closeDrawer,
  placeMatchOnCanvas,
} = useVisualSearch()

const boardStore = useBoardStore()
const { resolveMediaUrl } = useMediaUrl()

function openQuickLook(match: VisualSearchMatch) {
  const bookmark = boardStore.bookmarks.find(b => b.id === match.id)
  if (bookmark) {
    boardStore.openQuickLook(bookmark)
  }
}
</script>

<template>
  <!-- 背景クリックで閉じる scrim (モバイル時) -->
  <Transition
    enter-active-class="transition-opacity ease-out duration-300"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition-opacity ease-in duration-200"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="isDrawerOpen"
      class="fixed inset-0 z-[80] bg-slate-950/40 backdrop-blur-sm sm:hidden"
      @click="closeDrawer"
    />
  </Transition>

  <!-- Galaxy AI ドロワーパネル (画面右側からスライドイン、または下部) -->
  <Transition
    enter-active-class="transition-transform ease-out duration-300"
    enter-from-class="translate-y-full sm:translate-y-0 sm:translate-x-full"
    enter-to-class="translate-y-0 sm:translate-x-0"
    leave-active-class="transition-transform ease-in duration-200"
    leave-from-class="translate-y-0 sm:translate-x-0"
    leave-to-class="translate-y-full sm:translate-y-0 sm:translate-x-full"
  >
    <aside
      v-if="isDrawerOpen"
      class="fixed right-0 bottom-0 sm:top-14 w-full sm:w-[420px] max-h-[85vh] sm:max-h-none h-auto sm:h-[calc(100vh-3.5rem)] z-[85] bg-canvas-card border-t sm:border-t-0 sm:border-l border-canvas-border-strong flex flex-col shadow-2xl overflow-hidden rounded-t-2xl sm:rounded-none"
      role="dialog"
      aria-label="Galaxy AI 視覚検索結果"
    >
      <!-- ドロワーヘッダー (Galaxy AI風グラデーションバー) -->
      <header class="p-3.5 border-b border-canvas-border flex items-center justify-between shrink-0 bg-canvas-bg/60 backdrop-blur">
        <div class="flex items-center gap-2">
          <div class="w-6 h-6 rounded-lg bg-gradient-to-tr from-cyan-400 via-indigo-500 to-pink-500 flex items-center justify-center shadow-md">
            <Sparkles class="w-3.5 h-3.5 text-white animate-pulse" />
          </div>
          <div>
            <h2 class="text-xs font-bold text-ink flex items-center gap-1.5">
              <span class="bg-gradient-to-r from-cyan-500 via-indigo-500 to-pink-500 bg-clip-text text-transparent">
                Galaxy AI 視覚検索
              </span>
            </h2>
            <p class="text-[10px] text-ink-muted">かこみ選択領域の類似資料</p>
          </div>
        </div>

        <button
          type="button"
          class="p-1 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
          aria-label="ドロワーを閉じる"
          @click="closeDrawer"
        >
          <X class="w-4 h-4" />
        </button>
      </header>

      <!-- ローディング表示 -->
      <div v-if="isSearching" class="flex-1 p-6 flex flex-col items-center justify-center gap-3 text-center">
        <div class="relative w-12 h-12 flex items-center justify-center">
          <div class="absolute inset-0 rounded-full border-2 border-brand/30 border-t-brand animate-spin" />
          <Sparkles class="w-5 h-5 text-brand animate-pulse" />
        </div>
        <p class="text-xs font-bold text-ink">Galaxy AI が視覚要素を解析中...</p>
        <p class="text-[11px] text-ink-muted">構図・衣装・ライティング・色彩からライブラリ内を検索しています</p>
      </div>

      <!-- 解析結果 & 類似資料リスト -->
      <div v-else-if="searchResult" class="flex-1 overflow-y-auto p-3.5 space-y-3.5">
        <!-- かこった領域の解析サマリーカード -->
        <div class="p-3 rounded-xl bg-canvas-bg border border-canvas-border space-y-2">
          <div class="flex items-start gap-3">
            <!-- クロップサムネイル -->
            <div
              v-if="searchResult.crop_thumbnail"
              class="w-16 h-16 rounded-lg overflow-hidden shrink-0 border-2 border-indigo-500/40 shadow-sm bg-black/10 flex items-center justify-center"
            >
              <img
                :src="searchResult.crop_thumbnail"
                alt="かこみ領域"
                class="w-full h-full object-cover"
              />
            </div>
            <div class="flex-1 min-w-0">
              <span class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-brand/10 text-brand">
                ✨ 検出された特徴
              </span>
              <p class="text-xs font-bold text-ink mt-1 truncate">
                {{ searchResult.detected.summary }}
              </p>
              <div v-if="searchResult.detected.composition || searchResult.detected.lighting" class="text-[11px] text-ink-muted mt-0.5 truncate">
                <span>{{ [searchResult.detected.composition, searchResult.detected.lighting].filter(Boolean).join(' ・ ') }}</span>
              </div>
            </div>
          </div>

          <!-- 検出タグ一覧 -->
          <div v-if="searchResult.detected.tags.length" class="flex flex-wrap gap-1 pt-1 border-t border-canvas-border">
            <span
              v-for="tag in searchResult.detected.tags"
              :key="tag"
              class="px-2 py-0.5 rounded-md text-[10px] font-medium bg-canvas-card border border-canvas-border text-ink"
            >
              #{{ tag }}
            </span>
          </div>

          <!-- 検出カラーパレット -->
          <div v-if="searchResult.detected.palette.length" class="flex items-center gap-1.5 pt-0.5">
            <span class="text-[10px] text-ink-muted flex items-center gap-1">
              <Palette class="w-2.5 h-2.5 text-brand" />
              <span>色彩:</span>
            </span>
            <div class="flex items-center gap-1">
              <span
                v-for="hex in searchResult.detected.palette"
                :key="hex"
                class="w-3.5 h-3.5 rounded-full border border-black/20 shadow-xs"
                :style="{ backgroundColor: hex }"
                :title="hex"
              />
            </div>
          </div>
        </div>

        <!-- 類似資料一覧見出し -->
        <div class="flex items-center justify-between pt-1">
          <span class="text-xs font-bold text-ink flex items-center gap-1.5">
            <Layers class="w-3.5 h-3.5 text-brand" />
            <span>類似するリファレンス資料</span>
          </span>
          <span class="text-[11px] font-mono text-ink-muted">
            {{ searchResult.matches.length }} 件
          </span>
        </div>

        <!-- マッチ一覧 -->
        <div v-if="searchResult.matches.length" class="space-y-2">
          <article
            v-for="item in searchResult.matches"
            :key="item.id"
            class="p-2.5 rounded-xl bg-canvas-card border border-canvas-border hover:border-brand/40 transition-all flex items-start gap-2.5 group"
          >
            <!-- サムネイル -->
            <div
              class="w-14 h-14 rounded-lg overflow-hidden shrink-0 border border-canvas-border bg-black/5 cursor-pointer"
              @click="openQuickLook(item)"
            >
              <img
                :src="resolveMediaUrl(item.file_path)"
                :alt="item.title"
                class="w-full h-full object-cover group-hover:scale-105 transition-transform"
                loading="lazy"
              />
            </div>

            <!-- 情報 -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between gap-1">
                <span class="text-xs font-bold text-ink truncate cursor-pointer hover:text-brand" @click="openQuickLook(item)">
                  {{ item.title }}
                </span>
                <span class="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-brand text-brand-fg shrink-0 shadow-xs">
                  {{ item.similarity }}% 一致
                </span>
              </div>

              <!-- 一致した理由 -->
              <div v-if="item.reasons.length" class="flex flex-wrap gap-1 mt-1">
                <span
                  v-for="(r, idx) in item.reasons"
                  :key="idx"
                  class="text-[10px] px-1.5 py-0.5 rounded bg-brand/10 text-brand font-medium truncate max-w-full"
                >
                  ✨ {{ r }}
                </span>
              </div>

              <!-- アクションボタン -->
              <div class="flex items-center justify-end gap-1.5 mt-2">
                <button
                  type="button"
                  class="px-2 py-1 rounded-lg text-[10px] font-semibold text-ink-muted hover:text-ink bg-canvas-bg hover:bg-canvas-hover border border-canvas-border transition-colors flex items-center gap-1"
                  @click="openQuickLook(item)"
                >
                  <Eye class="w-3 h-3" />
                  <span>プレビュー</span>
                </button>
                <button
                  type="button"
                  class="px-2.5 py-1 rounded-lg text-[10px] font-bold text-brand-fg bg-brand hover:brightness-110 active:scale-95 transition-all flex items-center gap-1 shadow-xs"
                  @click="placeMatchOnCanvas(item)"
                >
                  <Plus class="w-3 h-3" />
                  <span>キャンバスに配置</span>
                </button>
              </div>
            </div>
          </article>
        </div>

        <!-- 0件のとき -->
        <div v-else class="p-6 rounded-xl bg-canvas-bg border border-canvas-border text-center space-y-2">
          <Sparkles class="w-6 h-6 text-ink-muted mx-auto" />
          <p class="text-xs font-bold text-ink">類似する資料が見つかりませんでした</p>
          <p class="text-[11px] text-ink-muted">別の部分を囲むか、新しい資料を追加してみてください</p>
        </div>
      </div>
    </aside>
  </Transition>
</template>
