import { nextTick, onMounted, onUnmounted, ref, watch, type Ref } from 'vue'

interface DialogOptions {
  /** Esc キーで閉じる（既定: true） */
  closeOnEscape?: boolean
  /** 背景のスクロールを止める（既定: true） */
  lockScroll?: boolean
}

/** 開いているダイアログのスタック（最後に開いたものだけが Esc に反応する） */
const openDialogs: number[] = []
let dialogSeq = 0

let scrollLockCount = 0
let previousBodyOverflow = ''
let previousBodyPaddingRight = ''

function lockPageScroll() {
  if (typeof document === 'undefined') return
  if (scrollLockCount === 0) {
    previousBodyOverflow = document.body.style.overflow
    previousBodyPaddingRight = document.body.style.paddingRight
    // スクロールバーが消える分のガタつき（横方向のずれ）を埋める
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth
    document.body.style.overflow = 'hidden'
    if (scrollbarWidth > 0) document.body.style.paddingRight = `${scrollbarWidth}px`
  }
  scrollLockCount += 1
}

function unlockPageScroll() {
  if (typeof document === 'undefined' || scrollLockCount === 0) return
  scrollLockCount -= 1
  if (scrollLockCount === 0) {
    document.body.style.overflow = previousBodyOverflow
    document.body.style.paddingRight = previousBodyPaddingRight
  }
}

/**
 * ダイアログ（モーダル）の共通挙動。
 *
 * - Esc で閉じる（複数開いているときは最前面だけ）
 * - 初期フォーカスと Tab / Shift+Tab の循環
 * - 背景スクロールのロック（複数モーダルでも二重解除しないよう参照カウント）
 * - 閉じたあと、開く前にフォーカスしていた要素へ戻す
 *
 * 背景クリックやボタンでの開閉は各コンポーネント側の実装をそのまま使う。
 */
export function useDialogA11y(
  isOpen: Ref<boolean>,
  onClose: () => void,
  options: DialogOptions = {},
) {
  const { closeOnEscape = true, lockScroll = true } = options
  const id = ++dialogSeq
  const dialogRef = ref<HTMLElement | null>(null)
  let active = false
  let lastFocused: HTMLElement | null = null

  function isTopDialog() {
    return active && openDialogs[openDialogs.length - 1] === id
  }

  function focusableElements() {
    return Array.from(dialogRef.value?.querySelectorAll<HTMLElement>(
      'a[href], button, input, select, textarea, [tabindex], [contenteditable="true"]',
    ) || []).filter(el => el.tabIndex >= 0 && !el.matches(':disabled, [inert], [aria-disabled="true"]')
      && !el.closest('[inert]') && el.getClientRects().length > 0
      && getComputedStyle(el).visibility !== 'hidden')
  }

  function focusInside() {
    const root = dialogRef.value
    if (!root || root.contains(document.activeElement)) return
    root.setAttribute('tabindex', '-1')
    const target = root.querySelector<HTMLElement>('[autofocus]') || focusableElements()[0] || root
    target.focus({ preventScroll: true })
  }

  function onFocusIn(event: FocusEvent) {
    if (isTopDialog() && dialogRef.value && !dialogRef.value.contains(event.target as Node)) focusInside()
  }

  function onKeyDown(event: KeyboardEvent) {
    if (!isTopDialog() || event.defaultPrevented || event.isComposing) return
    if (event.key === 'Escape' && closeOnEscape) {
      event.preventDefault()
      event.stopImmediatePropagation()
      onClose()
    } else if (event.key === 'Tab') {
      const elements = focusableElements()
      const first = elements[0]
      const last = elements[elements.length - 1]
      if (!first) {
        event.preventDefault()
        dialogRef.value?.focus({ preventScroll: true })
      } else if (event.shiftKey && (document.activeElement === first || document.activeElement === dialogRef.value)) {
        event.preventDefault()
        last.focus({ preventScroll: true })
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus({ preventScroll: true })
      }
    }
  }

  function activate() {
    if (active || typeof window === 'undefined') return
    active = true
    lastFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null
    openDialogs.push(id)
    if (lockScroll) lockPageScroll()
    document.addEventListener('keydown', onKeyDown)
    document.addEventListener('focusin', onFocusIn)
    void nextTick(() => { if (isTopDialog()) focusInside() })
  }

  function deactivate() {
    if (!active) return
    const wasTop = isTopDialog()
    active = false
    const index = openDialogs.lastIndexOf(id)
    if (index >= 0) openDialogs.splice(index, 1)
    if (lockScroll) unlockPageScroll()
    document.removeEventListener('keydown', onKeyDown)
    document.removeEventListener('focusin', onFocusIn)
    if (wasTop && lastFocused?.isConnected) lastFocused.focus({ preventScroll: true })
    lastFocused = null
  }

  watch(isOpen, (open) => (open ? activate() : deactivate()), { immediate: true })
  onMounted(() => { if (isOpen.value) activate() })
  onUnmounted(deactivate)

  return { activate, deactivate, dialogRef }
}
