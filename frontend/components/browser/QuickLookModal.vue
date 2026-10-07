<script setup lang="ts">
import { onMounted, onUnmounted, computed } from 'vue'
import {
  X,
  ExternalLink,
  Plus,
  Sparkles,
  Compass,
  Sun,
  Shirt,
  Tag,
  Instagram,
  Trash2,
} from 'lucide-vue-next'
import { useBoardStore } from '~/stores/boardStore'
import { useMediaUrl } from '~/composables/useMediaUrl'
import { useToast } from '~/composables/useToast'

const boardStore = useBoardStore()
const toast = useToast()
const { resolveMediaUrl } = useMediaUrl()

const item = computed(() => boardStore.quickLookItem)

function resolveImageUrl(path?: string) {
  return resolveMediaUrl(path)
}

async function placeOnCanvas() {
  if (!boardStore.quickLookItem) return
  await boardStore.placeBookmarkOnBoard(boardStore.quickLookItem.id, 150, 150)
  toast.success('キャンバスへ配置しました')
  boardStore.closeQuickLook()
}

async function removeFromLibrary() {
  if (!boardStore.quickLookItem) return
  await boardStore.deleteBookmark(boardStore.quickLookItem.id)
  toast.success('ライブラリから削除しました')
  boardStore.closeQuickLook()
}

function isTypingTarget(target: EventTarget | null) {
  const el = target as HTMLElement | null
  if (!el) return false
  return ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName) || !!el.isContentEditable
}

function onKeyDown(e: KeyboardEvent) {
  if (!boardStore.quickLookItem) return

  if (e.key === 'Escape' || e.key === ' ') {
    if (isTypingTarget(e.target)) return
    e.preventDefault()
    boardStore.closeQuickLook()
  } else if (e.key === 'Enter') {
    e.preventDefault()
    placeOnCanvas()
  }
}

onMounted(() => window.addEventListener('keydown', onKeyDown))
onUnmounted(() => window.removeEventListener('keydown', onKeyDown))
</script>

<template>
  <Teleport to="body">
    <div
      v-if="item"
      class="fixed inset-0 z-[65] flex items-center justify-center p-4 md:p-6 scrim animate-fade-in"
      @click.self="boardStore.closeQuickLook"
    >
      <div
        class="w-full max-w-4xl max-h-[85vh] rounded-2xl border border-canvas-border bg-canvas-panel shadow-pop overflow-hidden flex flex-col md:flex-row animate-scale-in"
        role="dialog"
        aria-modal="true"
        :aria-label="item.title"
      >
        <!-- 画像 -->
        <div class="flex-1 bg-canvas-sunken relative flex items-center justify-center p-4 min-h-[300px]">
          <img
            :src="resolveImageUrl(item.file_path)"
            :alt="item.title"
            class="max-w-full max-h-full object-contain rounded-lg"
          >

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
        </div>

        <!-- 情報 -->
        <div
          class="w-full md:w-80 border-t md:border-t-0 md:border-l border-canvas-border p-4 flex flex-col gap-3 overflow-y-auto"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <h3 class="text-sm font-bold text-ink leading-snug">{{ item.title }}</h3>
              <p class="text-xs text-ink-subtle mt-1 truncate">
                {{ item.author_name || 'Unknown' }}
              </p>
            </div>
            <button
              type="button"
              class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors shrink-0"
              aria-label="閉じる (Esc)"
              @click="boardStore.closeQuickLook"
            >
              <X class="w-4 h-4" />
            </button>
          </div>

          <!-- AI解析 -->
          <template v-if="item.ai_analysis">
            <div class="space-y-2">
              <p class="text-[10px] font-mono uppercase text-ink-subtle flex items-center gap-1.5">
                <Sparkles class="w-3 h-3 text-brand" />
                AI Visual Anatomy
              </p>

              <div v-if="item.ai_analysis.palette?.length" class="flex items-center gap-1">
                <span
                  v-for="(hex, idx) in item.ai_analysis.palette"
                  :key="idx"
                  class="w-5 h-5 rounded border border-canvas-border"
                  :style="{ backgroundColor: hex }"
                  :title="hex"
                />
              </div>

              <div class="p-2 rounded-lg bg-canvas-card border border-canvas-border text-[11px] text-ink-muted">
                <span class="font-semibold text-ok block mb-0.5">構図</span>
                {{ item.ai_analysis.composition }}
              </div>

              <div class="p-2 rounded-lg bg-canvas-card border border-canvas-border text-[11px] text-ink-muted">
                <span class="font-semibold text-warn block mb-0.5">ライティング</span>
                {{ item.ai_analysis.lighting }}
              </div>

              <div v-if="item.ai_analysis.tags?.length" class="flex flex-wrap gap-1">
                <span
                  v-for="tag in item.ai_analysis.tags"
                  :key="tag"
                  class="px-1.5 py-0.5 rounded text-[10px] bg-canvas-raised text-ink-muted border border-canvas-border"
                >
                  #{{ tag }}
                </span>
              </div>
            </div>
          </template>

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