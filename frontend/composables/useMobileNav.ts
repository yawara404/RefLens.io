import { useState } from '#imports'

/**
 * モバイル時のハンバーガーメニュー（ナビゲーション＋サイドメニュー統合ドロワー）の開閉状態
 */
export function useMobileNav() {
  const isOpen = useState<boolean>('reflens-mobile-nav-open', () => false)

  function open() {
    isOpen.value = true
  }

  function close() {
    isOpen.value = false
  }

  function toggle() {
    isOpen.value = !isOpen.value
  }

  return {
    isOpen,
    open,
    close,
    toggle,
  }
}

