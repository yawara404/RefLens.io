import { computed, ref } from 'vue'
import { useToast } from '~/composables/useToast'
import { useBackendUrl } from '~/composables/useBackendUrl'

/** pixiv API のレスポンス型（バックエンドで正規化済み） */
export interface PixivArtwork {
  id: string
  title: string
  caption?: string
  author_name: string
  author_id?: string
  author_account?: string
  author_avatar: string
  image_url: string
  original_url?: string
  category: string
  tags: string[]
  likes: number
  view_likes?: number
  bookmarks: number
  page_count: number
  width?: number
  height?: number
  is_r18?: boolean
  create_date?: string
  source_url: string
}

export interface PixivPage {
  image_url: string
  width: number
  height: number
}

export interface PixivStatus {
  configured: boolean
  /** 「Pixivの画面でログイン」による接続が可能か（公開プレビューでも true） */
  connect_available: boolean
  /** Refresh Token を直接貼る接続が可能か（ローカルのみ true） */
  token_connect_available?: boolean
  connected: boolean
  mode: 'live' | 'demo' | 'auth_required'
  account: {
    id: string
    name: string
    account: string
    avatar_url: string
    expires_at?: string | null
  } | null
  message: string
}

export interface PixivFeedResponse {
  mode: 'live' | 'demo'
  category: string
  page: number
  total: number
  has_next: boolean
  next_cursor?: string | null
  items: PixivArtwork[]
  notice?: string | null
}

/** pixiv クライアントの共通ロジック（/view とモーダルで共有） */
export function usePixiv() {
  const { apiBase } = useBackendUrl()
  const toast = useToast()

  const status = ref<PixivStatus | null>(null)
  const items = ref<PixivArtwork[]>([])
  const isLoading = ref(false)
  const isImporting = ref(false)
  const currentCategory = ref('recommended')
  const currentQuery = ref('')
  const currentPage = ref(1)
  const hasNext = ref(false)
  const notice = ref<string | null>(null)
  const feedError = ref<string | null>(null)
  const pageCursors = new Map<number, string>()
  let feedRequestId = 0

  /** 検索カテゴリのフィルタ（pixiv API の sort / duration に対応） */
  const sort = ref<'date_desc' | 'date_asc' | 'popular_desc'>('date_desc')
  const duration = ref<'' | 'within_last_day' | 'within_last_week' | 'within_last_month'>('')

  // 選択状態（/view の複数選択）
  const selectedIds = ref<string[]>([])

  const isConnected = computed(() => !!status.value?.connected)
  const accountName = computed(() => status.value?.account?.name || '')
  const canConnect = computed(() => !!status.value?.connect_available)
  /** Refresh Token 入力タブを出せるか（公開プレビューでは隠す） */
  const canConnectWithToken = computed(() => !!status.value?.token_connect_available)
  const statusMessage = computed(() => status.value?.message || '')

  function api(path: string) {
    return `${apiBase.value}${path}`
  }

  function proxyImage(url?: string) {
    if (!url || !url.startsWith('https://i.pximg.net/')) return url || ''
    return api(`/pixiv/image?url=${encodeURIComponent(url)}`)
  }

  async function fetchStatus() {
    try {
      status.value = await $fetch<PixivStatus>(api('/pixiv/status'))
    } catch (e: any) {
      status.value = {
        configured: false,
        connect_available: false,
        connected: false,
        mode: 'demo',
        account: null,
        message: 'バックエンドに接続できませんでした',
      }
    }
  }

  async function loadFeed(category?: string, page = 1) {
    if (category && category !== currentCategory.value) pageCursors.clear()
    if (category) currentCategory.value = category
    if (page === 1) pageCursors.clear()
    const requestId = ++feedRequestId
    const requestedCategory = currentCategory.value
    isLoading.value = true
    feedError.value = null

    try {
      const params = new URLSearchParams({
        category: requestedCategory,
        page: String(page),
      })
      if ((requestedCategory === 'following' || requestedCategory === 'bookmarks') && page > 1) {
        const cursor = pageCursors.get(page)
        if (!cursor) throw new Error('次ページの情報がありません。最初から読み込み直してください。')
        params.set('cursor', cursor)
      }
      if (requestedCategory === 'search') {
        if (currentQuery.value) params.set('query', currentQuery.value)
        // ソート / 期間フィルタは検索カテゴリのときだけAPIへ渡す
        if (sort.value) params.set('sort', sort.value)
        if (duration.value) params.set('duration', duration.value)
      }

      const res = await $fetch<PixivFeedResponse>(api(`/pixiv/feed?${params.toString()}`))
      if (requestId !== feedRequestId) return
      items.value = (res.items || []).map(item => res.mode === 'live'
        ? { ...item, image_url: proxyImage(item.image_url), original_url: proxyImage(item.original_url), author_avatar: proxyImage(item.author_avatar) }
        : item)
      hasNext.value = res.has_next
      currentPage.value = res.page
      notice.value = res.notice || null
      if (res.next_cursor) pageCursors.set(res.page + 1, res.next_cursor)
    } catch (e: any) {
      if (requestId !== feedRequestId) return
      items.value = []
      hasNext.value = false
      feedError.value = e?.data?.detail || e?.message || 'バックエンドの接続を確認してください'
      toast.error(
        'pixivの取得に失敗しました',
        feedError.value || undefined,
      )
    } finally {
      if (requestId === feedRequestId) isLoading.value = false
    }
  }

  function setQuery(query: string) {
    currentQuery.value = query.trim()
    currentPage.value = 1
  }

  function nextPage() {
    if (!hasNext.value) return
    loadFeed(undefined, currentPage.value + 1)
  }

  function prevPage() {
    if (currentPage.value <= 1) return
    loadFeed(undefined, currentPage.value - 1)
  }

  // --- 選択 ---
  function isSelected(id: string) {
    return selectedIds.value.includes(id)
  }
  function toggleSelection(id: string) {
    const idx = selectedIds.value.indexOf(id)
    if (idx >= 0) selectedIds.value.splice(idx, 1)
    else selectedIds.value.push(id)
  }
  function clearSelection() {
    selectedIds.value = []
  }

  // --- 取り込み ---
  /**
   * 作品をライブラリ（Manager）へ保存する。
   * pixiv接続中は bulk エンドポイントを使い、未接続（デモ表示）時は
   * 通常のブックマーク追加へフォールバックする。
   */
  async function stockToLibrary(ids: string[]) {
    if (!ids.length) return 0
    isImporting.value = true

    try {
      if (isConnected.value) {
        const res = await $fetch<{ count: number; errors: string[] }>(
          api('/pixiv/stock/bulk'),
          { method: 'POST', body: { illust_ids: ids } }
        )
        if (res.errors?.length) {
          if (res.count) toast.warning('一部の作品は保存できませんでした', res.errors.slice(0, 2).join(' / '))
          else toast.error('ライブラリへ保存できませんでした', res.errors.slice(0, 2).join(' / '))
        } else if (!res.count) {
          toast.error('ライブラリへ保存できませんでした', 'Pixivから画像を取得できませんでした')
        }
        return res.count || 0
      }

      // デモモード: URL 経由のブックマークとして保存
      const results = await Promise.allSettled(
        ids.map(id =>
          $fetch(api('/bookmarks/add'), {
            method: 'POST',
            body: { url: `https://www.pixiv.net/artworks/${id}` },
          })
        )
      )
      const ok = results.filter(r => r.status === 'fulfilled').length
      const failed = results.length - ok
      if (failed > 0) {
        toast.warning(`${failed} 件の保存に失敗しました`)
      }
      return ok
    } catch (e: any) {
      toast.error('ライブラリへの保存に失敗しました', e?.data?.detail || e?.message)
      return 0
    } finally {
      isImporting.value = false
    }
  }

  async function stockToCanvas(ids: string[], boardId: string, posX?: number, posY?: number) {
    if (!ids.length || !boardId) return false
    isImporting.value = true
    try {
      // 複数作品ぶんの取り込みは bulk エンドポイントでまとめて行う
      const res = await $fetch<{ count: number; errors: string[] }>(
        api('/pixiv/stock/bulk'),
        {
          method: 'POST',
          body: {
            illust_ids: ids,
            board_id: boardId,
            pos_x: posX,
            pos_y: posY,
          },
        }
      )
      if (res.errors?.length) {
        toast.warning('一部の作品は取得できませんでした', res.errors.slice(0, 2).join(' / '))
      }
      return (res.count || 0) > 0
    } catch (e: any) {
      toast.error(
        'キャンバスへの配置に失敗しました',
        e?.data?.detail || e?.message,
      )
      return false
    } finally {
      isImporting.value = false
    }
  }

  // --- 接続 ---
  function connect() {
    if (canConnect.value) window.dispatchEvent(new Event('reflens:pixiv-connect'))
  }

  async function disconnect() {
    try {
      await $fetch(api('/pixiv/disconnect'), { method: 'POST' })
      await fetchStatus()
      selectedIds.value = []
      await loadFeed('recommended', 1)
      toast.success('pixiv接続を解除しました')
    } catch (e: any) {
      toast.error('接続解除に失敗しました', e?.message)
    }
  }

  async function init() {
    await fetchStatus()
    await loadFeed('recommended', 1)
  }

  return {
    status,
    items,
    isLoading,
    isImporting,
    currentCategory,
    currentQuery,
    currentPage,
    hasNext,
    notice,
    feedError,
    sort,
    duration,
    selectedIds,
    isConnected,
    accountName,
    canConnect,
    canConnectWithToken,
    statusMessage,
    proxyImage,
    init,
    fetchStatus,
    loadFeed,
    setQuery,
    nextPage,
    prevPage,
    isSelected,
    toggleSelection,
    clearSelection,
    stockToLibrary,
    stockToCanvas,
    connect,
    disconnect,
  }
}
