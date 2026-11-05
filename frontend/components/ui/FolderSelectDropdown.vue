<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Folder, FolderPlus, Check, ChevronDown, Plus, Search, X } from 'lucide-vue-next'
import type { FolderItem } from '~/types'
import { useBoardStore } from '~/stores/boardStore'
import { useToast } from '~/composables/useToast'

const props = withDefaults(
  defineProps<{
    modelValue?: string | null
    folders?: FolderItem[]
    compact?: boolean
    size?: 'sm' | 'md'
    align?: 'left' | 'right' | 'top'
    placeholder?: string
    disabled?: boolean
  }>(),
  {
    modelValue: 'All References',
    compact: false,
    size: 'md',
    align: 'left',
    placeholder: 'フォルダを選択',
    disabled: false,
  }
)

const emit = defineEmits<{
  'update:modelValue': [folderName: string]
  'change': [folderName: string]
}>()

const boardStore = useBoardStore()
const toast = useToast()

const isOpen = ref(false)
const popoverRef = ref<HTMLElement | null>(null)
const triggerRef = ref<HTMLElement | null>(null)
const folderSearch = ref('')
const isCreating = ref(false)
const newName = ref('')
const newFolderInputRef = ref<HTMLInputElement | null>(null)

const availableFolders = computed<FolderItem[]>(() => {
  const list = props.folders || boardStore.folders
  if (!list.length) {
    return [{ name: 'All References', icon: 'layers', color: '#6366f1', count: boardStore.bookmarks.length }]
  }
  return list
})

const selectedFolderItem = computed(() => {
  const current = props.modelValue || 'All References'
  return availableFolders.value.find(f => f.name === current) || {
    name: current,
    color: '#6366f1',
    count: 0,
  }
})

const filteredFolders = computed(() => {
  const q = folderSearch.value.trim().toLowerCase()
  if (!q) return availableFolders.value
  return availableFolders.value.filter(f =>
    f.name.toLowerCase().includes(q) || (f.name === 'All References' && 'すべての資料'.includes(q))
  )
})

function formatLabel(name: string): string {
  if (name === 'All References') return 'すべての資料'
  return name
}

function selectFolder(name: string) {
  emit('update:modelValue', name)
  emit('change', name)
  isOpen.value = false
  folderSearch.value = ''
  isCreating.value = false
}

function toggleOpen() {
  if (props.disabled) return
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    folderSearch.value = ''
    isCreating.value = false
  }
}

function startCreating() {
  isCreating.value = true
  newName.value = ''
  nextTick(() => {
    newFolderInputRef.value?.focus()
  })
}

async function handleCreateNewFolder() {
  const name = newName.value.trim()
  if (!name) {
    isCreating.value = false
    return
  }

  const existing = availableFolders.value.find(f => f.name.toLowerCase() === name.toLowerCase())
  if (existing) {
    selectFolder(existing.name)
    return
  }

  await boardStore.createFolder(name)
  selectFolder(name)
  toast.success('新規フォルダを作成しました', name)
}

function handleClickOutside(event: MouseEvent) {
  if (!isOpen.value) return
  const target = event.target as Node | null
  if (
    popoverRef.value &&
    !popoverRef.value.contains(target) &&
    triggerRef.value &&
    !triggerRef.value.contains(target)
  ) {
    isOpen.value = false
  }
}

function handleKeyDown(event: KeyboardEvent) {
  if (event.key === 'Escape' && isOpen.value) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleKeyDown)
  if (!boardStore.folders.length) {
    boardStore.fetchFolders()
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleKeyDown)
})
</script>

<template>
  <div class="relative inline-block text-left">
    <!-- トリガーボタン -->
    <button
      ref="triggerRef"
      type="button"
      :disabled="disabled"
      class="group inline-flex items-center gap-1.5 rounded-xl border transition-all text-xs font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand disabled:opacity-50 select-none"
      :class="[
        compact
          ? 'px-2 py-1 text-[11px] bg-canvas-card/90 hover:bg-canvas-card border-canvas-border text-ink'
          : 'px-2.5 py-1.5 bg-canvas-card hover:bg-canvas-hover border-canvas-border-strong text-ink shadow-sm',
        isOpen ? 'border-brand ring-2 ring-brand/25' : ''
      ]"
      :aria-expanded="isOpen"
      :aria-label="`保存先フォルダ: ${formatLabel(selectedFolderItem.name)}`"
      @click="toggleOpen"
    >
      <span
        class="w-2.5 h-2.5 rounded-full shrink-0 shadow-sm"
        :style="{ backgroundColor: selectedFolderItem.color || '#6366f1' }"
      />
      <span class="truncate max-w-[110px] sm:max-w-[140px] text-left">
        {{ formatLabel(selectedFolderItem.name) }}
      </span>
      <ChevronDown
        class="w-3.5 h-3.5 text-ink-muted transition-transform shrink-0"
        :class="isOpen ? 'rotate-180 text-brand' : 'group-hover:text-ink'"
      />
    </button>

    <!-- ドロップダウンメニュー -->
    <div
      v-if="isOpen"
      ref="popoverRef"
      class="absolute z-50 mt-1 w-60 rounded-2xl border border-canvas-border-strong bg-canvas-panel shadow-pop p-1.5 flex flex-col gap-1 text-xs animate-scale-in"
      :class="[
        align === 'right' ? 'right-0' : 'left-0',
        align === 'top' ? 'bottom-full mb-1 mt-0' : 'top-full'
      ]"
      role="menu"
      aria-label="フォルダ選択メニュー"
    >
      <!-- ヘッダー & 検索 -->
      <div class="px-2 pt-1 pb-1.5 flex items-center justify-between gap-1 border-b border-canvas-border">
        <span class="text-[10px] font-bold text-ink-subtle uppercase tracking-wider">保存先フォルダ</span>
        <span class="text-[10px] font-mono text-ink-muted">{{ availableFolders.length }}件</span>
      </div>

      <div v-if="availableFolders.length > 3" class="relative px-1 pt-1">
        <Search class="absolute left-3 top-2.5 w-3.5 h-3.5 text-ink-subtle pointer-events-none" />
        <input
          v-model="folderSearch"
          type="search"
          placeholder="フォルダを検索..."
          class="w-full bg-canvas-card border border-canvas-border rounded-lg pl-7 pr-2 py-1 text-xs text-ink placeholder:text-ink-subtle focus:outline-none focus:border-brand"
        >
      </div>

      <!-- フォルダ一覧リスト -->
      <div class="max-h-52 overflow-y-auto space-y-0.5 p-1 no-scrollbar">
        <button
          v-for="f in filteredFolders"
          :key="f.name"
          type="button"
          class="w-full flex items-center justify-between gap-2 px-2.5 py-1.5 rounded-lg text-left transition-colors"
          :class="f.name === (modelValue || 'All References')
            ? 'bg-brand-soft text-brand font-bold'
            : 'text-ink hover:bg-canvas-hover font-medium'"
          role="menuitem"
          @click="selectFolder(f.name)"
        >
          <div class="flex items-center gap-2 min-w-0">
            <span
              class="w-2 h-2 rounded-full shrink-0"
              :style="{ backgroundColor: f.color || '#6366f1' }"
            />
            <span class="truncate">{{ formatLabel(f.name) }}</span>
          </div>
          <div class="flex items-center gap-1 shrink-0">
            <span v-if="f.count !== undefined" class="text-[10px] font-mono text-ink-muted">
              {{ f.count }}
            </span>
            <Check
              v-if="f.name === (modelValue || 'All References')"
              class="w-3.5 h-3.5 text-brand stroke-[2.5]"
            />
          </div>
        </button>

        <div v-if="!filteredFolders.length" class="py-3 text-center text-ink-subtle text-[11px]">
          フォルダが見つかりません
        </div>
      </div>

      <!-- インライン新規フォルダ作成 -->
      <div class="pt-1 border-t border-canvas-border px-1">
        <div v-if="isCreating" class="flex items-center gap-1">
          <input
            ref="newFolderInputRef"
            v-model="newName"
            type="text"
            maxlength="40"
            placeholder="フォルダ名を入力..."
            class="flex-1 min-w-0 bg-canvas-card border border-canvas-border-strong rounded-lg px-2 py-1 text-xs text-ink placeholder:text-ink-subtle focus:outline-none focus:border-brand"
            @keydown.enter.prevent="handleCreateNewFolder"
            @keydown.esc.prevent="isCreating = false"
          >
          <button
            type="button"
            class="p-1 rounded-lg bg-brand text-brand-fg hover:bg-brand-hover text-xs font-bold shrink-0 transition-colors"
            title="追加"
            :disabled="!newName.trim()"
            @click="handleCreateNewFolder"
          >
            <Check class="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            class="p-1 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover shrink-0 transition-colors"
            title="キャンセル"
            @click="isCreating = false"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>

        <button
          v-else
          type="button"
          class="w-full flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-ink-muted hover:text-brand hover:bg-brand-soft/40 font-semibold text-left transition-colors"
          @click="startCreating"
        >
          <Plus class="w-3.5 h-3.5" />
          <span>新規フォルダ作成</span>
        </button>
      </div>
    </div>
  </div>
</template>

