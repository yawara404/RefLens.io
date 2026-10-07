import { chromium } from 'playwright-core'

// 起動するブラウザは CHROME_PATH で上書き可能。未指定なら OS に入っている Google Chrome を使う
// （実行端末に依存する絶対パスは書かない）。
const EXEC = process.env.CHROME_PATH
const URL = process.env.URL || 'https://art.wawa-app.me/RefLens.io/board/47e993d6-139b-4bca-912f-699cf5ba536b'

const browser = await chromium.launch(EXEC ? { executablePath: EXEC, headless: true } : { channel: 'chrome', headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

// script として要求されたもの = module / classic script。レスポンスの Content-Type を見る
const scriptResponses = []
page.on('response', async r => {
  const rt = r.request().resourceType()
  if (rt !== 'script' && rt !== 'stylesheet') return
  const ct = (await r.allHeaders())['content-type'] || ''
  scriptResponses.push({
    kind: rt,
    ok: r.status(),
    ct,
    isCssButScript: rt === 'script' && ct.includes('text/css'),
    isJsButCss: rt === 'stylesheet' && ct.includes('javascript'),
    url: r.url().replace('https://art.wawa-app.me', ''),
  })
})

await page.goto(URL, { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(3000)

console.log('=== script / stylesheet の応答一覧 ===')
for (const r of scriptResponses) {
  const flag = r.isCssButScript ? '  ★MIME不一致' : r.isJsButCss ? '  ★MIME不一致' : ''
  console.log(`  [${r.kind.padEnd(10)}] ${r.ok} ${r.ct.split(';')[0].padEnd(26)} ${r.url.slice(0, 78)}${flag}`)
}

console.log('\n=== ページ内の <script type=module> ===')
const html = await page.content()
const mods = [...html.matchAll(/<script[^>]*type="module"[^>]*src="([^"]+)"/g)].map(m => m[1])
mods.forEach(m => console.log('  ' + m.slice(0, 90)))
console.log('  (合計 ' + mods.length + ')')

await browser.close()