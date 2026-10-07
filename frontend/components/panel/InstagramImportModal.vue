<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { X, Instagram, Check, Download, RefreshCw, LogIn } from 'lucide-vue-next'
import type { InstagramMediaPost } from '~/types'
import { useBoardStore } from '~/stores/boardStore'
import { useBackendUrl } from '~/composables/useBackendUrl'
import { useToast } from '~/composables/useToast'

const props = defineProps<{
  isOpen: boolean
  boardId: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'imported'): void
}>()

const { apiBase } = useBackendUrl()
const boardStore = useBoardStore()
const toast = useToast()

const isLoading = ref(false)
const isImporting = ref(false)
const isConnected = ref(false)
const username = ref('')
const mediaList = ref<InstagramMediaPost[]>([])
const selectedMediaIds = ref<string[]>([])

async function fetchInstagramMedia() {
  isLoading.value = true
  try {
    const res = await $fetch<{ connected: boolean; username: string; media: InstagramMediaPost[] }>(
      `${apiBase.value}/instagram/media`
    )
    isConnected.value = res.connected
    username.value = res.username
    mediaList.value = res.media || []
  } catch (e: any) {
    toast.error('Instagramの取得に失敗しました', e?.message)
  } finally {
    isLoading.value = false
  }
}

function toggleSelect(id: string) {
  const idx = selectedMediaIds.value.indexOf(id)
  if (idx >= 0) selectedMediaIds.value.splice(idx, 1)
  else selectedMediaIds.value.push(id)
}

const allSelected = computed(
  () => mediaList.value.length > 0 && selectedMediaIds.value.length === mediaList.value.length
)

function selectAll() {
  selectedMediaIds.value = allSelected.value ? [] : mediaList.value.map(m => m.id)
}

async function handleImport() {
  if (!selectedMediaIds.value.length || !props.boardId) return
  isImporting.value = true

  const selectedPosts = mediaList.value.filter(m => selectedMediaIds.value.includes(m.id))

  try {
    await $fetch(`${apiBase.value}/instagram/import`, {
      method: 'POST',
      body: {
        board_id: props.boardId,
        media_urls: selectedPosts.map(p => p.media_url),
        captions: selectedPosts.map(p => p.caption || 'Instagram Reference'),
      },
    })
    await boardStore.loadBoard(props.boardId)
    toast.success(`${selectedPosts.length} 件の投稿を取り込みました`)
    emit('imported')
    emit('close')
    selectedMediaIds.value = []
  } catch (e: any) {
    toast.error('取り込みに失敗しました', e?.data?.detail || e?.message)
  } finally {
    isImporting.value = false
  }
}

async function connectInstagram() {
  try {
    const res = await $fetch<{ auth_url: string }>(`${apiBase.value}/instagram/auth-url`)
    window.location.href = res.auth_url
  } catch (e: any) {
    toast.error('認証URLの取得に失敗しました', e?.data?.detail || e?.message)
  }
}

onMounted(() => {
  if (props.isOpen) fetchInstagramMedia()
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
        class="w-full max-w-3xl max-h-[85vh] rounded-2xl border border-canvas-border bg-canvas-panel shadow-pop flex flex-col overflow-hidden animate-scale-in"
        role="dialog"
        aria-modal="true"
        aria-label="Instagramから取り込む"
      >
        <!-- ヘッダー -->
        <div class="p-4 border-b border-canvas-border flex items-center justify-between gap-3 shrink-0">
          <div class="flex items-center gap-2.5 min-w-0">
            <div class="p-2 rounded-xl bg-instagram text-white">
              <Instagram class="w-4 h-4" />
            </div>
            <div class="min-w-0">
              <h3 class="text-sm font-semibold text-ink">Instagramから取り込む</h3>
              <p class="text-[11px] text-ink-subtle truncate">
                <template v-if="isConnected">
                  接続中: <span class="text-instagram font-medium">@{{ username }}</span>
                </template>
                <template v-else>未接続（デモフィードを表示中）</template>
              </p>
            </div>
          </div>

          <div class="flex items-center gap-1.5">
            <button
              type="button"
              class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
              aria-label="再読み込み"
              @click="fetchInstagramMedia"
            >
              <RefreshCw class="w-4 h-4" :class="isLoading ? 'animate-spin' : ''" />
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

        <!-- コンテンツ -->
        <div class="flex-1 overflow-y-auto p-4">
          <div v-if="isLoading" class="py-14 flex flex-col items-center justify-center gap-3">
            <div class="w-7 h-7 rounded-full border-2 border-instagram border-t-transparent animate-spin" />
            <p class="text-[11px] text-ink-muted font-mono">投稿を取得中...</p>
          </div>

          <template v-else>
            <div class="flex items-center justify-between mb-3">
              <p class="text-[11px] text-ink-muted">取り込むリファレンス画像を選択してください</p>
              <button
                type="button"
                class="text-[11px] font-medium text-brand hover:underline"
                @click="selectAll"
              >
                {{ allSelected ? '選択解除' : 'すべて選択' }}
              </button>
            </div>

            <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <figure
                v-for="post in mediaList"
                :key="post.id"
                class="group relative rounded-xl overflow-hidden aspect-square border cursor-pointer transition-colors"
                :class="selectedMediaIds.includes(post.id)
                  ? 'border-instagram ring-2 ring-instagram/40'
                  : 'border-canvas-border hover:border-canvas-border-strong'"
                @click="toggleSelect(post.id)"
              >
                <img
                  :src="post.media_url"
                  :alt="post.caption || 'Instagram photo'"
                  class="w-full h-full object-cover pointer-events-none"
                  loading="lazy"
                >

                <span
                  class="absolute top-2 right-2 w-5 h-5 rounded-full border flex items-center justify-center transition-all"
                  :class="selectedMediaIds.includes(post.id)
                    ? 'bg-instagram border-instagram'
                    : 'bg-canvas-panel/85 border-canvas-border-strong opacity-0 group-hover:opacity-100'"
                >
                  <Check v-if="selectedMediaIds.includes(post.id)" class="w-3 h-3 text-white stroke-[3]" />
                </span>

                <figcaption
                  v-if="post.caption"
                  class="absolute bottom-0 inset-x-0 bg-canvas-panel/95 px-2 py-1 text-[10px] text-ink-muted line-clamp-2 leading-tight opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  {{ post.caption }}
                </figcaption>
              </figure>
            </div>
          </template>
        </div>

        <!-- フッター -->
        <div class="p-3 border-t border-canvas-border flex items-center justify-between gap-3 shrink-0">
          <button
            type="button"
            class="flex items-center gap-1.5 text-[11px] text-ink-subtle hover:text-instagram transition-colors"
            @click="connectInstagram"
          >
            <LogIn class="w-3.5 h-3.5" />
            Instagram アカウントを接続
          </button>

          <div class="flex items-center gap-2">
            <span class="text-[11px] text-ink-muted">
              <span class="text-ink font-semibold">{{ selectedMediaIds.length }}</span> 件選択中
            </span>
            <button
              type="button"
              class="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-instagram text-white hover:bg-instagram-hover transition-colors disabled:opacity-50 flex items-center gap-1.5"
              :disabled="!selectedMediaIds.length || isImporting"
              @click="handleImport"
            >
              <Download class="w-3.5 h-3.5" />
              {{ isImporting ? '取り込み中...' : 'キャンバスへ' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>