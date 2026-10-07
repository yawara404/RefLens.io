import { computed, reactive, toRef } from 'vue'

export type ThemePreference = 'light' | 'dark' | 'auto'
export type ResolvedTheme = 'light' | 'dark'

const STORAGE_KEY = 'reflens-theme'
const COOKIE_KEY = 'reflens-theme'

/**
 * 初回描画の一瞬（CSS 反映前）にもテーマを適用するためのインラインスクリプト。
 * app.vue の useHead() から埋め込む。
 */
export const themeInitScript = `(function(){try{
var p=null;try{p=localStorage.getItem('${STORAGE_KEY}')}catch(_){}
if(p!=='light'&&p!=='dark'&&p!=='auto'){
  var m=document.cookie.match(/(?:^|; )${COOKIE_KEY}=([^;]+)/);
  p=m?decodeURIComponent(m[1]):'auto';
}
if(p!=='light'&&p!=='dark'&&p!=='auto')p='auto';
var d=p==='dark'||(p==='auto'&&window.matchMedia('(prefers-color-scheme: dark)').matches);
var e=document.documentElement;
e.classList.toggle('dark',d);
e.style.colorScheme=d?'dark':'light';
}catch(_){}})();`

interface ThemeState {
  preference: ThemePreference
  systemPrefersDark: boolean
  initialized: boolean
}

const state = reactive<ThemeState>({
  preference: 'auto',
  systemPrefersDark: false,
  initialized: false,
})

function readStoredPreference(): ThemePreference {
  if (typeof window === 'undefined') return 'auto'

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark' || stored === 'auto') return stored
  } catch {
    /* localStorage 無効時（プライベートモード等）は cookie へ */
  }

  const match = document.cookie.match(new RegExp(`(?:^|; )${COOKIE_KEY}=([^;]+)`))
  const fromCookie = match ? decodeURIComponent(match[1]) : null
  return fromCookie === 'light' || fromCookie === 'dark' || fromCookie === 'auto'
    ? (fromCookie as ThemePreference)
    : 'auto'
}

function persist(pref: ThemePreference) {
  if (typeof window === 'undefined') return

  try {
    window.localStorage.setItem(STORAGE_KEY, pref)
  } catch {
    /* ignore */
  }
  // タブ間共有と、localStorage 無効環境向けのフォールバック
  document.cookie = `${COOKIE_KEY}=${pref}; path=/; max-age=31536000; samesite=lax`
}

function applyToDocument(resolved: ResolvedTheme) {
  if (typeof document === 'undefined') return

  const root = document.documentElement
  root.classList.toggle('dark', resolved === 'dark')
  root.style.colorScheme = resolved
}

function resolve(pref: ThemePreference, systemDark: boolean): ResolvedTheme {
  if (pref === 'auto') return systemDark ? 'dark' : 'light'
  return pref
}

let listenersBound = false

export function useTheme() {
  const resolvedTheme = computed<ResolvedTheme>(() =>
    resolve(state.preference, state.systemPrefersDark)
  )
  const isDark = computed(() => resolvedTheme.value === 'dark')

  function setPreference(pref: ThemePreference) {
    state.preference = pref
    persist(pref)
    applyToDocument(resolvedTheme.value)
  }

  function toggle() {
    setPreference(isDark.value ? 'light' : 'dark')
  }

  /**
   * クライアント側でのみ1度だけ実行。OS の設定変更と他タブの変更を追従する。
   */
  function init() {
    if (typeof window === 'undefined' || state.initialized) return

    state.preference = readStoredPreference()
    state.systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    state.initialized = true
    applyToDocument(resolve(state.preference, state.systemPrefersDark))

    if (!listenersBound) {
      listenersBound = true

      const mql = window.matchMedia('(prefers-color-scheme: dark)')
      mql.addEventListener('change', (e) => {
        state.systemPrefersDark = e.matches
        applyToDocument(resolve(state.preference, state.systemPrefersDark))
      })

      // 他タブでテーマを変えた場合に追従
      window.addEventListener('storage', (e) => {
        if (e.key !== STORAGE_KEY || !e.newValue) return
        const v = e.newValue
        if (v === 'light' || v === 'dark' || v === 'auto') {
          state.preference = v
          applyToDocument(resolve(state.preference, state.systemPrefersDark))
        }
      })
    }
  }

  return {
    preference: toRef(state, 'preference'),
    systemPrefersDark: toRef(state, 'systemPrefersDark'),
    resolvedTheme,
    isDark,
    isReady: computed(() => state.initialized),
    setPreference,
    toggle,
    init,
  }
}
