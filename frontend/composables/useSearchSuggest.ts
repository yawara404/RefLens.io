import { ref } from 'vue'
import { useBackendUrl } from '~/composables/useBackendUrl'

export interface OllamaAIMatch {
  id: string
  title: string
  score: number
  reasons: string[]
  file_path: string
}

export type GalaxyAIMatch = OllamaAIMatch

export interface OllamaAIResult {
  intent: string | null
  matched_ids: string[]
  total: number
  matches: OllamaAIMatch[]
}

export type GalaxyAIResult = OllamaAIResult

export interface SearchSuggestResult {
  query: string
  source: 'ollama' | 'heuristic' | 'empty'
  suggestions: string[]
  library_tags: { tag: string; count: number }[]
  ollama_ai?: OllamaAIResult | null
  galaxy_ai?: OllamaAIResult | null
}

const globalCache = new Map<string, SearchSuggestResult>()

// フロントエンド即応用の Ollama AI 概念辞書（0ms レスポンス）
const FRONTEND_VISUAL_CONCEPTS: Record<string, { label: string; keys: string[] }> = {
  女の子: {
    label: '女の子 (女性キャラクター / 少女)',
    keys: ['女の子', '少女', '女性', '女子', '美少女', '1girl', '2girls', 'girl', 'woman', 'anime girl', 'kawaii', '娘', 'ヒロイン'],
  },
  少女: {
    label: '少女 (女の子 / 美少女)',
    keys: ['少女', '女の子', '美少女', '1girl', 'girl', 'female'],
  },
  女性: {
    label: '女性 (大人女性 / レディ)',
    keys: ['女性', 'woman', 'female', 'lady', '女の子', '1girl'],
  },
  男の子: {
    label: '男の子 (男性キャラクター / 少年)',
    keys: ['男の子', '少年', '男性', '男子', '1boy', 'boy', 'man', 'male'],
  },
  猫: {
    label: '猫 (ねこ / キャット)',
    keys: ['猫', 'ねこ', 'ネコ', 'cat', 'neko', 'にゃんこ', '猫耳'],
  },
  ねこ: {
    label: 'ねこ (猫 / キャット)',
    keys: ['ねこ', '猫', 'ネコ', 'cat', 'neko', 'にゃんこ'],
  },
  水着: {
    label: '水着 (ビキニ / スイムウェア)',
    keys: ['水着', 'ビキニ', 'swimsuit', 'bikini', 'サマー', '夏'],
  },
  初音ミク: {
    label: '初音ミク (ボーカロイド / Miku)',
    keys: ['初音ミク', 'ミク', 'miku', 'hatsune miku', 'vocaloid', 'ボーカロイド', 'ツインテール'],
  },
  ミク: {
    label: '初音ミク (ボーカロイド)',
    keys: ['ミク', '初音ミク', 'miku', 'hatsune miku', 'vocaloid'],
  },
  漫画: {
    label: '漫画 (マンガ / コミック)',
    keys: ['漫画', 'マンガ', 'コミック', 'comic', 'manga', 'コマ割り', '吹き出し'],
  },
  マンガ: {
    label: 'マンガ (漫画 / コミック)',
    keys: ['マンガ', '漫画', 'コミック', 'comic', 'manga'],
  },
  設定画: {
    label: '設定画 (キャラクター設定 / 三面図)',
    keys: ['設定画', '三面図', '設定資料', 'character sheet', '巨大娘'],
  },
  サイバーパンク: {
    label: 'サイバーパンク (近未来 / SF / ネオン)',
    keys: ['サイバーパンク', 'cyberpunk', 'sci-fi', 'ネオン', '近未来', 'メカ'],
  },
  夜景: {
    label: '夜景 (ナイトシーン / 星空)',
    keys: ['夜景', 'night', 'night_view', '星空', '月夜', '夜'],
  },
  風景: {
    label: '風景 (背景 / 自然 / 景観)',
    keys: ['風景', '背景', 'scenery', 'landscape', '自然', '空', '街並み', 'さんぽ'],
  },
  青空: {
    label: '青空 (空 / 雲 / スカイ)',
    keys: ['青空', '空', 'sky', 'clouds', '雲'],
  },
}

export function useSearchSuggest() {
  const { apiBase } = useBackendUrl()
  const isPredicting = ref(false)
  const suggestions = ref<string[]>([])
  const libraryTags = ref<{ tag: string; count: number }[]>([])
  const ollamaAIMatches = ref<OllamaAIMatch[]>([])
  const ollamaAIMatchedIds = ref<string[]>([])
  const ollamaAIIntent = ref<string | null>(null)
  const lastQuery = ref('')
  const predictionSource = ref<'ollama' | 'heuristic' | 'empty'>('empty')

  let debounceTimer: ReturnType<typeof setTimeout> | null = null

  function applyLocalVisualConcepts(query: string) {
    const q = query.trim().toLowerCase()
    if (!q) {
      ollamaAIIntent.value = null
      return
    }
    for (const [concept, defn] of Object.entries(FRONTEND_VISUAL_CONCEPTS)) {
      if (defn.keys.some(k => k.toLowerCase() === q || q.includes(k.toLowerCase()) || k.toLowerCase().includes(q))) {
        ollamaAIIntent.value = defn.label
        // ローカル予測キーワードの補強
        for (const k of defn.keys) {
          if (!suggestions.value.includes(k) && k !== q) {
            suggestions.value.push(k)
          }
        }
        break
      }
    }
  }

  async function fetchSuggestions(query: string) {
    const q = query.trim()
    if (!q) {
      suggestions.value = []
      libraryTags.value = []
      ollamaAIMatches.value = []
      ollamaAIMatchedIds.value = []
      ollamaAIIntent.value = null
      lastQuery.value = ''
      predictionSource.value = 'empty'
      isPredicting.value = false
      return
    }

    lastQuery.value = q
    applyLocalVisualConcepts(q)

    const cached = globalCache.get(q.toLowerCase())
    if (cached) {
      suggestions.value = cached.suggestions
      libraryTags.value = cached.library_tags
      predictionSource.value = cached.source
      const aiData = cached.ollama_ai || cached.galaxy_ai
      if (aiData) {
        ollamaAIMatches.value = aiData.matches || []
        ollamaAIMatchedIds.value = aiData.matched_ids || []
        if (aiData.intent) {
          ollamaAIIntent.value = aiData.intent
        }
      }
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
        const aiData = res.ollama_ai || res.galaxy_ai
        if (aiData) {
          ollamaAIMatches.value = aiData.matches || []
          ollamaAIMatchedIds.value = aiData.matched_ids || []
          if (aiData.intent) {
            ollamaAIIntent.value = aiData.intent
          }
        }
        // フロントエンド概念も追加適用
        applyLocalVisualConcepts(q)
        globalCache.set(q.toLowerCase(), res)
      }
    } catch (e) {
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
      ollamaAIMatches.value = []
      ollamaAIMatchedIds.value = []
      ollamaAIIntent.value = null
      lastQuery.value = ''
      isPredicting.value = false
      return
    }

    // 即座にローカル概念を適用して 0ms で UI 反応
    applyLocalVisualConcepts(q)

    // キャッシュにあれば即時適用
    const cached = globalCache.get(q.toLowerCase())
    if (cached) {
      suggestions.value = cached.suggestions
      libraryTags.value = cached.library_tags
      predictionSource.value = cached.source
      const aiData = cached.ollama_ai || cached.galaxy_ai
      if (aiData) {
        ollamaAIMatches.value = aiData.matches || []
        ollamaAIMatchedIds.value = aiData.matched_ids || []
        if (aiData.intent) {
          ollamaAIIntent.value = aiData.intent
        }
      }
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
    ollamaAIMatches.value = []
    ollamaAIMatchedIds.value = []
    ollamaAIIntent.value = null
    lastQuery.value = ''
    isPredicting.value = false
    predictionSource.value = 'empty'
  }

  return {
    isPredicting,
    suggestions,
    libraryTags,
    ollamaAIMatches,
    ollamaAIMatchedIds,
    ollamaAIIntent,
    // 互換性エイリアス
    galaxyAIMatches: ollamaAIMatches,
    galaxyAIMatchedIds: ollamaAIMatchedIds,
    galaxyAIIntent: ollamaAIIntent,
    predictionSource,
    fetchSuggestions,
    queueQuery,
    clearSuggestions,
  }
}
