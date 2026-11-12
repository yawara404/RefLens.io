<script setup lang="ts">
import { onMounted, onUnmounted, computed, ref, watch, nextTick } from 'vue'
import {
  X,
  ExternalLink,
  Plus,
  Sparkles,
  Instagram,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Check,
  Copy,
  Tag,
} from 'lucide-vue-next'
import { useBoardStore } from '~/stores/boardStore'
import { useMediaUrl } from '~/composables/useMediaUrl'
import { useImageProcessor } from '~/composables/useImageProcessor'
import { useToast } from '~/composables/useToast'
import { useDialogA11y } from '~/composables/useDialogA11y'
import { isTypingTarget } from '~/utils/dom'

const boardStore = useBoardStore()
const toast = useToast()
const { resolveMediaUrl } = useMediaUrl()
const { copyToClipboard } = useImageProcessor()

const item = computed(() => boardStore.quickLookItem)

// モーダル共通のキーボード操作とフォーカス管理。
const { dialogRef } = useDialogA11y(computed(() => !!item.value), () => boardStore.closeQuickLook())
const closeBtnRef = ref<HTMLButtonElement | null>(null)
const copiedHex = ref<string | null>(null)
let touchStartX = 0
let touchStartY = 0

function onTouchStart(e: TouchEvent) {
  if (e.touches.length !== 1) return
  touchStartX = e.touches[0].clientX
  touchStartY = e.touches[0].clientY
}

function onTouchEnd(e: TouchEvent) {
  if (e.changedTouches.length !== 1) return
  const dx = e.changedTouches[0].clientX - touchStartX
  const dy = e.changedTouches[0].clientY - touchStartY
  if (Math.abs(dx) > 48 && Math.abs(dx) > Math.abs(dy) * 1.4) {
    if (dx > 0) prevItem()
    else nextItem()
  }
}

const bookmarkList = computed(() =>
  boardStore.filteredBookmarks.length ? boardStore.filteredBookmarks : boardStore.bookmarks
)

const currentIndex = computed(() => {
  if (!item.value) return -1
  return bookmarkList.value.findIndex(b => b.id === item.value?.id)
})

const hasPrev = computed(() => currentIndex.value > 0)
const hasNext = computed(() => currentIndex.value >= 0 && currentIndex.value < bookmarkList.value.length - 1)

function prevItem() {
  if (hasPrev.value) {
    boardStore.openQuickLook(bookmarkList.value[currentIndex.value - 1])
  }
}

function nextItem() {
  if (hasNext.value) {
    boardStore.openQuickLook(bookmarkList.value[currentIndex.value + 1])
  }
}

function resolveImageUrl(path?: string) {
  return resolveMediaUrl(path)
}

async function copyHex(hex: string) {
  if (await copyToClipboard(hex)) {
    copiedHex.value = hex
    toast.success(`カラーコード ${hex} をコピーしました`)
    setTimeout(() => {
      if (copiedHex.value === hex) copiedHex.value = null
    }, 1400)
  } else {
    toast.error('クリップボードにコピーできませんでした')
  }
}

async function copySourceUrl() {
  if (!item.value?.source_url) return
  if (await copyToClipboard(item.value.source_url)) {
    toast.success('元のページURLをコピーしました')
  } else {
    toast.error('クリップボードにコピーできませんでした')
  }
}

async function placeOnCanvas() {
  if (!boardStore.quickLookItem) return
  const bookmarkId = boardStore.quickLookItem.id
  if (!boardStore.currentBoard) {
    await boardStore.loadFirstBoard()
  }
  const placed = await boardStore.placeBookmarkOnBoard(bookmarkId, 150, 150)
  if (!placed) return
  toast.success('キャンバスへ配置しました')
  boardStore.closeQuickLook()
}

async function removeFromLibrary() {
  if (!boardStore.quickLookItem) return
  const deleted = await boardStore.deleteBookmark(boardStore.quickLookItem.id)
  if (!deleted) return
  toast.success('ライブラリから削除しました')
  boardStore.closeQuickLook()
}

const isAddingTag = ref(false)
const newTagInput = ref('')
const tagInputRef = ref<HTMLInputElement | null>(null)
const isAnalyzing = ref(false)

const itemTags = computed(() => {
  return item.value?.ai_analysis?.tags || []
})

function openAddTag() {
  isAddingTag.value = true
  newTagInput.value = ''
  nextTick(() => {
    tagInputRef.value?.focus()
  })
}

async function handleAddTag() {
  const val = newTagInput.value.trim().replace(/^#/, '')
  if (!val || !item.value) return
  newTagInput.value = ''
  isAddingTag.value = false
  await boardStore.addBookmarkTag(item.value.id, val)
}

async function handleRemoveTag(tag: string) {
  if (!item.value) return
  await boardStore.removeBookmarkTag(item.value.id, tag)
}

async function handleTriggerAi() {
  if (!item.value || isAnalyzing.value) return
  isAnalyzing.value = true
  try {
    await boardStore.triggerAiAnalysis(item.value.id)
  } finally {
    setTimeout(() => {
      isAnalyzing.value = false
    }, 3500)
  }
}

function onKeyDown(e: KeyboardEvent) {
  if (e.defaultPrevented || e.isComposing || !boardStore.quickLookItem) return
  if (!dialogRef.value?.contains(e.target as Node)) return
  if (isTypingTarget(e.target)) return

  if ((e.key === ' ' || e.key === 'Enter') && (e.target as HTMLElement)?.closest('button, a, [role="button"]')) return
  if (e.key === 'Escape' || e.key === ' ') {
    e.preventDefault()
    boardStore.closeQuickLook()
  } else if (e.key === 'Enter') {
    e.preventDefault()
    placeOnCanvas()
  } else if (e.key === 'ArrowLeft') {
    e.preventDefault()
    prevItem()
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    nextItem()
  }
}

watch(
  () => item.value?.id,
  async (newId, oldId) => {
    if (newId && !oldId) {
      await nextTick()
      closeBtnRef.value?.focus()
    }
  }
)

onMounted(() => window.addEventListener('keydown', onKeyDown))
onUnmounted(() => window.removeEventListener('keydown', onKeyDown))
</script>

<template>
  <Teleport to="body">
    <div
      v-if="item"
      class="fixed inset-0 z-[65] flex items-end sm:items-center justify-center p-2 sm:p-4 md:p-6 scrim animate-fade-in"
      @click.self="boardStore.closeQuickLook"
    >
      <div
        class="w-full max-w-4xl max-h-[92dvh] sm:max-h-[85vh] rounded-2xl border border-canvas-border bg-canvas-panel shadow-pop overflow-hidden flex flex-col md:flex-row animate-scale-in"
        ref="dialogRef" role="dialog"
        aria-modal="true"
        :aria-label="item.title"
      >
        <!-- 画像 -->
        <div
          class="flex-1 bg-canvas-sunken relative flex items-center justify-center p-3 sm:p-4 min-h-[200px] max-h-[44dvh] md:max-h-none md:min-h-[300px] shrink-0 md:shrink"
          @touchstart.passive="onTouchStart"
          @touchend.passive="onTouchEnd"
        >
          <img
            :src="resolveImageUrl(item.file_path)"
            :alt="item.title"
            class="max-w-full max-h-full object-contain rounded-lg"
          >

          <!-- モバイル用フローティング閉じるボタン -->
          <button
            type="button"
            class="md:hidden absolute top-2.5 right-2.5 z-20 p-1.5 rounded-full bg-canvas-panel/90 text-ink border border-canvas-border shadow-sm"
            aria-label="閉じる"
            @click="boardStore.closeQuickLook"
          >
            <X class="w-4 h-4" />
          </button>

          <span
            v-if="item.source_type === 'pixiv'"
            class="absolute top-3 left-3 px-2 py-0.5 rounded text-[11px] font-bold bg-pixiv text-white"
          >
            pixiv
          </span>
          <span
            v-else-if="item.source_type === 'instagram'"
            class="absolute top-3 left-3 px-2 py-0.5 rounded text-[11px] font-bold bg-instagram text-white flex items-center gap-1"
          >
            <Instagram class="w-3 h-3" />
            Instagram
          </span>

          <span
            v-if="currentIndex >= 0 && bookmarkList.length > 1"
            class="absolute bottom-2.5 right-2.5 md:bottom-auto md:top-3 md:right-3 px-2 py-0.5 rounded-md text-[11px] font-mono bg-canvas-panel/90 text-ink border border-canvas-border"
          >
            {{ currentIndex + 1 }} / {{ bookmarkList.length }}
          </span>

          <!-- 前後の資料への移動ボタン -->
          <template v-if="bookmarkList.length > 1">
            <button
              type="button"
              class="absolute left-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-canvas-panel/90 text-ink hover:bg-canvas-raised transition-colors disabled:opacity-30 shadow-sm"
              :disabled="!hasPrev"
              title="前の資料 (←)"
              aria-label="前の資料"
              @click="prevItem"
            >
              <ChevronLeft class="w-4 h-4" />
            </button>
            <button
              type="button"
              class="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-canvas-panel/90 text-ink hover:bg-canvas-raised transition-colors disabled:opacity-30 shadow-sm"
              :disabled="!hasNext"
              title="次の資料 (→)"
              aria-label="次の資料"
              @click="nextItem"
            >
              <ChevronRight class="w-4 h-4" />
            </button>
          </template>
        </div>

        <!-- 情報 -->
        <div
          class="w-full md:w-80 flex-1 min-h-0 border-t md:border-t-0 md:border-l border-canvas-border p-3.5 sm:p-4 flex flex-col gap-3 overflow-y-auto"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <h3 class="text-sm font-bold text-ink leading-snug">{{ item.title }}</h3>
              <p class="text-xs text-ink-subtle mt-1 truncate">
                {{ item.author_name || 'Unknown' }}
              </p>
            </div>
            <button
              ref="closeBtnRef"
              type="button"
              class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors shrink-0"
              aria-label="閉じる (Esc)"
              @click="boardStore.closeQuickLook"
            >
              <X class="w-4 h-4" />
            </button>
          </div>

          <!-- AI解析 -->
          <template v-if="item.ai_analysis && (item.ai_analysis.composition || item.ai_analysis.lighting || item.ai_analysis.palette?.length)">
            <div class="space-y-2">
              <p class="text-[10px] font-mono uppercase text-ink-subtle flex items-center gap-1.5">
                <Sparkles class="w-3 h-3 text-brand" />
                AI Visual Anatomy
              </p>

              <div v-if="item.ai_analysis.palette?.length" class="flex items-center gap-1.5 flex-wrap">
                <button
                  v-for="(hex, idx) in item.ai_analysis.palette"
                  :key="idx"
                  type="button"
                  class="w-6 h-6 rounded border border-canvas-border hover:scale-110 transition-transform flex items-center justify-center"
                  :style="{ backgroundColor: hex }"
                  :title="`${hex} をコピー`"
                  :aria-label="`カラーコード ${hex} をコピー`"
                  @click="copyHex(hex)"
                >
                  <Check v-if="copiedHex === hex" class="w-3.5 h-3.5 text-white stroke-[3] drop-shadow" />
                </button>
              </div>

              <div v-if="item.ai_analysis.composition" class="p-2 rounded-lg bg-canvas-card border border-canvas-border text-[11px] text-ink-muted">
                <span class="font-semibold text-ok block mb-0.5">構図</span>
                {{ item.ai_analysis.composition }}
              </div>

              <div v-if="item.ai_analysis.lighting" class="p-2 rounded-lg bg-canvas-card border border-canvas-border text-[11px] text-ink-muted">
                <span class="font-semibold text-warn block mb-0.5">ライティング</span>
                {{ item.ai_analysis.lighting }}
              </div>
            </div>
          </template>

          <!-- タグセクション（いつでもタグの編集・追加・削除・AI解析が可能） -->
          <div class="space-y-2 pt-2 border-t border-canvas-border">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-ink flex items-center gap-1.5">
                <Tag class="w-3.5 h-3.5 text-brand" />
                <span>タグ ({{ itemTags.length }})</span>
              </span>
              <button
                type="button"
                class="text-[11px] font-semibold text-brand hover:underline flex items-center gap-1 transition-colors"
                :disabled="isAnalyzing"
                @click="handleTriggerAi"
              >
                <Sparkles class="w-3 h-3" />
                <span>{{ isAnalyzing ? 'AI解析中...' : 'AIで自動タグ生成' }}</span>
              </button>
            </div>

            <!-- タグバッジ一覧 -->
            <div class="flex flex-wrap gap-1.5 min-h-[28px] items-center">
              <span
                v-for="tag in itemTags"
                :key="tag"
                class="group inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-xs bg-canvas-card border border-canvas-border text-ink hover:border-brand transition-colors"
              >
                <span>#{{ tag }}</span>
                <button
                  type="button"
                  class="text-ink-subtle hover:text-danger rounded p-0.5 transition-colors"
                  :title="`#${tag} を削除`"
                  :aria-label="`タグ ${tag} を削除`"
                  @click="handleRemoveTag(tag)"
                >
                  <X class="w-2.5 h-2.5" />
                </button>
              </span>

              <!-- 新規タグ入力フォーム -->
              <form
                v-if="isAddingTag"
                class="inline-flex items-center gap-1"
                @submit.prevent="handleAddTag"
              >
                <input
                  ref="tagInputRef"
                  v-model="newTagInput"
                  type="text"
                  placeholder="タグ名を入力..."
                  class="w-28 px-2 py-0.5 text-xs bg-canvas-bg border border-brand rounded-lg text-ink focus:outline-none"
                  @keydown.esc="isAddingTag = false"
                >
                <button
                  type="submit"
                  class="px-2 py-0.5 text-[10px] font-bold bg-brand text-brand-fg rounded-md"
                  :disabled="!newTagInput.trim()"
                >
                  追加
                </button>
                <button
                  type="button"
                  class="p-0.5 text-ink-subtle hover:text-ink text-xs"
                  @click="isAddingTag = false"
                >
                  <X class="w-3 h-3" />
                </button>
              </form>
              <button
                v-else
                type="button"
                class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-xs font-semibold bg-canvas-bg hover:bg-canvas-card border border-dashed border-canvas-border-strong text-ink-muted hover:text-brand transition-colors"
                @click="openAddTag"
              >
                <Plus class="w-3 h-3" />
                <span>タグ追加</span>
              </button>
            </div>
          </div>

          <!-- アクション -->
          <div class="mt-auto space-y-1.5 pt-3 border-t border-canvas-border">
            <button
              type="button"
              class="w-full py-2 rounded-lg bg-brand text-brand-fg text-xs font-bold hover:bg-brand-hover transition-colors flex items-center justify-center gap-1.5"
              @click="placeOnCanvas"
            >
              <Plus class="w-3.5 h-3.5 stroke-[2.5]" />
              キャンバスへ配置 (Enter)
            </button>

            <div class="flex items-center gap-1.5">
              <a
                v-if="item.source_url"
                :href="item.source_url"
                target="_blank"
                rel="noopener noreferrer"
                class="flex-1 py-2 rounded-lg bg-canvas-card hover:bg-canvas-hover text-ink-muted hover:text-ink text-xs font-medium text-center flex items-center justify-center gap-1.5 transition-colors border border-canvas-border"
              >
                <ExternalLink class="w-3.5 h-3.5" />
                元のページ
              </a>
              <button
                v-if="item.source_url"
                type="button"
                class="py-2 px-3 rounded-lg bg-canvas-card hover:bg-canvas-hover text-ink-muted hover:text-ink text-xs transition-colors border border-canvas-border"
                title="元のページURLをコピー"
                aria-label="元のページURLをコピー"
                @click="copySourceUrl"
              >
                <Copy class="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                class="py-2 px-3 rounded-lg bg-canvas-card hover:bg-danger-soft text-ink-muted hover:text-danger text-xs transition-colors border border-canvas-border"
                title="ライブラリから削除"
                aria-label="ライブラリから削除"
                @click="removeFromLibrary"
              >
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
