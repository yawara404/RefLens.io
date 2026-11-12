import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { createRequire } from 'node:module'
import ts from 'typescript'

/**
 * 抽出した utils は Nuxt の alias（`~/...`）を使うため、
 * 既存の reliability.test.mjs と同じ方式（TS を transpile して vm で実行）で読み込む。
 */
const require = createRequire(import.meta.url)

/** vm 内で生成された配列/オブジェクトはプロトタイプが異なるため、比較前に素の値へ落とす */
const plain = value => JSON.parse(JSON.stringify(value))

function loadModule(relativePath, shims = {}) {
  const source = readFileSync(new URL(relativePath, import.meta.url), 'utf8')
  const code = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText

  const exports = {}
  vm.runInNewContext(
    code,
    {
      exports,
      console: { error() {}, warn() {} },
      require(name) {
        if (name in shims) return shims[name]
        return require(name)
      },
    },
    { filename: relativePath },
  )
  return exports
}

const foldersUtil = loadModule('../utils/folders.ts')
const bookmarksUtil = loadModule('../utils/bookmarks.ts', {
  '~/utils/folders': foldersUtil,
  '~/types': {},
})
const domUtil = loadModule('../utils/dom.ts')

const { formatFolderLabel, folderColorByName } = foldersUtil
const {
  BOOKMARK_SORT_OPTIONS,
  hexToRgb,
  rgbToHsl,
  colorDistance,
  bookmarkPalette,
  bookmarkMinColorDistance,
  bookmarkColorMetrics,
  buildBookmarkCorpus,
  topAiTags,
  sortBookmarks,
} = bookmarksUtil
const { isTypingTarget } = domUtil

/** テスト用の最小ブックマーク */
function item(id, extra = {}) {
  return {
    id,
    title: `title-${id}`,
    file_path: '/uploads/a.jpg',
    source_type: 'pixiv',
    width: 100,
    height: 100,
    aspect_ratio: 1,
    folder_name: 'All References',
    created_at: '2026-01-01T00:00:00Z',
    ai_analysis: {
      composition: '',
      lighting: '',
      pose_anatomy: '',
      costume_structure: '',
      palette: [],
      tags: [],
    },
    ...extra,
  }
}

test('hexToRgb は 3桁/6桁を受け付け、不正値は null', () => {
  assert.deepEqual(plain(hexToRgb('#fff')), [255, 255, 255])
  assert.deepEqual(plain(hexToRgb('4338ca')), [67, 56, 202])
  assert.equal(hexToRgb('nope'), null)
  assert.equal(hexToRgb(''), null)
})

test('rgbToHsl は赤の色相を 0 度にする', () => {
  const red = rgbToHsl(255, 0, 0)
  assert.equal(Math.round(red.h), 0)
  assert.equal(red.s, 1)
  assert.equal(red.l, 0.5)
})

test('colorDistance は同色 0・不正値 999', () => {
  assert.equal(colorDistance('#000000', '#000'), 0)
  assert.equal(colorDistance('zzz', '#fff'), 999)
})

test('bookmarkPalette は AI パレット→フォルダカラーの順でフォールバックする', () => {
  const folders = [{ name: 'Folder A', icon: '', color: '#112233', count: 1 }]
  assert.deepEqual(plain(bookmarkPalette(item('a'), folders)), ['#6366f1'])
  assert.deepEqual(plain(bookmarkPalette(item('b', { folder_name: 'Folder A' }), folders)), ['#112233'])
  assert.deepEqual(
    plain(
      bookmarkPalette(
        item('c', { ai_analysis: { ...item('c').ai_analysis, palette: ['#ff0000', 'invalid'] } }),
        folders,
      ),
    ),
    ['#ff0000'],
  )
})

test('bookmarkMinColorDistance は最も近い色までの距離を返す', () => {
  const b = item('a', {
    ai_analysis: { ...item('a').ai_analysis, palette: ['#ff0000', '#0000ff'] },
  })
  assert.ok(bookmarkMinColorDistance(b, '#ff0000') < 1)
  assert.ok(bookmarkMinColorDistance(b, '#0000ff') < 1)
  assert.ok(bookmarkMinColorDistance(b, '#00ff00') > 100)
})

test('bookmarkColorMetrics は無彩色を色相の末尾に回す', () => {
  const gray = item('g', {
    ai_analysis: { ...item('g').ai_analysis, palette: ['#808080'] },
  })
  const metrics = bookmarkColorMetrics(gray)
  assert.ok(metrics.hue >= 360)
  assert.equal(metrics.saturation, 0)
})

test('buildBookmarkCorpus はタグ・構図・パレットを含めて小文字化する', () => {
  const b = item('a', {
    title: 'Blue Sky',
    author_name: 'Artist',
    folder_name: 'Landscape',
    ai_analysis: {
      composition: 'Triangle',
      lighting: 'Backlight',
      pose_anatomy: '',
      costume_structure: '',
      palette: ['#AABBCC'],
      tags: ['Sky', 'Cloud'],
    },
  })
  const corpus = buildBookmarkCorpus(b)
  for (const word of ['blue sky', 'artist', 'landscape', 'triangle', 'backlight', 'sky', 'cloud', '#aabbcc']) {
    assert.ok(corpus.includes(word), `${word} を含む: ${corpus}`)
  }
})

test('topAiTags は出現回数順に並べ、件数で打ち切る', () => {
  const list = [
    item('1', { ai_analysis: { ...item('1').ai_analysis, tags: ['sky', 'cloud', 'sky'] } }),
    item('2', { ai_analysis: { ...item('2').ai_analysis, tags: ['cloud', 'sea'] } }),
    item('3', { ai_analysis: { ...item('3').ai_analysis, tags: ['  '] } }),
  ]
  assert.deepEqual(plain(topAiTags(list, 2)), [
    { tag: 'sky', count: 2 },
    { tag: 'cloud', count: 2 },
  ])
})



test('sortBookmarks は追加日時・タイトル・作者名で並べ替える', () => {
  const older = item('old', { created_at: '2025-01-01T00:00:00Z', title: 'b', author_name: 'Z' })
  const newer = item('new', { created_at: '2026-01-01T00:00:00Z', title: 'a', author_name: 'A' })

  assert.deepEqual(plain(sortBookmarks([older, newer], 'newest').map(b => b.id)), ['new', 'old'])
  assert.deepEqual(plain(sortBookmarks([newer, older], 'oldest').map(b => b.id)), ['old', 'new'])
  assert.deepEqual(plain(sortBookmarks([older, newer], 'title').map(b => b.id)), ['new', 'old'])
  assert.deepEqual(plain(sortBookmarks([older, newer], 'author').map(b => b.id)), ['new', 'old'])
})

test('sortBookmarks は指定色に近い順を最優先する', () => {
  const red = item('red', { ai_analysis: { ...item('red').ai_analysis, palette: ['#ff0000'] } })
  const blue = item('blue', { ai_analysis: { ...item('blue').ai_analysis, palette: ['#0000ff'] } })
  assert.deepEqual(
    plain(sortBookmarks([blue, red], 'newest', { targetColor: '#ff0000' }).map(b => b.id)),
    ['red', 'blue'],
  )
})

test('sortBookmarks はフォルダカラー順で同じフォルダをまとめる', () => {
  const folders = [
    { name: 'Red', icon: '', color: '#ff0000', count: 1 },
    { name: 'Blue', icon: '', color: '#0000ff', count: 1 },
  ]
  const blueItem = item('blue', { folder_name: 'Blue' })
  const redItem = item('red', { folder_name: 'Red' })
  assert.deepEqual(
    plain(sortBookmarks([blueItem, redItem], 'folder_color', { folders }).map(b => b.id)),
    ['red', 'blue'],
  )
})

test('sortBookmarks は元の配列を破壊しない', () => {
  const list = [item('b', { created_at: '2025-01-01T00:00:00Z' }), item('a')]
  const sorted = sortBookmarks(list, 'newest')
  assert.notEqual(sorted, list)
  assert.deepEqual(list.map(b => b.id), ['b', 'a'])
})

test('formatFolderLabel / folderColorByName は予約フォルダを吸収する', () => {
  assert.equal(formatFolderLabel(undefined), 'すべての資料')
  assert.equal(formatFolderLabel('All References'), 'すべての資料')
  assert.equal(formatFolderLabel('My Folder'), 'My Folder')

  const folders = [{ name: 'My Folder', icon: '', color: '#abcdef', count: 1 }]
  assert.equal(folderColorByName(folders, 'My Folder'), '#abcdef')
  assert.equal(folderColorByName(folders, 'Missing'), '#6366f1')
})

test('isTypingTarget は入力要素と contenteditable を判定する', () => {
  assert.equal(isTypingTarget({ tagName: 'INPUT' }), true)
  assert.equal(isTypingTarget({ tagName: 'TEXTAREA' }), true)
  assert.equal(isTypingTarget({ tagName: 'SELECT' }), true)
  assert.equal(isTypingTarget({ tagName: 'DIV', isContentEditable: true }), true)
  assert.equal(isTypingTarget({ tagName: 'DIV' }), false)
  assert.equal(isTypingTarget(null), false)
})

test('並び替えの選択肢は一覧と一致する', () => {
  assert.deepEqual(
    plain(BOOKMARK_SORT_OPTIONS.map(option => option.id)),
    ['newest', 'oldest', 'color_hue', 'color_bright', 'color_dark', 'folder_color', 'title', 'author'],
  )
})
