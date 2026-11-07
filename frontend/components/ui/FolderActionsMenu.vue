<script setup lang="ts">
import { ref, watch } from 'vue'
import { Check, MoreVertical, Palette, Pencil, Trash2, X } from 'lucide-vue-next'
import type { FolderItem } from '~/types'

const props = defineProps<{ folder: FolderItem }>()
const emit = defineEmits<{
  rename: [name: string]
  colorChange: [color: string]
  delete: []
}>()

const FOLDER_COLOR_PRESETS = [
  { hex: '#6366f1', label: 'インディゴ' },
  { hex: '#3b82f6', label: 'ブルー' },
  { hex: '#06b6d4', label: 'シアン' },
  { hex: '#10b981', label: 'エメラルド' },
  { hex: '#84cc16', label: 'ライム' },
  { hex: '#f59e0b', label: 'アンバー' },
  { hex: '#f97316', label: 'オレンジ' },
  { hex: '#ef4444', label: 'レッド' },
  { hex: '#ec4899', label: 'ピンク' },
  { hex: '#a855f7', label: 'パープル' },
] as const

const open = ref(false)
const confirmDelete = ref(false)
const draftName = ref('')
const draftColor = ref('#6366f1')

function close() {
  open.value = false
  confirmDelete.value = false
}

const { dialogRef } = useDialogA11y(open, close)

watch(open, value => {
  if (value) {
    draftName.value = props.folder.name
    draftColor.value = props.folder.color || '#6366f1'
    confirmDelete.value = false
  }
})

function submitRename() {
  const name = draftName.value.trim()
  if (!name || name === props.folder.name) {
    close()
    return
  }
  emit('rename', name)
  close()
}

function selectColor(color: string) {
  draftColor.value = color
  if (color.toLowerCase() !== (props.folder.color || '#6366f1').toLowerCase()) {
    emit('colorChange', color)
  }
}
</script>

<template>
  <div class="relative z-20 shrink-0" @click.stop>
    <button
      type="button"
      class="p-1.5 rounded-lg text-ink-muted opacity-100 md:opacity-0 md:group-hover:opacity-100 focus-visible:opacity-100 hover:text-ink hover:bg-canvas-card transition-colors"
      :class="open ? 'opacity-100 text-ink bg-canvas-card' : ''"
      :aria-label="`${folder.name}の操作メニュー`"
      aria-haspopup="dialog"
      :aria-expanded="open"
      @click="open ? close() : (open = true)"
    >
      <MoreVertical class="w-3.5 h-3.5" />
    </button>

    <Teleport to="body">
      <div
        v-if="open"
        class="fixed inset-0 z-[85] flex items-end sm:items-center justify-center p-2 sm:p-4 scrim animate-fade-in"
        @click.self="close"
      >
        <div
          class="w-full max-w-sm rounded-2xl border border-canvas-border bg-canvas-panel shadow-pop overflow-hidden animate-scale-in"
          ref="dialogRef" role="dialog"
          aria-modal="true"
          :aria-label="`${folder.name}の編集`"
          @click.stop
        >
          <div class="px-4 py-3 border-b border-canvas-border flex items-center justify-between gap-2">
            <h2 class="text-sm font-bold text-ink flex items-center gap-2 truncate">
              <span
                class="w-3 h-3 rounded-full shrink-0"
                :style="{ backgroundColor: draftColor }"
              />
              <Pencil class="w-4 h-4 text-brand shrink-0" />
              <span class="truncate">コレクション編集: {{ folder.name }}</span>
            </h2>
            <button
              type="button"
              class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors shrink-0"
              aria-label="閉じる"
              @click="close"
            >
              <X class="w-4 h-4" />
            </button>
          </div>

          <div class="p-4 space-y-4">
            <!-- 名前変更フォーム -->
            <form class="space-y-2" @submit.prevent="submitRename">
              <label class="block text-xs font-bold text-ink">
                コレクション名を変更
              </label>
              <div class="flex items-center gap-2">
                <input
                  v-model="draftName"
                  type="text"
                  class="flex-1 bg-canvas-bg border border-canvas-border-strong rounded-xl px-3 py-2 text-xs font-medium text-ink focus:outline-none focus:border-brand"
                  :aria-label="`${folder.name}の新しい名前`"
                  autofocus
                >
                <button
                  type="submit"
                  class="px-3.5 py-2 rounded-xl bg-brand text-brand-fg hover:bg-brand-hover text-xs font-bold transition-colors disabled:opacity-50 shrink-0"
                  :disabled="!draftName.trim()"
                >
                  保存
                </button>
              </div>
            </form>

            <!-- フォルダカラー設定 -->
            <div class="pt-3 border-t border-canvas-border space-y-2.5">
              <div class="flex items-center justify-between gap-2">
                <label class="text-xs font-bold text-ink flex items-center gap-1.5">
                  <Palette class="w-3.5 h-3.5 text-brand shrink-0" />
                  <span>フォルダカラー</span>
                </label>
                <label class="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-canvas-bg border border-canvas-border-strong hover:border-brand text-[11px] font-semibold text-ink cursor-pointer transition-colors">
                  <input
                    type="color"
                    :value="draftColor"
                    class="w-3.5 h-3.5 rounded border-0 bg-transparent p-0 cursor-pointer"
                    aria-label="カスタムフォルダカラーを選択"
                    @input="selectColor(($event.target as HTMLInputElement).value)"
                  >
                  <span class="font-mono uppercase">{{ draftColor }}</span>
                </label>
              </div>

              <div class="grid grid-cols-5 gap-2">
                <button
                  v-for="preset in FOLDER_COLOR_PRESETS"
                  :key="preset.hex"
                  type="button"
                  class="h-8 rounded-xl border transition-transform hover:scale-105 flex items-center justify-center"
                  :class="draftColor.toLowerCase() === preset.hex.toLowerCase()
                    ? 'border-ink ring-2 ring-brand/40 scale-105'
                    : 'border-canvas-border'"
                  :style="{ backgroundColor: preset.hex }"
                  :title="`${preset.label} (${preset.hex})`"
                  :aria-label="`${preset.label} (${preset.hex}) に変更`"
                  @click="selectColor(preset.hex)"
                >
                  <Check
                    v-if="draftColor.toLowerCase() === preset.hex.toLowerCase()"
                    class="w-3.5 h-3.5 text-white drop-shadow"
                  />
                </button>
              </div>
            </div>

            <!-- 削除 -->
            <div class="pt-3 border-t border-canvas-border space-y-2">
              <template v-if="!confirmDelete">
                <button
                  type="button"
                  class="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl bg-danger-soft/70 hover:bg-danger-soft text-danger text-xs font-bold transition-colors"
                  @click="confirmDelete = true"
                >
                  <Trash2 class="w-4 h-4 shrink-0" />
                  <span>このコレクションを削除</span>
                </button>
              </template>
              <template v-else>
                <p class="text-xs font-semibold text-ink">
                  本当に「{{ folder.name }}」を削除しますか？
                </p>
                <p class="text-[11px] text-ink-muted">
                  中の資料は削除されず「All References」に移動します。
                </p>
                <div class="flex gap-2 pt-1">
                  <button
                    type="button"
                    class="flex-1 rounded-xl border border-canvas-border-strong bg-canvas-bg hover:bg-canvas-hover px-3 py-2 text-xs font-semibold text-ink transition-colors"
                    @click="confirmDelete = false"
                  >
                    キャンセル
                  </button>
                  <button
                    type="button"
                    class="flex-1 rounded-xl bg-danger text-white hover:opacity-90 px-3 py-2 text-xs font-bold transition-opacity"
                    @click="emit('delete'); close()"
                  >
                    削除する
                  </button>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
