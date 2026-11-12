<script setup lang="ts">
import { ref, computed, toRef, watch, nextTick } from 'vue'
import { Folder, FolderPlus, X, Check, Bookmark, Layers, RefreshCw } from 'lucide-vue-next'
import { useBoardStore } from '~/stores/boardStore'
import { useToast } from '~/composables/useToast'
import { useMediaUrl } from '~/composables/useMediaUrl'
import FolderSelectDropdown from '~/components/ui/FolderSelectDropdown.vue'
import { useDialogA11y } from '~/composables/useDialogA11y'
import { formatFolderLabel } from '~/utils/folders'

const props = defineProps<{
  isOpen: boolean
  boardId: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved', count: number, folder: string): void
}>()

const boardStore = useBoardStore()
const toast = useToast()
const { resolveMediaUrl } = useMediaUrl()

// Esc で閉じる / 背景スクロールを止める
const { dialogRef } = useDialogA11y(toRef(props, 'isOpen'), () => emit('close'))

// 保存先モード: 'new' (新規フォルダ作成 - デフォルト) | 'existing' (既存フォルダ選択)
const saveMode = ref<'new' | 'existing'>('new')
const newFolderName = ref('')
const selectedFolder = ref('All References')
const targetScope = ref<'all' | 'selected'>('all')
const isSaving = ref(false)
const newFolderInputRef = ref<HTMLInputElement | null>(null)

const hasSelection = computed(() => boardStore.selectedItemIds.length > 0)

const targetItems = computed(() => {
  if (targetScope.value === 'selected' && hasSelection.value) {
    return boardStore.selectedItems
  }
  return boardStore.items
})

const previewThumbs = computed(() => {
  return targetItems.value
    .slice(0, 8)
    .map(it => resolveMediaUrl(it.media?.file_path))
    .filter(Boolean)
})

// モーダルオープン時の初期化: デフォルトで新規フォルダモードにし、ボード名を初期値としてセット
watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      saveMode.value = 'new'
      const baseTitle = boardStore.currentBoard?.title?.trim()
      newFolderName.value = baseTitle || '新規フォルダ'
      targetScope.value = hasSelection.value ? 'selected' : 'all'
      nextTick(() => {
        newFolderInputRef.value?.focus()
        newFolderInputRef.value?.select()
      })
    }
  },
  { immediate: true }
)

async function handleSave() {
  if (!targetItems.value.length) {
    toast.error('保存する資料がありません')
    return
  }

  let folder = ''
  if (saveMode.value === 'new') {
    folder = newFolderName.value.trim()
    if (!folder) {
      toast.error('フォルダ名を入力してください')
      newFolderInputRef.value?.focus()
      return
    }
  } else {
    folder = selectedFolder.value.trim() || 'All References'
  }

  isSaving.value = true
  const itemIds = targetScope.value === 'selected' && hasSelection.value
    ? boardStore.selectedItemIds
    : [] // empty means all items on board

  const success = await boardStore.saveCanvasItemsToFolder(itemIds, folder)
  isSaving.value = false

  if (success) {
    emit('saved', targetItems.value.length, folder)
    emit('close')
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-[75] flex items-end sm:items-center justify-center p-2 sm:p-4 scrim animate-fade-in"
      @click.self="emit('close')"
    >
      <div
        ref="dialogRef"
        class="w-full max-w-lg rounded-2xl border border-canvas-border bg-canvas-panel shadow-pop relative overflow-visible animate-scale-in"
        role="dialog"
        aria-modal="true"
        aria-label="キャンバス上の資料を一括フォルダ保存"
      >
        <!-- ヘッダー -->
        <div class="px-4 py-3.5 border-b border-canvas-border flex items-center justify-between rounded-t-2xl bg-canvas-panel">
          <div class="flex items-center gap-2">
            <div class="p-2 rounded-xl bg-brand text-brand-fg">
              <Folder class="w-4 h-4" />
            </div>
            <div>
              <h2 class="text-sm font-bold text-ink">キャンバス上の資料を一括フォルダ保存</h2>
              <p class="text-[11px] text-ink-subtle">キャンバス上の画像をブックマークフォルダに整理・セーブします</p>
            </div>
          </div>
          <button
            type="button"
            class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
            aria-label="閉じる"
            @click="emit('close')"
          >
            <X class="w-4 h-4" />
          </button>
        </div>

        <div class="p-4 space-y-4">
          <!-- 保存対象の選択 -->
          <div v-if="hasSelection" class="space-y-1.5">
            <label class="text-xs font-bold text-ink">保存対象</label>
            <div class="grid grid-cols-2 gap-2">
              <button
                type="button"
                class="px-3 py-2 rounded-xl border text-xs font-semibold text-left transition-colors flex items-center justify-between"
                :class="targetScope === 'selected'
                  ? 'bg-brand text-brand-fg border-brand font-bold shadow-sm'
                  : 'bg-canvas-card border-canvas-border text-ink hover:border-canvas-border-strong'"
                @click="targetScope = 'selected'"
              >
                <span>選択中の資料のみ</span>
                <span class="text-[11px] opacity-80 font-mono">{{ boardStore.selectedItems.length }}件</span>
              </button>
              <button
                type="button"
                class="px-3 py-2 rounded-xl border text-xs font-semibold text-left transition-colors flex items-center justify-between"
                :class="targetScope === 'all'
                  ? 'bg-brand text-brand-fg border-brand font-bold shadow-sm'
                  : 'bg-canvas-card border-canvas-border text-ink hover:border-canvas-border-strong'"
                @click="targetScope = 'all'"
              >
                <span>キャンバスの全資料</span>
                <span class="text-[11px] opacity-80 font-mono">{{ boardStore.items.length }}件</span>
              </button>
            </div>
          </div>

          <!-- 保存先フォルダ選択 (デフォルト: 新規フォルダ作成) -->
          <div class="space-y-3 p-3.5 rounded-2xl bg-canvas-sunken/60 border border-canvas-border relative z-20">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-ink flex items-center gap-1.5">
                <Bookmark class="w-3.5 h-3.5 text-brand" />
                <span>保存先フォルダ</span>
              </span>
              <span class="text-[10px] text-ink-subtle">
                {{ saveMode === 'new' ? '新しいフォルダを自動生成' : '既存フォルダを選択' }}
              </span>
            </div>

            <!-- モード切替タブ: デフォルト新規フォルダ -->
            <div class="grid grid-cols-2 gap-1 p-1 bg-canvas-card rounded-xl border border-canvas-border text-xs">
              <button
                type="button"
                class="py-1.5 px-3 rounded-lg font-bold flex items-center justify-center gap-1.5 transition-all text-xs"
                :class="saveMode === 'new'
                  ? 'bg-brand text-brand-fg shadow-xs'
                  : 'text-ink-muted hover:text-ink'"
                @click="saveMode = 'new'"
              >
                <FolderPlus class="w-3.5 h-3.5" />
                <span>新規フォルダを作成</span>
              </button>
              <button
                type="button"
                class="py-1.5 px-3 rounded-lg font-bold flex items-center justify-center gap-1.5 transition-all text-xs"
                :class="saveMode === 'existing'
                  ? 'bg-brand text-brand-fg shadow-xs'
                  : 'text-ink-muted hover:text-ink'"
                @click="saveMode = 'existing'"
              >
                <Folder class="w-3.5 h-3.5" />
                <span>既存フォルダを選択</span>
              </button>
            </div>

            <!-- A. 新規フォルダモード (デフォルト) -->
            <div v-if="saveMode === 'new'" class="space-y-1.5 pt-0.5">
              <div class="relative flex items-center">
                <FolderPlus class="absolute left-3 w-4 h-4 text-brand pointer-events-none" />
                <input
                  ref="newFolderInputRef"
                  v-model="newFolderName"
                  type="text"
                  maxlength="40"
                  placeholder="新しいフォルダ名を入力..."
                  class="w-full pl-9 pr-3 py-2 rounded-xl border border-canvas-border-strong bg-canvas-card text-xs font-semibold text-ink placeholder:text-ink-subtle focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition-all"
                  @keydown.enter.prevent="handleSave"
                >
              </div>
              <p class="text-[11px] text-ink-subtle px-0.5">
                一括保存と同時にこのフォルダが作成され、キャンバスの資料が整理されます。
              </p>
            </div>

            <!-- B. 既存フォルダモード -->
            <div v-else class="space-y-1.5 pt-0.5">
              <FolderSelectDropdown
                v-model="selectedFolder"
                button-class="w-full text-xs justify-between"
                align="left"
                placeholder="フォルダを選択..."
              />
              <p class="text-[11px] text-ink-subtle px-0.5">
                選択した既存のフォルダにキャンバスの資料を追加・保存します。
              </p>
            </div>
          </div>

          <!-- プレビューサムネイルストリップ -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between text-[11px] text-ink-muted px-0.5">
              <span>保存される資料 ({{ targetItems.length }}件)</span>
            </div>
            <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar p-1.5 rounded-xl bg-canvas-card border border-canvas-border">
              <div
                v-for="(thumb, idx) in previewThumbs"
                :key="idx"
                class="w-12 h-12 rounded-lg bg-canvas-sunken border border-canvas-border overflow-hidden shrink-0"
              >
                <img :src="thumb" alt="" class="w-full h-full object-cover" loading="lazy">
              </div>
              <div
                v-if="targetItems.length > 8"
                class="w-12 h-12 rounded-lg bg-canvas-raised border border-canvas-border flex items-center justify-center text-[11px] font-mono font-bold text-ink-muted shrink-0"
              >
                +{{ targetItems.length - 8 }}
              </div>
            </div>
          </div>

          <!-- フッターアクション -->
          <div class="pt-3 border-t border-canvas-border flex items-center justify-end gap-2">
            <button
              type="button"
              class="px-4 py-2 rounded-xl text-xs font-semibold text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
              @click="emit('close')"
            >
              キャンセル
            </button>
            <button
              type="button"
              class="px-4 py-2 rounded-xl bg-brand text-brand-fg hover:bg-brand-hover text-xs font-bold transition-colors flex items-center gap-1.5 disabled:opacity-50 shadow-sm"
              :disabled="isSaving || !targetItems.length || (saveMode === 'new' && !newFolderName.trim())"
              @click="handleSave"
            >
              <RefreshCw v-if="isSaving" class="w-3.5 h-3.5 animate-spin" />
              <Check v-else class="w-3.5 h-3.5" />
              <span v-if="isSaving">保存中...</span>
              <span v-else-if="saveMode === 'new'">
                「{{ newFolderName.trim() || '新規フォルダ' }}」を作成して一括保存
              </span>
              <span v-else>
                「{{ formatFolderLabel(selectedFolder) }}」に一括保存
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
