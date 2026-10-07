<script setup lang="ts">
import { ref } from 'vue'
import { Pipette, Check, Copy } from 'lucide-vue-next'
import { useImageProcessor } from '~/composables/useImageProcessor'
import { useToast } from '~/composables/useToast'

const props = defineProps<{
  palette: string[]
  title?: string
}>()

const { pickColor, copyToClipboard } = useImageProcessor()
const toast = useToast()
const copiedHex = ref<string | null>(null)

async function handleCopy(hex: string) {
  const success = await copyToClipboard(hex)
  if (success) {
    copiedHex.value = hex
    setTimeout(() => { copiedHex.value = null }, 1400)
  } else {
    toast.error('クリップボードにコピーできませんでした')
  }
}

async function handlePickColor() {
  const picked = await pickColor()
  if (picked) {
    await handleCopy(picked)
    toast.success('画面の色をコピーしました', picked)
  }
}
</script>

<template>
  <div class="floating-bar px-3 py-1.5 rounded-full flex items-center gap-2 select-none">
    <span class="text-[11px] font-mono text-ink-subtle uppercase tracking-wider flex items-center gap-1.5 mr-1">
      <span class="w-1.5 h-1.5 rounded-full bg-brand" />
      Palette
    </span>

    <!-- カラーチップ -->
    <div class="flex items-center gap-1.5">
      <button
        v-for="(hex, idx) in palette"
        :key="`${hex}-${idx}`"
        type="button"
        class="group relative w-6 h-6 rounded-full border border-canvas-border-strong transition-transform hover:scale-125 focus:outline-none focus-visible:scale-125 z-0 hover:z-10"
        :style="{ backgroundColor: hex }"
        :title="`クリックでコピー: ${hex}`"
        :aria-label="`カラーパレット ${hex} をコピー`"
        @click.stop="handleCopy(hex)"
      >
        <span
          v-if="copiedHex === hex"
          class="absolute inset-0 flex items-center justify-center bg-black/55 rounded-full"
        >
          <Check class="w-3.5 h-3.5 text-white stroke-[3]" />
        </span>
        <span
          v-else
          class="absolute inset-0 opacity-0 group-hover:opacity-100 flex items-center justify-center bg-black/35 rounded-full transition-opacity"
        >
          <Copy class="w-2.5 h-2.5 text-white" />
        </span>
      </button>
    </div>

    <div class="h-3.5 w-px bg-canvas-border mx-0.5" />

    <!-- カラーピッカー -->
    <button
      type="button"
      class="p-1 rounded-full text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors focus:outline-none"
      title="画面上から色を吸い取る"
      aria-label="カラーピッカー"
      @click.stop="handlePickColor"
    >
      <Pipette class="w-3.5 h-3.5" />
    </button>
  </div>
</template>