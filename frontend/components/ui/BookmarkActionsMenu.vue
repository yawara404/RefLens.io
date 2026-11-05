<script setup lang="ts">
import { onBeforeUnmount, ref, watch, nextTick, computed } from 'vue'
import { ExternalLink, FolderInput, Layers, MoreHorizontal, Trash2, X, Check, ArrowLeft, Plus, Tag, Sparkles } from 'lucide-vue-next'
import type { BookmarkItem, FolderItem } from '~/types'
import { useBoardStore } from '~/stores/boardStore'

const props = withDefaults(defineProps<{ item: BookmarkItem; folders?: FolderItem[] }>(), {
  folders: () => [],
})
const emit = defineEmits<{
  place: []
  move: [folderName: string]
  delete: []
}>()

const boardStore = useBoardStore()
const availableFolders = computed(() => (props.folders && props.folders.length > 0 ? props.folders : boardStore.folders))
const open = ref(false)
const section = ref<'actions' | 'folders' | 'tags' | 'delete'>('actions')
const isCreatingFolder = ref(false)
const newFolderName = ref('')
const newFolderInputRef = ref<HTMLInputElement | null>(null)
const newTagInput = ref('')
const isAnalyzing = ref(false)

const currentTags = computed(() => props.item.ai_analysis?.tags || [])

function close() {
  open.value = false
  section.value = 'actions'
  isCreatingFolder.value = false
  newFolderName.value = ''
  newTagInput.value = ''
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

function formatFolderLabel(name?: string): string {
  if (!name || name === 'All References') return 'すべての資料'
  return name
}

function chooseFolder(name: string) {
  if (name !== props.item.folder_name) emit('move', name)
  close()
}

function startCreatingFolder() {
  isCreatingFolder.value = true
  newFolderName.value = ''
  nextTick(() => {
    newFolderInputRef.value?.focus()
  })
}

async function handleCreateAndMove() {
  const name = newFolderName.value.trim()
  if (!name) {
    isCreatingFolder.value = false
    return
  }
  await boardStore.createFolder(name)
  chooseFolder(name)
}

async function addTag() {
  const val = newTagInput.value.trim().replace(/^#/, '')
  if (!val) return
  newTagInput.value = ''
  await boardStore.addBookmarkTag(props.item.id, val)
}

async function removeTag(tag: string) {
  await boardStore.removeBookmarkTag(props.item.id, tag)
}

async function triggerAi() {
  if (isAnalyzing.value) return
  isAnalyzing.value = true
  try {
    await boardStore.triggerAiAnalysis(props.item.id)
  } finally {
    setTimeout(() => {
      isAnalyzing.value = false
    }, 3500)
  }
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
                <FolderInput class="w-4 h-4 text-brand shrink-0" />
                <span>フォルダを変更</span>
              </span>
              <span class="text-[11px] text-ink-muted truncate max-w-[120px]">{{ formatFolderLabel(item.folder_name) }}</span>
            </button>

            <button
              type="button"
              class="w-full flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-xl bg-canvas-bg hover:bg-canvas-hover border border-canvas-border-strong text-ink font-medium text-xs transition-colors"
              @click="section = 'tags'"
            >
              <span class="flex items-center gap-3">
                <Tag class="w-4 h-4 text-brand shrink-0" />
                <span>タグを編集</span>
              </span>
              <span class="text-[11px] text-ink-muted">
                {{ currentTags.length ? `${currentTags.length}件` : '未設定' }}
              </span>
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

          <!-- フォルダ変更 -->
          <div v-else-if="section === 'folders'" class="p-3 space-y-2">
            <div class="flex items-center justify-between px-1">
              <p class="text-xs font-bold text-ink">移動先のフォルダ</p>
              <button
                type="button"
                class="text-xs font-medium text-ink-muted hover:text-ink flex items-center gap-1"
                @click="section = 'actions'"
              >
                <ArrowLeft class="w-3.5 h-3.5" />
                戻る
              </button>
            </div>

            <div class="max-h-52 overflow-y-auto space-y-1 pr-0.5 no-scrollbar">
              <button
                v-for="folder in availableFolders"
                :key="folder.name"
                type="button"
                class="w-full flex items-center justify-between gap-2 px-3 py-2 rounded-xl text-xs border transition-colors text-left"
                :class="folder.name === item.folder_name
                  ? 'bg-brand-soft border-brand text-brand font-bold'
                  : 'bg-canvas-bg border-canvas-border-strong text-ink font-medium hover:bg-canvas-hover'"
                @click="chooseFolder(folder.name)"
              >
                <span class="flex items-center gap-2 truncate">
                  <span class="w-2.5 h-2.5 rounded-full shrink-0" :style="{ backgroundColor: folder.color || '#6366f1' }" />
                  <span class="truncate">{{ formatFolderLabel(folder.name) }}</span>
                </span>
                <Check v-if="folder.name === item.folder_name" class="w-4 h-4 text-brand shrink-0" />
              </button>
            </div>

            <!-- 新規フォルダ作成 -->
            <div class="pt-2 border-t border-canvas-border">
              <div v-if="isCreatingFolder" class="flex items-center gap-1">
                <input
                  ref="newFolderInputRef"
                  v-model="newFolderName"
                  type="text"
                  placeholder="フォルダ名を入力..."
                  class="flex-1 min-w-0 bg-canvas-card border border-canvas-border rounded-lg px-2 py-1.5 text-xs text-ink focus:outline-none focus:border-brand"
                  @keydown.enter.prevent="handleCreateAndMove"
                  @keydown.esc.prevent="isCreatingFolder = false"
                >
                <button
                  type="button"
                  class="p-1.5 rounded-lg bg-brand text-brand-fg text-xs font-bold shrink-0"
                  :disabled="!newFolderName.trim()"
                  @click="handleCreateAndMove"
                >
                  <Check class="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  class="p-1.5 rounded-lg text-ink-muted hover:text-ink shrink-0"
                  @click="isCreatingFolder = false"
                >
                  <X class="w-3.5 h-3.5" />
                </button>
              </div>
              <button
                v-else
                type="button"
                class="w-full py-1.5 px-2 rounded-lg text-xs font-semibold text-brand hover:bg-brand-soft flex items-center gap-1.5 transition-colors"
                @click="startCreatingFolder"
              >
                <Plus class="w-3.5 h-3.5" />
                <span>新しいフォルダを作成して移動</span>
              </button>
            </div>
          </div>

          <!-- タグ編集 -->
          <div v-else-if="section === 'tags'" class="p-3 space-y-2.5">
            <div class="flex items-center justify-between px-1">
              <p class="text-xs font-bold text-ink flex items-center gap-1.5">
                <Tag class="w-3.5 h-3.5 text-brand" />
                <span>タグ編集 ({{ currentTags.length }})</span>
              </p>
              <button
                type="button"
                class="text-xs font-medium text-ink-muted hover:text-ink flex items-center gap-1"
                @click="section = 'actions'"
              >
                <ArrowLeft class="w-3.5 h-3.5" />
                戻る
              </button>
            </div>

            <!-- 新規タグ追加入力 -->
            <form class="flex items-center gap-1.5" @submit.prevent="addTag">
              <input
                v-model="newTagInput"
                type="text"
                placeholder="新しいタグ名を入力..."
                class="flex-1 min-w-0 bg-canvas-bg border border-canvas-border-strong rounded-xl px-2.5 py-1.5 text-xs text-ink focus:outline-none focus:border-brand"
              >
              <button
                type="submit"
                class="px-3 py-1.5 rounded-xl bg-brand text-brand-fg text-xs font-bold whitespace-nowrap disabled:opacity-40"
                :disabled="!newTagInput.trim()"
              >
                追加
              </button>
            </form>

            <!-- 現在のタグ一覧 -->
            <div class="max-h-48 overflow-y-auto space-y-1 pr-0.5 no-scrollbar">
              <div v-if="!currentTags.length" class="py-4 text-center text-xs text-ink-muted">
                まだタグがありません
              </div>
              <div v-else class="flex flex-wrap gap-1.5 pt-1">
                <span
                  v-for="tag in currentTags"
                  :key="tag"
                  class="group inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-canvas-bg border border-canvas-border-strong text-ink hover:border-brand transition-colors"
                >
                  <span>#{{ tag }}</span>
                  <button
                    type="button"
                    class="text-ink-subtle hover:text-danger rounded p-0.5 transition-colors"
                    :title="`#${tag} を削除`"
                    :aria-label="`タグ ${tag} を削除`"
                    @click="removeTag(tag)"
                  >
                    <X class="w-3 h-3" />
                  </button>
                </span>
              </div>
            </div>

            <div class="pt-2 border-t border-canvas-border flex items-center justify-between">
              <button
                type="button"
                class="text-[11px] font-semibold text-brand hover:underline flex items-center gap-1"
                :disabled="isAnalyzing"
                @click="triggerAi"
              >
                <Sparkles class="w-3 h-3" />
                <span>{{ isAnalyzing ? 'AI解析中...' : 'AIタグを自動生成' }}</span>
              </button>
              <button
                type="button"
                class="px-3 py-1 rounded-lg bg-canvas-bg border border-canvas-border text-xs font-semibold text-ink hover:bg-canvas-hover"
                @click="close"
              >
                完了
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
