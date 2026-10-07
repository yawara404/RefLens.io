import { chromium } from 'playwright-core'

// 起動するブラウザは CHROME_PATH で上書き可能。未指定なら OS に入っている Google Chrome を使う
// （実行端末に依存する絶対パスは書かない）。
const EXEC = process.env.CHROME_PATH
const BASE = process.env.BASE || 'https://art.wawa-app.me/RefLens.io'
const BOARD = process.env.BOARD || '47e993d6-139b-4bca-912f-699cf5ba536b'

const browser = await chromium.launch(EXEC ? { executablePath: EXEC, headless: true } : { channel: 'chrome', headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

const issues = []
const logs = []
page.on('console', m => {
  const t = m.text()
  if (['error', 'warning'].includes(m.type()) && !t.includes('fonts.g')) logs.push(`[${m.type()}] ${t}`)
})
page.on('pageerror', e => logs.push(`[pageerror] ${e.message}`))
page.on('response', r => { if (r.status() >= 400) logs.push(`[http${r.status()}] ${r.url()}`) })

await page.goto(`${BASE}/board/${BOARD}`, { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(3500)

const state = await page.evaluate(() => {
  const canvas = document.querySelector('.touch-canvas')
  const items = document.querySelectorAll('.will-change-transform > div[class*="absolute top-0 left-0"]')
  const imgs = [...document.querySelectorAll('.touch-canvas img')]
  return {
    canvasExists: !!canvas,
    itemCount: items.length,
    imgLoaded: `${imgs.filter(i => i.naturalWidth > 0).length}/${imgs.length}`,
  }
})
console.log('=== 状態 ===')
for (const [k, v] of Object.entries(state)) console.log(`  ${k.padEnd(13)}: ${v}`)
if (!state.canvasExists) issues.push('キャンバス要素が無い')
if (state.itemCount === 0) issues.push('アイテムが1件も描画されていない')
if (state.imgLoaded !== `3/3` && !state.imgLoaded.startsWith(`${state.itemCount}/${state.itemCount}`)) {
  issues.push(`画像が未読込: ${state.imgLoaded}`)
}

const worldT = () => page.evaluate(() =>
  document.querySelector('.will-change-transform')?.style.transform || '')
const box = await page.locator('.touch-canvas').boundingBox()

if (box) {
  const cx = box.x + box.width / 2
  const cy = box.y + box.height / 2

  // 1. ホイールでパン
  const t0 = await worldT()
  await page.mouse.move(cx, cy); await page.mouse.wheel(0, -200); await page.waitForTimeout(300)
  const t1 = await worldT()
  console.log(`\n=== ホイールパン === ${t0 !== t1 ? 'OK' : 'NG'}`)
  if (t0 === t1) issues.push('ホイールでパンしない')

  // 2. Space + ドラッグでパン
  await page.keyboard.down('Space')
  const t2 = await worldT()
  await page.mouse.move(cx, cy); await page.mouse.down()
  await page.mouse.move(cx + 150, cy + 100, { steps: 12 }); await page.mouse.up()
  await page.keyboard.up('Space'); await page.waitForTimeout(300)
  const t3 = await worldT()
  console.log(`=== Space+ドラッグ パン === ${t2 !== t3 ? 'OK' : 'NG'}`)
  if (t2 === t3) issues.push('Space+ドラッグでパンしない')

  // 3. アイテム選択 → ドラッグ → 反転
  const itemBox = await page.locator('.will-change-transform > div[class*="absolute top-0 left-0"]').first().boundingBox()
  if (itemBox) {
    const ix = itemBox.x + itemBox.width / 2, iy = itemBox.y + itemBox.height / 2
    await page.mouse.click(ix, iy); await page.waitForTimeout(400)
    const sel = await page.evaluate(() => document.querySelectorAll('.ring-brand').length)
    console.log(`=== アイテム選択 === ${sel > 0 ? 'OK' : 'NG'}`)
    if (sel === 0) issues.push('クリックしても選択されない')

    const p0 = await page.evaluate(() => document.querySelector('.will-change-transform > div[class*="absolute top-0 left-0"]')?.style.transform)
    await page.mouse.move(ix, iy); await page.mouse.down()
    await page.mouse.move(ix + 100, iy + 60, { steps: 12 }); await page.mouse.up()
    await page.waitForTimeout(500)
    const p1 = await page.evaluate(() => document.querySelector('.will-change-transform > div[class*="absolute top-0 left-0"]')?.style.transform)
    console.log(`=== アイテムドラッグ === ${p0 !== p1 ? 'OK' : 'NG'}`)
    if (p0 === p1) issues.push('アイテムをドラッグしても移動しない')

    const h0 = await page.evaluate(() => document.querySelector('.touch-canvas img')?.style.transform)
    await page.keyboard.press('h'); await page.waitForTimeout(400)
    const h1 = await page.evaluate(() => document.querySelector('.touch-canvas img')?.style.transform)
    console.log(`=== Hキーで反転 === ${h0 !== h1 ? 'OK' : 'NG'}`)
    if (h0 === h1) issues.push('Hキーで反転が効かない')
  } else issues.push('アイテムの boundingBox が取れない')

  // 4. ヘルプモーダル
  await page.keyboard.press('?'); await page.waitForTimeout(500)
  const help = await page.evaluate(() => !!document.querySelector('[aria-label="キーボードショートカット一覧"]'))
  console.log(`=== ?でヘルプ === ${help ? 'OK' : 'NG'}`)
  if (!help) issues.push('?でヘルプが開かない')
}

console.log('\n=== 検出された問題 ===')
console.log(issues.length ? issues.map(i => '  ✗ ' + i).join('\n') : '  なし ✓')

console.log('\n=== コンソール / HTTPエラー ===')
console.log(logs.length ? [...new Set(logs)].slice(0, 10).map(l => '  ' + l).join('\n') : '  なし ✓')

await page.screenshot({ path: '/tmp/reflens-canvas.png' })
console.log('\nscreenshot: /tmp/reflens-canvas.png')
await browser.close()