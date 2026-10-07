import { ref } from 'vue'

export type ToastKind = 'info' | 'success' | 'warning' | 'error'

export interface Toast {
  id: number
  kind: ToastKind
  message: string
  detail?: string
}

const toasts = ref<Toast[]>([])
let nextId = 1

function push(kind: ToastKind, message: string, detail?: string, timeout = 3800) {
  const id = nextId++
  toasts.value.push({ id, kind, message, detail })
  if (timeout > 0) {
    setTimeout(() => dismiss(id), timeout)
  }
  return id
}

function dismiss(id: number) {
  toasts.value = toasts.value.filter(t => t.id !== id)
}

export function useToast() {
  return {
    toasts,
    dismiss,
    info: (message: string, detail?: string) => push('info', message, detail),
    success: (message: string, detail?: string) => push('success', message, detail),
    warning: (message: string, detail?: string) => push('warning', message, detail, 5200),
    error: (message: string, detail?: string) => push('error', message, detail, 6000),
  }
}