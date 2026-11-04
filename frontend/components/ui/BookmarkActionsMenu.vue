<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { ExternalLink, FolderInput, Layers, MoreHorizontal, Trash2, X, Check, ArrowLeft } from 'lucide-vue-next'
import type { BookmarkItem, FolderItem } from '~/types'

const props = defineProps<{ item: BookmarkItem; folders: FolderItem[] }>()
const emit = defineEmits<{
  place: []
  move: [folderName: string]
  delete: []
}>()

const open = ref(false)
const section = ref<'actions' | 'folders' | 'delete'>('actions')

function close() {
  open.value = false
  section.value = 'actions'
}

function onEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') close()
}

watch(open, value => {
  if (value) {
    document.addEventListener('keydown', onEscape)
  } else {
    document.removeEventListener('keydown', onEscape)
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onEscape)
})

function chooseFolder(name: string) {
  if (name !== props.item.folder_name) emit('move', name)
  close()
}
</script>

<template>
  <div class="relative z-20 shrink-0" @click.stop>
    <button
      type="button"
      class="p-1.5 rounded-lg bg-canvas-raised/95 text-ink hover:text-brand border border-canvas-border-strong shadow-sm transition-colors"
      :aria-label="`${item.title}の操作メニュー`"
      aria-haspopup="dialog"
      :aria-expanded="open"
      @click="open ? close() : (open = true)"
    >
      <MoreHorizontal class="w-4 h-4" />
    </button>

    <Teleport to="body">
      <div
        v-if="open"
        class="fixed inset-0 z-[85] flex items-end sm:items-center justify-center p-2 sm:p-4 scrim animate-fade-in"
        @click.self="close"
      >
        <div
          class="w-full max-w-sm rounded-2xl border border-canvas-border bg-canvas-panel shadow-pop overflow-hidden animate-scale-in"
          role="dialog"
          aria-modal="true"
          :aria-label="`${item.title}の操作`"
          @click.stop
        >
          <!-- ヘッダー -->
          <div class="px-4 py-3 border-b border-canvas-border flex items-center justify-between gap-2">
            <div class="min-w-0">
              <p class="text-xs font-bold text-ink truncate">{{ item.title }}</p>
              <p class="text-[11px] text-ink-muted truncate">{{ item.author_name || item.folder_name }}</p>
            </div>
            <button
              type="button"
              class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors shrink-0"
              aria-label="閉じる"
              @click="close"
            >
              <X class="w-4 h-4" />
            </button>
          </div>

          <!-- メイン操作一覧 -->
          <div v-if="section === 'actions'" class="p-3 space-y-1.5">
            <button
              type="button"
              class="w-full flex items-center gap-3 px-3.5 py-3 rounded-xl bg-brand-soft text-brand font-bold text-xs hover:opacity-90 transition-opacity"
              @click="emit('place'); close()"
            >
              <Layers class="w-4 h-4 shrink-0" />
              <span>キャンバスへ配置</span>
            </button>

            <a
              v-if="item.source_url"
              :href="item.source_url"
              target="_blank"
              rel="noopener noreferrer"
              class="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl bg-canvas-bg hover:bg-canvas-hover border border-canvas-border-strong text-ink font-medium text-xs transition-colors"
              @click="close"
            >
              <ExternalLink class="w-4 h-4 text-ink-muted shrink-0" />
              <span>元のページを開く</span>
            </a>

            <button
              type="button"
              class="w-full flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-xl bg-canvas-bg hover:bg-canvas-hover border border-canvas-border-strong text-ink font-medium text-xs transition-colors"
              @click="section = 'folders'"
            >
              <span class="flex items-center gap-3">
                <FolderInput class="w-4 h-4 text-ink-muted shrink-0" />
                <span>コレクションを変更</span>
              </span>
              <span class="text-[11px] text-ink-muted truncate max-w-[120px]">{{ item.folder_name }}</span>
            </button>

            <button
              type="button"
              class="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl bg-danger-soft/60 hover:bg-danger-soft text-danger font-semibold text-xs transition-colors"
              @click="section = 'delete'"
            >
              <Trash2 class="w-4 h-4 shrink-0" />
              <span>ライブラリから削除</span>
            </button>
          </div>

          <!-- コレクション変更 -->
          <div v-else-if="section === 'folders'" class="p-3 space-y-2">
            <div class="flex items-center justify-between px-1">
              <p class="text-xs font-bold text-ink">移動先のコレクション</p>
              <button
                type="button"
                class="text-xs font-medium text-ink-muted hover:text-ink flex items-center gap-1"
                @click="section = 'actions'"
              >
                <ArrowLeft class="w-3.5 h-3.5" />
                戻る
              </button>
            </div>

            <div class="max-h-60 overflow-y-auto space-y-1 pr-0.5">
              <button
                v-for="folder in folders"
                :key="folder.name"
                type="button"
                class="w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl text-xs border transition-colors text-left"
                :class="folder.name === item.folder_name
                  ? 'bg-brand-soft border-brand text-brand font-bold'
                  : 'bg-canvas-bg border-canvas-border-strong text-ink font-medium hover:bg-canvas-hover'"
                @click="chooseFolder(folder.name)"
              >
                <span class="flex items-center gap-2 truncate">
                  <span class="w-2.5 h-2.5 rounded-full shrink-0" :style="{ backgroundColor: folder.color || '#6366f1' }" />
                  <span class="truncate">{{ folder.name }}</span>
                </span>
                <Check v-if="folder.name === item.folder_name" class="w-4 h-4 text-brand shrink-0" />
              </button>
            </div>
          </div>

          <!-- 削除確認 -->
          <div v-else class="p-4 space-y-3">
            <p class="text-xs font-semibold text-ink">この資料をライブラリから削除しますか？</p>
            <div class="flex gap-2">
              <button
                type="button"
                class="flex-1 rounded-xl border border-canvas-border-strong bg-canvas-bg hover:bg-canvas-hover px-3 py-2.5 text-xs font-semibold text-ink transition-colors"
                @click="section = 'actions'"
              >
                キャンセル
              </button>
              <button
                type="button"
                class="flex-1 rounded-xl bg-danger text-white hover:opacity-90 px-3 py-2.5 text-xs font-bold transition-opacity"
                @click="emit('delete'); close()"
              >
                削除する
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
