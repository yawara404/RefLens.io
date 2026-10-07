import { chromium } from 'playwright-core'

// 起動するブラウザは CHROME_PATH で上書き可能。未指定なら OS に入っている Google Chrome を使う
// （実行端末に依存する絶対パスは書かない）。
const EXEC = process.env.CHROME_PATH
const BASE = process.env.BASE || 'http://localhost:3000'
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
await page.waitForTimeout(3000)

// --- サイドバーを開く ---
const aside = page.locator('aside[aria-label="資料ライブラリ"]')
console.log(`=== 初期状態のサイドバー === ${await aside.count() ? 'OK (最初から表示)' : '非表示'}`)

if (!(await aside.count())) {
  // B キー
  await page.keyboard.press('b')
  await page.waitForTimeout(800)
  console.log(`=== Bキーで開く === ${await aside.count() ? 'OK' : 'NG'}`)
  if (!(await aside.count())) issues.push('Bキーでサイドバーが開かない')
}

const tiles = aside.locator('figure[draggable="true"], div[draggable="true"]')
const tileCount = await tiles.count()
console.log(`=== ライブラリ件数 === ${tileCount}`)

// 画像が実際に描画されているか
const imgStats = await page.evaluate(() => {
  const imgs = [...document.querySelectorAll('aside[aria-label="資料ライブラリ"] img')]
  return `${imgs.filter(i => i.naturalWidth > 0).length}/${imgs.length}`
})
console.log(`=== サムネイル読込 === ${imgStats}`)

// --- キャンバス側 ---
const before = await page.locator('.will-change-transform > div[class*="absolute top-0 left-0"]').count()

// --- ドラッグ&ドロップ ---
const canvasBox = await page.locator('.touch-canvas').boundingBox()
if (canvasBox && tileCount > 0) {
  const src = await tiles.first().boundingBox()
  const dropX = canvasBox.x + canvasBox.width * 0.65
  const dropY = canvasBox.y + canvasBox.height * 0.5

  // dataTransfer のotyp を見るため、dragstart をフックして実際に_information_ を読む
  await page.evaluate(() => {
    window.__dt = null
    document.addEventListener('dragstart', (e) => { window.__dt = e.dataTransfer }, true)
  })

  await page.mouse.move(src.x + src.width / 2, src.y + src.height / 2)
  await page.mouse.down()
  await page.mouse.move(src.x + src.width / 2 + 40, src.y + src.height / 2 + 20, { steps: 8 })
  await page.mouse.move(dropX, dropY, { steps: 25 })
  await page.waitForTimeout(300)
  await page.mouse.up()
  await page.waitForTimeout(2500)

  const dtTypes = await page.evaluate(() => window.__dt ? [...window.__dt.types] : null)
  console.log(`=== dragstart の dataTransfer === ${dtTypes ? dtTypes.join(', ') : 'イベント未発火'}`)

  const after = await page.locator('.will-change-transform > div[class*="absolute top-0 left-0"]').count()
  console.log(`=== D&D で追加 === ${before} -> ${after} ${after > before ? 'OK' : 'NG'}`)
  if (after <= before) issues.push('サイドバーからキャンバスへのドラッグ＆ドロップで追加されない')

  const toast = await page.evaluate(() =>
    [...document.querySelectorAll('[class*="toast"], [role="status"], [role="alert"]')].map(e => e.textContent.trim()).join(' | '))
  if (toast) console.log(`=== トースト === ${toast}`)
} else {
  issues.push('キャンバス or ライブラリタイルの boundingBox が取れない')
}

console.log('\n=== 検出された問題 ===')
console.log(issues.length ? issues.map(i => '  ✗ ' + i).join('\n') : '  なし ✓')

console.log('\n=== コンソール / HTTPエラー ===')
console.log(logs.length ? [...new Set(logs)].slice(0, 10).map(l => '  ' + l).join('\n') : '  なし ✓')

await page.screenshot({ path: '/tmp/reflens-browser.png' })
console.log('\nscreenshot: /tmp/reflens-browser.png')
await browser.close()