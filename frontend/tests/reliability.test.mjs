import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import { createRequire } from 'node:module'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const { createPinia, setActivePinia } = require('pinia')
function loadSource(path, globals = {}) {
  const source = readFileSync(new URL(path, import.meta.url), 'utf8')
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  const exports = {}
  vm.runInNewContext(code, {
    exports, console: { error() {} }, setTimeout,
    require(name) {
      if (name === '~/composables/useToast') return { useToast: () => ({ error() {}, success() {} }) }
      if (name === '~/composables/useBackendUrl') return { useBackendUrl: () => ({ apiBase: { value: '/api' } }) }
      return require(name)
    },
    ...globals,
  }, { filename: path })
  return exports
}
function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function storeWith(fetch) {
  setActivePinia(createPinia())
  const store = loadSource('../stores/boardStore.ts', { $fetch: fetch }).useBoardStore()
  store.currentBoard = { id: 'board-a', title: 'A' }
  store.items = [{ id: 'item', pos_x: 1 }]
  store.hasUnsavedChanges = true
  return store
}

test('edits made during a save remain unsaved', async () => {
  const request = deferred()
  const store = storeWith(() => request.promise)
  const saving = store.saveCanvas(0, 0, 1)
  await Promise.resolve()
  store.items[0].pos_x = 25
  request.resolve({})
  assert.equal(await saving, true)
  assert.equal(store.hasUnsavedChanges, true)
  assert.equal(store.isSaving, false)
})

test('overlapping saves reach the server in order with independent snapshots', async () => {
  const first = deferred(), second = deferred()
  const calls = []
  const store = storeWith((url, options) => {
    calls.push(options.body)
    return calls.length === 1 ? first.promise : second.promise
  })
  const a = store.saveCanvas(0, 0, 1)
  await Promise.resolve()
  store.items[0].pos_x = 99
  const b = store.saveCanvas(10, 20, 2)
  await Promise.resolve()
  assert.equal(calls.length, 1)
  assert.equal(calls[0].items[0].pos_x, 1)
  first.resolve({})
  await a
  assert.equal(store.isSaving, true)
  assert.equal(store.hasUnsavedChanges, true)
  assert.equal(calls.length, 2)
  assert.equal(calls[1].items[0].pos_x, 99)
  second.resolve({})
  assert.equal(await b, true)
  assert.equal(store.hasUnsavedChanges, false)
  assert.equal(store.isSaving, false)
})

test('failed saves retain changes and allow retry', async () => {
  let fail = true
  const store = storeWith(async () => { if (fail) throw new Error('offline'); return {} })
  assert.equal(await store.saveCanvas(0, 0, 1), false)
  assert.equal(store.hasUnsavedChanges, true)
  fail = false
  assert.equal(await store.saveCanvas(0, 0, 1), true)
  assert.equal(store.hasUnsavedChanges, false)
})

test('queued saves for a previous board are discarded', async () => {
  const first = deferred()
  let calls = 0
  const store = storeWith(() => { calls++; return first.promise })
  const a = store.saveCanvas(0, 0, 1)
  await Promise.resolve()
  const b = store.saveCanvas(0, 0, 1)
  store.currentBoard = { id: 'board-b', title: 'B' }
  store.hasUnsavedChanges = true
  first.resolve({})
  await a
  assert.equal(await b, false)
  assert.equal(calls, 1)
  assert.equal(store.hasUnsavedChanges, true)
})

test('late board responses cannot replace the latest board', async () => {
  const older = deferred(), newer = deferred()
  const store = storeWith(url => url.endsWith('/old') ? older.promise : newer.promise)
  const a = store.loadBoard('old')
  const b = store.loadBoard('new')
  newer.resolve({ id: 'new', items: [] })
  await b
  older.resolve({ id: 'old', items: [] })
  assert.equal(await a, null)
  assert.equal(store.currentBoard.id, 'new')
  assert.equal(store.isLoading, false)
})

test('failed initial board load never returns a stale board', async () => {
  const store = storeWith(async url => {
    if (url.endsWith('/boards/')) return [{ id: 'missing' }]
    throw new Error('not found')
  })
  assert.equal(await store.loadFirstBoard(), null)
})

test('image extraction falls back to files when the items list is empty', () => {
  const { extractImagesFromDataTransfer } = loadSource('../composables/useImageProcessor.ts').useImageProcessor()
  const image = { type: 'image/png' }
  assert.equal(extractImagesFromDataTransfer({ items: [], files: [image, { type: 'text/plain' }] })[0], image)
})

test('clipboard fallback cleans up and restores focus even when copying throws', async () => {
  let removed = false, focused = false, appended = false
  const previousFocus = { isConnected: true, closest: () => null, focus: () => { focused = true } }
  const textarea = { style: {}, setAttribute() {}, select() {}, remove() { removed = true } }
  const document = {
    activeElement: previousFocus, createElement: () => textarea,
    body: { appendChild() { appended = true } }, execCommand() { throw new Error('denied') },
  }
  const { copyToClipboard } = loadSource('../composables/useImageProcessor.ts', { document }).useImageProcessor()
  assert.equal(await copyToClipboard('test'), false)
  assert.equal(appended && removed && focused, true)
})

test('clipboard fallback stays inside the focused modal', async () => {
  let appended = false
  const modal = { appendChild() { appended = true } }
  const document = {
    activeElement: { isConnected: true, closest: () => modal, focus() {} },
    createElement: () => ({ style: {}, setAttribute() {}, select() {}, remove() {} }),
    execCommand: () => true,
  }
  const { copyToClipboard } = loadSource('../composables/useImageProcessor.ts', { document }).useImageProcessor()
  assert.equal(await copyToClipboard('test'), true)
  assert.equal(appended, true)
})

function dialogHarness() {
  const listeners = new Map()
  const watchers = []
  let document
  class Element {
    constructor(name, children = []) { this.name = name; this.children = children; this.tabIndex = 0; this.isConnected = true }
    contains(node) { return node === this || this.children.includes(node) }
    querySelectorAll() { return this.children }
    querySelector() { return null }
    setAttribute() {}
    matches() { return false }
    closest() { return null }
    getClientRects() { return [{}] }
    focus() {
      document.activeElement = this
      for (const fn of listeners.get('focusin') || []) fn({ target: this })
    }
  }
  document = {
    activeElement: new Element('trigger'), body: { style: { overflow: 'auto', paddingRight: '3px' } },
    documentElement: { clientWidth: 1000 },
    addEventListener(name, handler) { if (!listeners.has(name)) listeners.set(name, new Set()); listeners.get(name).add(handler) },
    removeEventListener(name, handler) { listeners.get(name)?.delete(handler) },
  }
  const { useDialogA11y } = loadSource('../composables/useDialogA11y.ts', {
    document, window: { innerWidth: 1015 }, HTMLElement: Element,
    getComputedStyle: () => ({ visibility: 'visible' }),
    require: name => {
      assert.equal(name, 'vue')
      return {
        ref: value => ({ value }), nextTick: fn => Promise.resolve().then(fn),
        onMounted() {}, onUnmounted() {},
        watch: (source, callback) => { watchers.push(callback); callback(source.value) },
      }
    },
  })
  function key(key, shiftKey = false) {
    const event = { key, shiftKey, defaultPrevented: false, preventDefault() { this.defaultPrevented = true }, stopImmediatePropagation() { this.stopped = true } }
    for (const fn of [...(listeners.get('keydown') || [])]) { fn(event); if (event.stopped) break }
    return event
  }
  function create(children = [new Element('first'), new Element('last')]) {
    const state = { value: false }
    let closed = 0
    const index = watchers.length
    const dialog = useDialogA11y(state, () => { closed++; state.value = false; watchers[index](false) })
    dialog.dialogRef.value = new Element('dialog', children)
    return { ...dialog, get closed() { return closed }, open() { state.value = true; watchers[index](true) }, children }
  }
  return { document, create, key }
}

test('dialogs focus their first control, wrap Tab both ways, and restore the trigger', async () => {
  const { document, create, key } = dialogHarness()
  const trigger = document.activeElement
  const dialog = create()
  dialog.open()
  await Promise.resolve()
  assert.equal(document.activeElement.name, 'first')
  assert.equal(document.body.style.overflow, 'hidden')
  trigger.focus()
  assert.equal(document.activeElement.name, 'first')
  dialog.children[1].focus()
  assert.equal(key('Tab').defaultPrevented, true)
  assert.equal(document.activeElement.name, 'first')
  key('Tab', true)
  assert.equal(document.activeElement.name, 'last')
  key('Escape')
  assert.equal(dialog.closed, 1)
  assert.equal(document.activeElement, trigger)
  assert.equal(document.body.style.overflow, 'auto')
  assert.equal(document.body.style.paddingRight, '3px')
})

test('Escape closes only the top dialog and keeps the background scroll locked', async () => {
  const { document, create, key } = dialogHarness()
  const outer = create(), inner = create()
  outer.open()
  await Promise.resolve()
  inner.open()
  await Promise.resolve()
  key('Escape')
  assert.equal(inner.closed, 1)
  assert.equal(outer.closed, 0)
  assert.equal(document.body.style.overflow, 'hidden')
  assert.equal(document.activeElement, outer.children[0])
  key('Escape')
  assert.equal(outer.closed, 1)
  assert.equal(document.body.style.overflow, 'auto')
})

test('dialogs without controls keep focus inside on Tab', async () => {
  const { document, create, key } = dialogHarness()
  const dialog = create([])
  dialog.open()
  await Promise.resolve()
  assert.equal(document.activeElement, dialog.dialogRef.value)
  assert.equal(key('Tab').defaultPrevented, true)
  assert.equal(document.activeElement, dialog.dialogRef.value)
  key('Escape')
})

test('drag previews fit both dimensions for portraits, landscapes, and invalid sizes', () => {
  const { fitDragPreview } = loadSource('../utils/dragPreview.ts')
  for (const [width, height, expectedWidth, expectedHeight] of [
    [4000, 6000, 107, 160], [8000, 800, 160, 16], [800, 8000, 16, 160],
    [80, 40, 80, 40], [0, 0, 160, 160], [Infinity, NaN, 160, 160],
  ]) {
    const size = fitDragPreview(width, height)
    assert.equal(size.width, expectedWidth)
    assert.equal(size.height, expectedHeight)
  }
  const tallCanvasImage = fitDragPreview(1000, 10000, 220, 260)
  assert.equal(tallCanvasImage.width, 26)
  assert.equal(tallCanvasImage.height, 260)
})

test('native drag uses a bounded canvas snapshot and removes it after dragstart', () => {
  const image = { complete: true, naturalWidth: 3840, naturalHeight: 2160 }
  let appended, dragImage, drawArgs, cleanup, removed = false
  const canvas = {
    style: {}, setAttribute() {}, remove() { removed = true },
    getContext: () => ({ fillRect() {}, drawImage(...args) { drawArgs = args } }),
  }
  const { setReferenceDragPreview } = loadSource('../utils/dragPreview.ts', {
    document: { createElement: () => canvas, body: { appendChild(node) { appended = node } } },
    setTimeout: callback => { cleanup = callback },
  })
  setReferenceDragPreview({
    currentTarget: { querySelector: () => image },
    dataTransfer: { setDragImage(node) { dragImage = node } },
  })
  assert.equal(dragImage, canvas)
  assert.equal(appended, canvas)
  assert.equal(canvas.width, 160)
  assert.equal(canvas.height, 90)
  assert.deepEqual(drawArgs, [image, 0, 0, 160, 90])
  assert.equal(removed, false)
  cleanup()
  assert.equal(removed, true)
})
