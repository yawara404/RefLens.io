import { ref } from 'vue'
import { useBackendUrl } from '~/composables/useBackendUrl'
import { useToast } from '~/composables/useToast'
import { useBoardStore } from '~/stores/boardStore'

export interface VisualSearchMatch {
  id: string
  title: string
  file_path: string
  thumbnail_url: string
  source_type: string
  folder_name: string
  author_name?: string
  similarity: number
  reasons: string[]
  tags: string[]
  palette: string[]
}

export interface VisualSearchResult {
  crop_thumbnail?: string
  detected: {
    summary: string
    tags: string[]
    palette: string[]
    composition?: string
    lighting?: string
    pose?: string
    costume?: string
  }
  total_matches: number
  matches: VisualSearchMatch[]
}

const isCircleSearchActive = ref(false)
const isSearching = ref(false)
const isDrawerOpen = ref(false)
const searchResult = ref<VisualSearchResult | null>(null)
const lastSearchTime = ref<number>(0)

export function useVisualSearch() {
  const { apiBase } = useBackendUrl()
  const toast = useToast()
  const boardStore = useBoardStore()

  function startCircleSearch() {
    isCircleSearchActive.value = true
    isDrawerOpen.value = false
  }

  function cancelCircleSearch() {
    isCircleSearchActive.value = false
  }

  async function searchCrop(imageBase64: string) {
    isCircleSearchActive.value = false
    isSearching.value = true
    isDrawerOpen.value = true

    try {
      const res = await $fetch<VisualSearchResult>(`${apiBase.value}/media/visual-search`, {
        method: 'POST',
        body: {
          image_base64: imageBase64,
          limit: 15,
        },
      })

      searchResult.value = res
      lastSearchTime.value = Date.now()
      if (res.matches.length === 0) {
        toast.info('視覚特徴を解析しました', '類似度の高い資料は見つかりませんでした')
      } else {
        toast.success('Galaxy AI 視覚検索完了', `${res.matches.length} 件の類似資料が見つかりました`)
      }
    } catch (e: any) {
      console.error('Visual search failed:', e)
      toast.error('視覚検索に失敗しました', e?.message || '通信エラー')
    } finally {
      isSearching.value = false
    }
  }

  async function searchMediaItem(mediaItemId: string) {
    isCircleSearchActive.value = false
    isSearching.value = true
    isDrawerOpen.value = true

    try {
      const res = await $fetch<VisualSearchResult>(`${apiBase.value}/media/visual-search`, {
        method: 'POST',
        body: {
          media_item_id: mediaItemId,
          limit: 15,
        },
      })

      searchResult.value = res
      lastSearchTime.value = Date.now()
      toast.success('Galaxy AI 視覚検索完了', `${res.matches.length} 件の類似資料が見つかりました`)
    } catch (e: any) {
      console.error('Visual search failed:', e)
      toast.error('視覚検索に失敗しました', e?.message || '通信エラー')
    } finally {
      isSearching.value = false
    }
  }

  async function placeMatchOnCanvas(match: VisualSearchMatch) {
    if (!boardStore.currentBoard) {
      toast.warning('キャンバスが開かれていません')
      return
    }

    try {
      await boardStore.addBookmarkToBoard(match.id)
      toast.success('キャンバスに配置しました', match.title)
    } catch (e: any) {
      toast.error('配置に失敗しました', e?.message)
    }
  }

  function closeDrawer() {
    isDrawerOpen.value = false
  }

  function openDrawer() {
    if (searchResult.value) {
      isDrawerOpen.value = true
    }
  }

  return {
    isCircleSearchActive,
    isSearching,
    isDrawerOpen,
    searchResult,
    lastSearchTime,
    startCircleSearch,
    cancelCircleSearch,
    searchCrop,
    searchMediaItem,
    placeMatchOnCanvas,
    closeDrawer,
    openDrawer,
  }
}
