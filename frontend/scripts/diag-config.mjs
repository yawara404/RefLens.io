import { chromium } from 'playwright-core'

// 起動するブラウザは CHROME_PATH で上書き可能。未指定なら OS に入っている Google Chrome を使う
// （実行端末に依存する絶対パスは書かない）。
const EXEC = process.env.CHROME_PATH
const URL = process.env.URL || 'https://art.wawa-app.me/RefLens.io/board/47e993d6-139b-4bca-912f-699cf5ba536b'

const browser = await chromium.launch(EXEC ? { executablePath: EXEC, headless: true } : { channel: 'chrome', headless: true })
const page = await browser.newPage()
await page.goto(URL, { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2500)

const cfg = await page.evaluate(() => {
  const raw = document.querySelector('#__NUXT_DATA__')?.textContent || ''
  const pick = k => (raw.match(new RegExp('"' + k + '":"[^"]*"', 'g')) || [])
  return {
    hasData: !!raw,
    appBase: pick('appBase'),
    apiBase: pick('apiBase'),
    mediaBase: pick('mediaBase'),
  }
})

console.log('=== ブラウザ上.runtimeConfig の実値 ===')
console.log('  __NUXT_DATA__ あり:', cfg.hasData)
console.log('  appBase :', cfg.appBase.join(', ') || '(見つからない)')
console.log('  apiBase :', cfg.apiBase.join(', ') || '(見つからない)')
console.log('  mediaBase:', cfg.mediaBase.join(', ') || '(見つからない)')

await browser.close()