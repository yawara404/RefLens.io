<script setup lang="ts">
import { computed } from 'vue'
import { Check, Info, AlertTriangle, XCircle, X } from 'lucide-vue-next'
import { useToast, type ToastKind } from '~/composables/useToast'

const { toasts, dismiss } = useToast()

const ICONS: Record<ToastKind, any> = {
  info: Info,
  success: Check,
  warning: AlertTriangle,
  error: XCircle,
}

const CLASSES: Record<ToastKind, string> = {
  info: 'border-canvas-border bg-canvas-raised text-ink',
  success: 'border-ok/40 bg-ok-soft text-ok',
  warning: 'border-warn/40 bg-warn-soft text-warn',
  error: 'border-danger/40 bg-danger-soft text-danger',
}

const hasToasts = computed(() => toasts.value.length > 0)
</script>

<template>
  <div
    class="fixed bottom-4 left-1/2 -translate-x-1/2 z-[70] flex flex-col items-center gap-2 pointer-events-none w-full max-w-md px-4"
    role="status"
    aria-live="polite"
  >
    <TransitionGroup
      v-if="hasToasts"
      name="toast"
      tag="div"
      class="flex flex-col items-center gap-2 w-full"
    >
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="pointer-events-auto w-full flex items-start gap-2.5 rounded-xl border px-3.5 py-2.5 shadow-pop"
        :class="CLASSES[toast.kind]"
      >
        <component :is="ICONS[toast.kind]" class="w-4 h-4 shrink-0 mt-px" />
        <div class="flex-1 min-w-0">
          <p class="text-xs font-semibold leading-snug break-words">{{ toast.message }}</p>
          <p
            v-if="toast.detail"
            class="text-[11px] mt-0.5 opacity-80 leading-relaxed break-words"
          >
            {{ toast.detail }}
          </p>
        </div>
        <button
          class="shrink-0 p-0.5 rounded opacity-60 hover:opacity-100 transition-opacity"
          :aria-label="'閉じる'"
          @click="dismiss(toast.id)"
        >
          <X class="w-3.5 h-3.5" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
.toast-move {
  transition: transform 0.18s ease;
}
</style>