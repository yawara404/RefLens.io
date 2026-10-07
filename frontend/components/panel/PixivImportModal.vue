<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import {
  X,
  Compass,
  Search,
  Check,
  RefreshCw,
  LogOut,
  Link2,
  Layers,
  Bookmark,
  Info,
} from 'lucide-vue-next'
import { useBoardStore } from '~/stores/boardStore'
import { usePixiv } from '~/composables/usePixiv'
import PixivImage from '~/components/ui/PixivImage.vue'
import { useToast } from '~/composables/useToast'

const props = defineProps<{
  isOpen: boolean
  boardId: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'imported'): void
}>()

const boardStore = useBoardStore()
const pixiv = usePixiv()
const toast = useToast()

const searchInput = ref('')
const selectedIds = ref<string[]>([])

const categories = [
  { id: 'recommended', label: 'おすすめ' },
  { id: 'ranking', label: '人気' },
  { id: 'following', label: 'フォロー' },
  { id: 'bookmarks', label: 'ブックマーク' },
]

const canSelectAll = computed(() => pixiv.items.value.length > 0)
const allOnPageSelected = computed(() => canSelectAll.value && pixiv.items.value.every(item => pixiv.isSelected(item.id)))

async function load() {
  pixiv.clearSelection()
  await pixiv.fetchStatus()
  await pixiv.loadFeed('recommended')
}

function submitSearch() {
  pixiv.setQuery(searchInput.value)
  pixiv.clearSelection()
  pixiv.loadFeed('search')
}

function pickCategory(id: string) {
  if ((id === 'following' || id === 'bookmarks') && !pixiv.isConnected.value) {
    pixiv.connect()
    return
  }
  pixiv.clearSelection()
  pixiv.loadFeed(id)
}

function toggleSelect(id: string) {
  pixiv.toggleSelection(id)
}

function toggleSelectAll() {
  if (!canSelectAll.value) return
  const pageIds = new Set(pixiv.items.value.map(item => item.id))
  if (allOnPageSelected.value) {
    pixiv.selectedIds.value = pixiv.selectedIds.value.filter(id => !pageIds.has(id))
  } else {
    pixiv.items.value.forEach((item) => {
      if (!pixiv.isSelected(item.id)) pixiv.selectedIds.value.push(item.id)
    })
  }
}

async function handleImport(placeOnCanvas: boolean) {
  const ids = [...pixiv.selectedIds.value]
  if (!ids.length) return

  const count = placeOnCanvas
    ? await pixiv.stockToCanvas(ids, props.boardId)
    : await pixiv.stockToLibrary(ids)

  if (!count) return

  if (placeOnCanvas) {
    await boardStore.loadBoard(props.boardId)
    emit('imported')
  } else {
    await boardStore.fetchBookmarks()
    await boardStore.fetchFolders()
  }

  toast.success(`${count} 作品を${placeOnCanvas ? 'キャンバスへ配置' : 'ライブラリへ保存'}しました`)
  pixiv.clearSelection()
  emit('close')
}

function copyId(id: string) {
  navigator.clipboard.writeText(`https://www.pixiv.net/artworks/${id}`)
  toast.success('作品URLをコピーしました')
}

watch(() => props.isOpen, (open) => {
  if (open && !pixiv.items.value.length) load()
})

onMounted(() => {
  if (props.isOpen) load()
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="fixed inset-0 z-[60] flex items-center justify-center p-4 scrim animate-fade-in"
      @click.self="emit('close')"
    >
      <div
        class="w-full max-w-5xl max-h-[85vh] rounded-2xl border border-canvas-border bg-canvas-panel shadow-pop flex flex-col overflow-hidden animate-scale-in"
        role="dialog"
        aria-modal="true"
        aria-label="pixivから取り込む"
      >
        <!-- ヘッダー -->
        <div class="p-4 border-b border-canvas-border flex items-center justify-between gap-3 shrink-0">
          <div class="flex items-center gap-2.5 min-w-0">
            <div class="p-2 rounded-xl bg-pixiv text-white">
              <Compass class="w-4 h-4" />
            </div>
            <div class="min-w-0">
              <h3 class="text-sm font-semibold text-ink">pixivから取り込む</h3>
              <p class="text-[11px] text-ink-subtle truncate">
                <template v-if="pixiv.isConnected.value">
                  接続中: <span class="text-pixiv font-medium">{{ pixiv.accountName.value }}</span>
                </template>
                <template v-else>Pixivに接続するとフォロー中・ブックマークを表示できます</template>
              </p>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <button
              v-if="pixiv.isConnected.value"
              type="button"
              class="p-1.5 rounded-lg text-ink-muted hover:text-danger hover:bg-danger-soft transition-colors"
              title="pixiv接続を解除"
              aria-label="pixiv接続を解除"
              @click="pixiv.disconnect()"
            >
              <LogOut class="w-4 h-4" />
            </button>
            <button
              type="button"
              class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
              aria-label="更新"
              @click="load"
            >
              <RefreshCw class="w-4 h-4" :class="pixiv.isLoading.value ? 'animate-spin' : ''" />
            </button>
            <button
              type="button"
              class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
              aria-label="閉じる"
              @click="emit('close')"
            >
              <X class="w-4 h-4" />
            </button>
          </div>
        </div>

        <!-- 検索バー -->
        <div class="p-3 border-b border-canvas-border flex flex-col gap-2.5 shrink-0">
          <div class="flex items-center gap-2">
            <div class="relative flex-1">
              <Search class="absolute left-3 w-3.5 h-3.5 text-ink-subtle pointer-events-none" />
              <input
                v-model="searchInput"
                type="search"
                placeholder="タグやキーワードで検索（例: ポーズ参考、逆光）"
                class="w-full bg-canvas-card border border-canvas-border rounded-full pl-8 pr-3 py-1.5 text-xs text-ink placeholder:text-ink-subtle focus:outline-none focus:border-pixiv transition-colors"
                @keydown.enter="submitSearch"
              />
            </div>
            <button
              type="button"
              class="px-3 py-1.5 rounded-full text-xs font-semibold bg-pixiv text-white hover:bg-pixiv-hover transition-colors"
              @click="submitSearch"
            >
              検索
            </button>
          </div>

          <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
            <button
              v-for="cat in categories"
              :key="cat.id"
              type="button"
              class="px-3 py-1 rounded-full text-[11px] font-medium whitespace-nowrap border transition-colors"
              :class="pixiv.currentCategory.value === cat.id
                ? 'bg-pixiv border-pixiv text-white'
                : 'bg-canvas-card border-canvas-border text-ink-muted hover:text-ink hover:bg-canvas-hover'"
              :title="!pixiv.isConnected.value && (cat.id === 'following' || cat.id === 'bookmarks') ? 'Pixivへの接続が必要です' : undefined"
              @click="pickCategory(cat.id)"
            >
              {{ cat.label }}
            </button>
          </div>

          <!-- 未接続バナー -->
          <div
            v-if="!pixiv.isConnected.value"
            class="flex items-start gap-2 p-2.5 rounded-lg border border-canvas-border bg-canvas-card"
          >
            <Info class="w-3.5 h-3.5 text-ink-subtle shrink-0 mt-px" />
            <p class="text-[11px] text-ink-muted leading-relaxed">
              {{ pixiv.statusMessage.value || 'デモフィードを表示中' }}
            </p>
            <button
              v-if="pixiv.canConnect.value"
              type="button"
              class="shrink-0 px-2.5 py-1 rounded-md bg-pixiv text-white text-[11px] font-semibold hover:bg-pixiv-hover transition-colors"
              @click="pixiv.connect()"
            >
              Pixivに接続
            </button>
          </div>
        </div>

        <!-- グリッド -->
        <div class="flex-1 overflow-y-auto p-4">
          <div v-if="pixiv.isLoading.value" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            <div v-for="i in 8" :key="i" class="aspect-square rounded-xl bg-canvas-card animate-pulse" />
          </div>

          <div
            v-else-if="!pixiv.items.value.length"
            class="py-16 text-center space-y-2"
          >
            <Compass class="w-7 h-7 text-ink-subtle mx-auto" />
            <p class="text-xs text-ink-muted">{{ pixiv.feedError.value ? 'Pixivの取得に失敗しました' : pixiv.currentCategory.value === 'bookmarks' ? 'このPixivアカウントの公開ブックマークはありません' : '作品が見つかりませんでした' }}</p>
            <p v-if="pixiv.feedError.value" class="text-[11px] text-danger">{{ pixiv.feedError.value }}</p>
            <p v-else-if="pixiv.currentCategory.value === 'bookmarks'" class="text-[11px] text-ink-subtle">連携先: {{ pixiv.accountName.value }}</p>
          </div>

          <div v-else class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            <figure
              v-for="item in pixiv.items.value"
              :key="item.id"
              class="group relative rounded-xl overflow-hidden border cursor-pointer transition-colors"
              :class="pixiv.isSelected(item.id)
                ? 'border-pixiv ring-2 ring-pixiv/40'
                : 'border-canvas-border hover:border-canvas-border-strong'"
              @click="toggleSelect(item.id)"
            >
              <div class="relative aspect-square bg-canvas-sunken">
                <PixivImage
                  :src="item.image_url"
                  :alt="item.title"
                  class="w-full h-full object-cover pointer-events-none"
                  loading="lazy"
                />

                <!-- 選択チェック -->
                <span
                  class="absolute top-2 right-2 w-5 h-5 rounded-full border flex items-center justify-center transition-colors"
                  :class="pixiv.isSelected(item.id)
                    ? 'bg-pixiv border-pixiv'
                    : 'bg-canvas-panel/80 border-canvas-border-strong opacity-0 group-hover:opacity-100'"
                >
                  <Check v-if="pixiv.isSelected(item.id)" class="w-3 h-3 text-white stroke-[3]" />
                </span>

                <!-- ページ数 -->
                <span
                  v-if="item.page_count > 1"
                  class="absolute top-2 left-2 px-1.5 py-0.5 rounded text-[10px] font-bold bg-canvas-panel/90 text-ink border border-canvas-border"
                >
                  {{ item.page_count }}P
                </span>

                <!-- ホバー: タイトル -->
                <figcaption
                  class="absolute bottom-0 inset-x-0 bg-canvas-panel/95 px-2 py-1.5 text-[10px] text-ink-muted truncate opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  {{ item.title }}
                </figcaption>
              </div>

              <!-- フッター -->
              <div class="p-2 bg-canvas-card border-t border-canvas-border space-y-1">
                <p class="text-[11px] font-medium text-ink truncate" :title="item.title">
                  {{ item.title }}
                </p>
                <div class="flex items-center justify-between gap-2">
                  <span class="text-[10px] text-ink-subtle truncate">{{ item.author_name }}</span>
                  <button
                    type="button"
                    class="shrink-0 p-0.5 rounded text-ink-subtle hover:text-pixiv transition-colors"
                    title="作品URLをコピー"
                    aria-label="作品URLをコピー"
                    @click.stop="copyId(item.id)"
                  >
                    <Link2 class="w-3 h-3" />
                  </button>
                </div>
              </div>
            </figure>
          </div>
        </div>

        <!-- フッター -->
        <div class="p-3 border-t border-canvas-border flex items-center justify-between gap-3 shrink-0">
          <div class="flex items-center gap-3">
            <button
              type="button"
              class="text-[11px] text-ink-subtle hover:text-ink transition-colors disabled:opacity-40"
              :disabled="!canSelectAll"
              @click="toggleSelectAll"
            >
              {{ allOnPageSelected ? 'このページの選択解除' : 'このページをすべて選択' }}
            </button>
            <div class="flex items-center gap-1 text-[11px] text-ink-muted">
              <button type="button" class="px-2 py-1 rounded hover:bg-canvas-hover disabled:opacity-40" :disabled="pixiv.isLoading.value || pixiv.currentPage.value <= 1" @click="pixiv.prevPage()">前へ</button>
              <span>{{ pixiv.currentPage.value }} ページ</span>
              <button type="button" class="px-2 py-1 rounded hover:bg-canvas-hover disabled:opacity-40" :disabled="pixiv.isLoading.value || !pixiv.hasNext.value" @click="pixiv.nextPage()">次へ</button>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <span class="text-[11px] text-ink-muted">
              <span class="text-ink font-semibold">{{ pixiv.selectedIds.value.length }}</span> 件選択中
            </span>
            <button
              type="button"
              class="px-3 py-1.5 rounded-lg text-xs font-medium text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors disabled:opacity-40"
              :disabled="!pixiv.selectedIds.value.length || pixiv.isImporting.value"
              @click="handleImport(false)"
            >
              <Bookmark class="w-3.5 h-3.5 inline mr-1" />
              Libraryへ
            </button>
            <button
              type="button"
              class="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-pixiv text-white hover:bg-pixiv-hover transition-colors disabled:opacity-50 flex items-center gap-1.5"
              :disabled="!pixiv.selectedIds.value.length || pixiv.isImporting.value"
              @click="handleImport(true)"
            >
              <Layers class="w-3.5 h-3.5" />
              {{ pixiv.isImporting.value ? '取り込み中...' : 'キャンバスへ' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
