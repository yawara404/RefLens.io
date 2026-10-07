import { useBoardStore } from '~/stores/boardStore'

/**
 * ログイン / ログアウトでユーザーが変わったときに、ボードとライブラリを読み直す。
 *
 * バックエンドはユーザー ID で絞り込むため、切り替え直後に古いデータが残ると
 * 「保存したはずが見つからない」状態になる。authStore はイベントを投げるだけで、
 * 実際の再取得はここに集約する（ストア同士を直接依存させないため）。
 */
export default defineNuxtPlugin({
  name: 'board-refresh',
  setup() {
    const boardStore = useBoardStore()

    async function reload() {
      await Promise.all([
        boardStore.fetchBookmarks(),
        boardStore.fetchFolders(),
      ])
      await boardStore.loadFirstBoard()
    }

    window.addEventListener('reflens:auth-changed', reload)
  },
})