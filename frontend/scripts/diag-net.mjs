import { chromium } from 'playwright-core'

// 起動するブラウザは CHROME_PATH で上書き可能。未指定なら OS に入っている Google Chrome を使う
// （実行端末に依存する絶対パスは書かない）。
const EXEC = process.env.CHROME_PATH
const URL = process.env.URL || 'https://art.wawa-app.me/RefLens.io/board/47e993d6-139b-4bca-912f-699cf5ba536b'

const browser = await chromium.launch(EXEC ? { executablePath: EXEC, headless: true } : { channel: 'chrome', headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

const failed = []
page.on('requestfailed', r => failed.push([r.resourceType(), r.url(), r.failure()?.errorText]))
page.on('response', async r => {
  if (r.status() >= 400) failed.push([r.request().resourceType(), r.url(), `HTTP ${r.status()}`])
})
page.on('request', r => {
  // モジュールスクリプトとして読まれ、かつ CSS が返っているものを検出
  if (r.resourceType() === 'script' && r.url().includes('lang.css')) {
    failed.push(['SCRIPT-BUT-CSS', r.url(), 'lang.css が script として要求された'])
  }
})
const consoleErrs = []
page.on('console', m => { if (m.type() === 'error') consoleErrs.push(m.text()) })

await page.goto(URL, { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(3500)

console.log('=== 失敗したリクエスト ===')
if (!failed.length) console.log('  なし')
else [...new Set(failed.map(f => f.join(' | ')))].slice(0, 20).forEach(f => console.log('  ' + f))

console.log('\n=== コンソールエラー ===')
if (!consoleErrs.length) console.log('  なし')
else [...new Set(consoleErrs)].slice(0, 10).forEach(e => console.log('  ' + e))

const s = await page.evaluate(() => ({
  items: document.querySelectorAll('.touch-canvas img').length,
  worldChildren: document.querySelector('.will-change-transform')?.children.length ?? -1,
}))
console.log('\n=== 描画状態 ===')
console.log('  canvas images :', s.items)
console.log('  world children:', s.worldChildren)

await browser.close()