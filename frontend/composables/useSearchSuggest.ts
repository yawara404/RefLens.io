import { ref } from 'vue'
import { useBackendUrl } from '~/composables/useBackendUrl'

export interface SearchSuggestResult {
  query: string
  source: 'ollama' | 'heuristic' | 'empty'
  suggestions: string[]
  library_tags: { tag: string; count: number }[]
}

const globalCache = new Map<string, SearchSuggestResult>()

export function useSearchSuggest() {
  const { apiBase } = useBackendUrl()
  const isPredicting = ref(false)
  const suggestions = ref<string[]>([])
  const libraryTags = ref<{ tag: string; count: number }[]>([])
  const lastQuery = ref('')
  const predictionSource = ref<'ollama' | 'heuristic' | 'empty'>('empty')

  let debounceTimer: ReturnType<typeof setTimeout> | null = null

  async function fetchSuggestions(query: string) {
    const q = query.trim()
    if (!q) {
      suggestions.value = []
      libraryTags.value = []
      lastQuery.value = ''
      predictionSource.value = 'empty'
      isPredicting.value = false
      return
    }

    lastQuery.value = q
    const cached = globalCache.get(q.toLowerCase())
    if (cached) {
      suggestions.value = cached.suggestions
      libraryTags.value = cached.library_tags
      predictionSource.value = cached.source
      return
    }

    isPredicting.value = true
    try {
      const res = await $fetch<SearchSuggestResult>(`${apiBase.value}/bookmarks/search-suggest`, {
        params: { q },
      })
      if (res && lastQuery.value === q) {
        suggestions.value = res.suggestions || []
        libraryTags.value = res.library_tags || []
        predictionSource.value = res.source || 'heuristic'
        globalCache.set(q.toLowerCase(), res)
      }
    } catch (e) {
      // ネットワークやタイムアウト時は静かに無視
      console.debug('Search suggestions fetch error:', e)
    } finally {
      if (lastQuery.value === q) {
        isPredicting.value = false
      }
    }
  }

  function queueQuery(query: string, delay = 200) {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }

    const q = query.trim()
    if (!q) {
      suggestions.value = []
      libraryTags.value = []
      lastQuery.value = ''
      isPredicting.value = false
      return
    }

    // キャッシュにあれば即時適用
    const cached = globalCache.get(q.toLowerCase())
    if (cached) {
      suggestions.value = cached.suggestions
      libraryTags.value = cached.library_tags
      predictionSource.value = cached.source
      return
    }

    debounceTimer = setTimeout(() => {
      fetchSuggestions(query)
    }, delay)
  }

  function clearSuggestions() {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
      debounceTimer = null
    }
    suggestions.value = []
    libraryTags.value = []
    lastQuery.value = ''
    isPredicting.value = false
    predictionSource.value = 'empty'
  }

  return {
    isPredicting,
    suggestions,
    libraryTags,
    predictionSource,
    fetchSuggestions,
    queueQuery,
    clearSuggestions,
  }
}
