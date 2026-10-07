<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  X,
  Sparkles,
  Compass,
  Sun,
  UserCheck,
  Shirt,
  Palette,
  Tag,
  RefreshCw,
  Check,
} from 'lucide-vue-next'
import type { CanvasItem } from '~/types'
import { useBoardStore } from '~/stores/boardStore'
import { useImageProcessor } from '~/composables/useImageProcessor'
import { useMediaUrl } from '~/composables/useMediaUrl'
import { useToast } from '~/composables/useToast'

const props = defineProps<{
  item: CanvasItem | null
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'select-tag', tag: string): void
}>()

const boardStore = useBoardStore()
const { copyToClipboard } = useImageProcessor()
const toast = useToast()

const isReanalyzing = ref(false)
const copiedHex = ref<string | null>(null)
const { resolveMediaUrl } = useMediaUrl()

const pixivPolicy = computed(() => props.item?.media?.source_type === 'pixiv'
  ? (props.item.media.ai_analysis_policy || 'unknown')
  : 'allowed')
const analysis = computed(() => pixivPolicy.value === 'allowed' ? props.item?.ai_analysis : null)

const resolvedImageUrl = computed(() => resolveMediaUrl(props.item?.media?.file_path))

async function handleReanalyze() {
  if (!props.item?.media_item_id || pixivPolicy.value === 'blocked') return
  isReanalyzing.value = true
  try {
    if (await boardStore.reanalyzeActiveItem()) toast.success('AI解析を更新しました')
  } catch (e: any) {
    toast.error('AI解析に失敗しました', e?.data?.detail || e?.message)
  } finally {
    isReanalyzing.value = false
  }
}

async function handleCopyHex(hex: string) {
  if (await copyToClipboard(hex)) {
    copiedHex.value = hex
    setTimeout(() => { copiedHex.value = null }, 1400)
  } else {
    toast.error('クリップボードにコピーできませんでした')
  }
}

const SECTIONS = [
  {
    key: 'composition',
    label: '構図 (Composition)',
    icon: Compass,
    color: 'text-ok',
  },
  {
    key: 'lighting',
    label: 'ライティング (Lighting)',
    icon: Sun,
    color: 'text-warn',
  },
  {
    key: 'pose_anatomy',
    label: 'ポーズ・重心 (Pose & Anatomy)',
    icon: UserCheck,
    color: 'text-instagram',
  },
  {
    key: 'costume_structure',
    label: '衣装構造・シワ (Costume & Folds)',
    icon: Shirt,
    color: 'text-brand',
  },
] as const
</script>

<template>
  <aside
    v-if="isOpen"
    class="relative h-full w-full sm:w-[min(400px,34vw)] shrink-0 flex flex-col border-l border-canvas-border bg-canvas-panel shadow-pop"
    aria-label="AI解析サイドバー"
  >
    <!-- ヘッダー -->
    <div class="p-3.5 border-b border-canvas-border flex items-center justify-between shrink-0">
      <div class="flex items-center gap-2">
        <div class="p-1.5 rounded-lg bg-brand-soft text-brand">
          <Sparkles class="w-4 h-4" />
        </div>
        <div>
          <h2 class="text-xs font-semibold text-ink">RefLens Vision AI</h2>
          <p class="text-[10px] text-ink-subtle">マルチモーダル視覚解析</p>
        </div>
      </div>

      <div class="flex items-center gap-1">
        <button
          type="button"
          class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors disabled:opacity-50"
          :class="isReanalyzing ? 'animate-spin' : ''"
          title="AI解析を再実行"
          aria-label="AI解析を再実行"
          :disabled="isReanalyzing || !props.item || pixivPolicy === 'blocked'"
          @click="handleReanalyze"
        >
          <RefreshCw class="w-4 h-4" />
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
    <div v-if="item" class="flex-1 overflow-y-auto p-3.5 space-y-3">
      <!-- プレビュー -->
      <div class="relative rounded-xl overflow-hidden bg-canvas-sunken border border-canvas-border aspect-video">
        <img
          :src="resolvedImageUrl"
          :alt="item.caption || 'Reference preview'"
          class="w-full h-full object-cover"
        />
        <div class="absolute bottom-0 inset-x-0 bg-canvas-panel/95 px-3 py-1.5 text-[11px] text-ink truncate">
          {{ item.caption || item.media?.original_file_name || 'Selected Reference' }}
        </div>
      </div>

      <div v-if="pixivPolicy === 'blocked'" class="rounded-xl border border-canvas-border bg-canvas-card p-4 text-xs text-ink-muted leading-relaxed">
        作者がAI学習禁止を明示しているため、このPixiv作品はAI解析しません。
      </div>
      <div v-else-if="pixivPolicy === 'unlisted'" class="rounded-xl border border-canvas-border bg-canvas-card p-4 space-y-3 text-xs text-ink-muted leading-relaxed">
        Danbooruで同じPixiv作品IDの掲載を確認できないため、AI解析は停止しています。
        <button type="button" class="block rounded-lg bg-brand px-3 py-1.5 text-brand-fg" @click="handleReanalyze">
          掲載を再確認して解析
        </button>
      </div>
      <div v-else-if="pixivPolicy === 'unknown'" class="rounded-xl border border-canvas-border bg-canvas-card p-4 space-y-3 text-xs text-ink-muted leading-relaxed">
        Pixiv作品情報またはDanbooru掲載を確認できないため、AI解析は停止しています。
        <button type="button" class="block rounded-lg bg-brand px-3 py-1.5 text-brand-fg" @click="handleReanalyze">
          条件を再確認して解析
        </button>
      </div>
      <!-- 解析中 -->
      <div v-else-if="isReanalyzing" class="py-14 flex flex-col items-center justify-center gap-3">
        <div class="w-7 h-7 rounded-full border-2 border-brand border-t-transparent animate-spin" />
        <p class="text-[11px] text-ink-muted font-mono">視覚構造を解析中...</p>
      </div>

      <template v-else-if="analysis">
        <!-- カラーパレット -->
        <section v-if="analysis.palette?.length" class="p-3 rounded-xl bg-canvas-card border border-canvas-border space-y-2">
          <h3 class="flex items-center gap-1.5 text-[11px] font-semibold text-ink">
            <Palette class="w-3.5 h-3.5 text-brand" />
            抽出カラーパレット
          </h3>
          <div class="grid grid-cols-5 gap-1.5">
            <button
              v-for="(hex, idx) in analysis.palette"
              :key="idx"
              type="button"
              class="group flex flex-col items-center rounded-lg p-1 border border-canvas-border hover:border-brand transition-colors"
              :title="`${hex} をコピー`"
              :aria-label="`カラーパレット ${hex} をコピー`"
              @click="handleCopyHex(hex)"
            >
              <span
                class="w-full aspect-square rounded-md border border-canvas-border flex items-center justify-center"
                :style="{ backgroundColor: hex }"
              >
                <Check v-if="copiedHex === hex" class="w-3.5 h-3.5 text-white stroke-[3]" />
              </span>
              <span class="text-[9px] font-mono text-ink-subtle mt-0.5 uppercase">{{ hex }}</span>
            </button>
          </div>
        </section>

        <!-- 構図 / ライティング / ポーズ / 衣装 -->
        <section
          v-for="section in SECTIONS"
          :key="section.key"
          class="p-3 rounded-xl bg-canvas-card border border-canvas-border space-y-1.5"
        >
          <h3 class="flex items-center gap-1.5 text-[11px] font-semibold text-ink">
            <component :is="section.icon" class="w-3.5 h-3.5" :class="section.color" />
            {{ section.label }}
          </h3>
          <p class="text-[11px] leading-relaxed text-ink-muted">
            {{ analysis[section.key] || '解析データなし' }}
          </p>
        </section>

        <!-- タグ -->
        <section v-if="analysis.tags?.length" class="p-3 rounded-xl bg-canvas-card border border-canvas-border space-y-2">
          <h3 class="flex items-center gap-1.5 text-[11px] font-semibold text-ink">
            <Tag class="w-3.5 h-3.5 text-ok" />
            セマンティックタグ
          </h3>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="tag in analysis.tags"
              :key="tag"
              type="button"
              class="px-2 py-0.5 rounded-full text-[11px] font-medium bg-canvas-raised hover:bg-brand-soft hover:text-brand border border-canvas-border transition-colors"
              :title="`#${tag} で絞り込み`"
              @click="emit('select-tag', tag)"
            >
              #{{ tag }}
            </button>
          </div>
        </section>
      </template>

      <!-- 未解析 -->
      <div v-else class="py-12 text-center space-y-3">
        <Sparkles class="w-7 h-7 text-ink-subtle mx-auto" />
        <p class="text-xs text-ink-muted">この画像のAI解析はまだ完了していません。</p>
        <button
          type="button"
          class="px-3.5 py-1.5 rounded-lg bg-brand text-brand-fg text-xs font-medium hover:bg-brand-hover transition-colors"
          @click="handleReanalyze"
        >
          今すぐAIスキャンを実行
        </button>
      </div>
    </div>

    <!-- 未選択 -->
    <div v-else class="flex-1 flex flex-col items-center justify-center p-6 text-center gap-3">
      <div class="p-3 rounded-full bg-canvas-card text-ink-subtle">
        <Sparkles class="w-6 h-6" />
      </div>
      <p class="text-xs text-ink-muted leading-relaxed">
        キャンバス上の画像を選択すると、<br>
        構図・光・衣装のAI詳細解析が表示されます。
      </p>
    </div>
  </aside>
</template>
