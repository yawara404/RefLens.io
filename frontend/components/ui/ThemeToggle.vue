<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { Sun, Moon, Monitor, Check, X } from 'lucide-vue-next'
import { useTheme, type ThemePreference } from '~/composables/useTheme'

const { preference, resolvedTheme, setPreference } = useTheme()
const isOpen = ref(false)

const options: { value: ThemePreference; label: string; desc: string; icon: any }[] = [
  { value: 'light', label: 'ライトテーマ', desc: '明るく視認性の高い標準表示', icon: Sun },
  { value: 'dark', label: 'ダークテーマ', desc: '暗所での作業やキャンバス閲覧向け', icon: Moon },
  { value: 'auto', label: 'OSの設定に合わせる', desc: 'デバイスの外観モードに自動追従', icon: Monitor },
]

const current = computed(() => options.find(o => o.value === preference.value) || options[0])
const CurrentIcon = computed(() => current.value.icon)

function select(pref: ThemePreference) {
  setPreference(pref)
  isOpen.value = false
}

function onKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape' && isOpen.value) isOpen.value = false
}

onMounted(() => {
  window.addEventListener('keydown', onKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
})
</script>

<template>
  <div class="relative shrink-0">
    <button
      type="button"
      class="flex items-center gap-1.5 p-2 lg:px-2.5 lg:py-1.5 rounded-xl text-xs text-ink hover:text-brand hover:bg-canvas-hover transition-colors border border-canvas-border-strong font-bold"
      :title="`テーマ: ${current.label}（現在 ${resolvedTheme === 'dark' ? 'ダーク' : 'ライト'}）`"
      :aria-label="`テーマ設定を開く（現在 ${current.label}）`"
      aria-haspopup="dialog"
      :aria-expanded="isOpen"
      @click="isOpen = !isOpen"
    >
      <component :is="CurrentIcon" class="w-4 h-4 lg:w-3.5 lg:h-3.5 text-brand" />
      <span class="hidden lg:inline font-bold">{{ current.label }}</span>
    </button>

    <Teleport to="body">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[85] flex items-end sm:items-center justify-center p-2 sm:p-4 scrim animate-fade-in"
        @click.self="isOpen = false"
      >
        <div
          class="w-full max-w-xs rounded-2xl border border-canvas-border bg-canvas-panel shadow-pop overflow-hidden animate-scale-in"
          role="dialog"
          aria-modal="true"
          aria-label="テーマ設定"
        >
          <div class="px-4 py-3 border-b border-canvas-border flex items-center justify-between">
            <h2 class="text-sm font-bold text-ink flex items-center gap-2">
              <component :is="CurrentIcon" class="w-4 h-4 text-brand" />
              <span>外観テーマ設定</span>
            </h2>
            <button
              type="button"
              class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
              aria-label="閉じる"
              @click="isOpen = false"
            >
              <X class="w-4 h-4" />
            </button>
          </div>

          <div class="p-3 space-y-1.5" role="radiogroup" aria-label="テーマの選択">
            <button
              v-for="opt in options"
              :key="opt.value"
              type="button"
              class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-colors border"
              :class="preference === opt.value
                ? 'text-brand font-bold bg-brand-soft border-brand'
                : 'text-ink bg-canvas-bg border-canvas-border-strong hover:bg-canvas-hover font-medium'"
              role="radio"
              :aria-checked="preference === opt.value"
              @click="select(opt.value)"
            >
              <component :is="opt.icon" class="w-4 h-4 shrink-0" :class="preference === opt.value ? 'text-brand' : 'text-ink-muted'" />
              <div class="flex-1 min-w-0">
                <p class="text-xs">{{ opt.label }}</p>
                <p class="text-[10px] text-ink-muted font-normal mt-0.5">{{ opt.desc }}</p>
              </div>
              <Check v-if="preference === opt.value" class="w-4 h-4 text-brand shrink-0" />
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
