<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { Sun, Moon, Monitor, Check } from 'lucide-vue-next'
import { useTheme, type ThemePreference } from '~/composables/useTheme'

const { preference, resolvedTheme, setPreference } = useTheme()
const isOpen = ref(false)
const rootRef = ref<HTMLElement | null>(null)

const options: { value: ThemePreference; label: string; icon: any }[] = [
  { value: 'light', label: 'ライト', icon: Sun },
  { value: 'dark', label: 'ダーク', icon: Moon },
  { value: 'auto', label: 'OS に合わせる', icon: Monitor },
]

const current = computed(() => options.find(o => o.value === preference.value) || options[2])
const CurrentIcon = computed(() => current.value.icon)

function select(pref: ThemePreference) {
  setPreference(pref)
  isOpen.value = false
}

function onDocumentClick(e: MouseEvent) {
  if (isOpen.value && rootRef.value && !rootRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

function onKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape' && isOpen.value) isOpen.value = false
}

onMounted(() => {
  document.addEventListener('mousedown', onDocumentClick)
  window.addEventListener('keydown', onKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', onDocumentClick)
  window.removeEventListener('keydown', onKeyDown)
})
</script>

<template>
  <div ref="rootRef" class="relative">
    <button
      type="button"
      class="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors border border-canvas-border"
      :title="`テーマ: ${current.label}（現在 ${resolvedTheme === 'dark' ? 'ダーク' : 'ライト'}）`"
      :aria-label="`テーマ設定（現在 ${current.label}）`"
      aria-haspopup="menu"
      :aria-expanded="isOpen"
      @click="isOpen = !isOpen"
    >
      <component :is="CurrentIcon" class="w-3.5 h-3.5" />
      <span class="hidden lg:inline">{{ current.label }}</span>
    </button>

    <div
      v-if="isOpen"
      class="absolute right-0 top-full mt-1.5 z-50 min-w-[160px] p-1 rounded-xl border border-canvas-border bg-canvas-raised shadow-pop animate-scale-in"
      role="menu"
    >
      <button
        v-for="opt in options"
        :key="opt.value"
        type="button"
        class="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs transition-colors"
        :class="preference === opt.value
          ? 'text-brand font-semibold bg-brand-soft'
          : 'text-ink-muted hover:text-ink hover:bg-canvas-hover'"
        role="menuitemradio"
        :aria-checked="preference === opt.value"
        @click="select(opt.value)"
      >
        <component :is="opt.icon" class="w-3.5 h-3.5" />
        <span class="flex-1 text-left">{{ opt.label }}</span>
        <Check v-if="preference === opt.value" class="w-3.5 h-3.5" />
      </button>
    </div>
  </div>
</template>
