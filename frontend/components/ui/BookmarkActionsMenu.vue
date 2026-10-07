<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { ExternalLink, FolderInput, Layers, MoreHorizontal, Trash2 } from 'lucide-vue-next'
import type { BookmarkItem, FolderItem } from '~/types'

const props = defineProps<{ item: BookmarkItem; folders: FolderItem[] }>()
const emit = defineEmits<{
  place: []
  move: [folderName: string]
  delete: []
}>()

const root = ref<HTMLElement | null>(null)
const open = ref(false)
const section = ref<'actions' | 'folders' | 'delete'>('actions')

function close() {
  open.value = false
  section.value = 'actions'
}

function onOutsideClick(event: MouseEvent) {
  if (root.value && !root.value.contains(event.target as Node)) close()
}

function onEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') close()
}

watch(open, value => {
  if (value) {
    document.addEventListener('click', onOutsideClick)
    document.addEventListener('keydown', onEscape)
  } else {
    document.removeEventListener('click', onOutsideClick)
    document.removeEventListener('keydown', onEscape)
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onOutsideClick)
  document.removeEventListener('keydown', onEscape)
})

function chooseFolder(name: string) {
  if (name !== props.item.folder_name) emit('move', name)
  close()
}
</script>

<template>
  <div ref="root" class="relative z-20 shrink-0" @click.stop>
    <button
      type="button"
      class="p-1.5 rounded-lg bg-canvas-raised/95 text-ink-muted hover:text-ink border border-canvas-border shadow-sm transition-colors"
      :aria-label="`${item.title}の操作メニュー`"
      aria-haspopup="menu"
      :aria-expanded="open"
      @click="open ? close() : (open = true)"
    >
      <MoreHorizontal class="w-4 h-4" />
    </button>

    <div
      v-if="open"
      class="absolute right-0 top-full mt-1 w-48 max-h-72 overflow-y-auto rounded-xl border border-canvas-border bg-canvas-panel shadow-xl p-1 text-[11px]"
      role="menu"
      :aria-label="`${item.title}の操作`"
    >
      <template v-if="section === 'actions'">
        <button type="button" role="menuitem" class="menu-item" @click="emit('place'); close()">
          <Layers class="w-3.5 h-3.5" /> キャンバスへ配置
        </button>
        <a
          v-if="item.source_url"
          :href="item.source_url"
          target="_blank"
          rel="noopener noreferrer"
          role="menuitem"
          class="menu-item"
          @click="close"
        >
          <ExternalLink class="w-3.5 h-3.5" /> 元のページを開く
        </a>
        <button type="button" role="menuitem" class="menu-item" @click="section = 'folders'">
          <FolderInput class="w-3.5 h-3.5" /> フォルダを変更
        </button>
        <button type="button" role="menuitem" class="menu-item text-danger" @click="section = 'delete'">
          <Trash2 class="w-3.5 h-3.5" /> ライブラリから削除
        </button>
      </template>

      <template v-else-if="section === 'folders'">
        <p class="px-2 py-1 text-ink-muted">移動先のフォルダ</p>
        <button
          v-for="folder in folders"
          :key="folder.name"
          type="button"
          role="menuitem"
          class="menu-item"
          :disabled="folder.name === item.folder_name"
          @click="chooseFolder(folder.name)"
        >
          <span class="truncate">{{ folder.name }}</span>
          <span v-if="folder.name === item.folder_name" class="ml-auto text-brand">✓</span>
        </button>
        <button type="button" class="menu-item text-ink-muted" @click="section = 'actions'">戻る</button>
      </template>

      <template v-else>
        <p class="px-2 py-1.5 text-ink">このブックマークを削除しますか？</p>
        <div class="flex gap-1 p-1">
          <button type="button" class="flex-1 rounded-lg border border-canvas-border px-2 py-1.5" @click="section = 'actions'">キャンセル</button>
          <button type="button" class="flex-1 rounded-lg bg-danger text-white px-2 py-1.5" @click="emit('delete'); close()">削除する</button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.menu-item {
  @apply w-full flex items-center gap-2 rounded-lg px-2 py-2 text-left hover:bg-canvas-hover disabled:opacity-50 disabled:cursor-default;
}
</style>
