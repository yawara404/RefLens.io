import { ref } from 'vue'

export type ToastKind = 'info' | 'success' | 'warning' | 'error'

export interface Toast {
  id: number
  kind: ToastKind
  message: string
  detail?: string
}

/** 画面に同時に出す最大件数（積み上がりすぎて操作を邪魔しないように） */
const MAX_VISIBLE = 3

const toasts = ref<Toast[]>([])
const timers = new Map<number, ReturnType<typeof setTimeout>>()
let nextId = 1

function clearTimer(id: number) {
  const timer = timers.get(id)
  if (timer) clearTimeout(timer)
  timers.delete(id)
}

function arm(id: number, timeout: number) {
  if (timeout <= 0) return
  timers.set(
    id,
    setTimeout(() => {
      timers.delete(id)
      dismiss(id)
    }, timeout),
  )
}

function push(kind: ToastKind, message: string, detail?: string, timeout = 3800) {
  const id = nextId++
  toasts.value.push({ id, kind, message, detail })

  // 古いものから間引く（エラーを読んでいる最中に消えないよう、消すのは最古のみ）
  while (toasts.value.length > MAX_VISIBLE) {
    const oldest = toasts.value[0]
    if (!oldest) break
    dismiss(oldest.id)
  }

  arm(id, timeout)
  return id
}

function dismiss(id: number) {
  clearTimer(id)
  toasts.value = toasts.value.filter(t => t.id !== id)
}

/** カーソルが乗っている間は自動で消さない（読み切る前に消えるストレスを無くす） */
function pause(id: number) {
  clearTimer(id)
}

/** カーソルが外れたら、少し猶予を持たせてから消す */
function resume(id: number) {
  if (timers.has(id)) return
  if (!toasts.value.some(t => t.id === id)) return
  arm(id, 2600)
}

export function useToast() {
  return {
    toasts,
    dismiss,
    pause,
    resume,
    info: (message: string, detail?: string) => push('info', message, detail),
    success: (message: string, detail?: string) => push('success', message, detail),
    warning: (message: string, detail?: string) => push('warning', message, detail, 5200),
    error: (message: string, detail?: string) => push('error', message, detail, 6000),
  }
}
