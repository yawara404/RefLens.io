import { chromium } from 'playwright-core'

// 起動するブラウザは CHROME_PATH で上書き可能。未指定なら OS に入っている Google Chrome を使う
// （実行端末に依存する絶対パスは書かない）。
const EXEC = process.env.CHROME_PATH
const BASE = process.env.BASE || 'http://localhost:3000'

const browser = await chromium.launch(EXEC ? { executablePath: EXEC, headless: true } : { channel: 'chrome', headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

// Manager: ログインモーダル（ライトテーマ）
await page.goto(`${BASE}/`, { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2000)
await page.locator('header button:has-text("ログイン")').first().click()
await page.waitForTimeout(600)
await page.screenshot({ path: '/tmp/auth-dialog-login.png' })

// 新規登録タブ
await page.locator('button:has-text("新規登録")').first().click()
await page.waitForTimeout(400)
await page.screenshot({ path: '/tmp/auth-dialog-register.png' })

// ダークテーマで Manager ヘッダー
await page.keyboard.press('Escape')
await page.waitForTimeout(300)
await page.evaluate(() => localStorage.setItem('reflens-theme', 'dark'))
await page.reload({ waitUntil: 'networkidle' })
await page.waitForTimeout(2000)
await page.screenshot({ path: '/tmp/auth-manager-dark.png' })

// Canvas ページ（ログイン済みでもゲストでもヘッダーにAuthButton が出る）
const boards = await page.evaluate(async () => {
  const r = await fetch('http://127.0.0.1:8080/api/v1/boards/').then(x => x.json())
  return r.map(b => b.id)
})
if (boards[0]) {
  await page.goto(`${BASE}/board/${boards[0]}`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(2500)
  await page.keyboard.press('b')
  await page.waitForTimeout(800)
  await page.screenshot({ path: '/tmp/auth-canvas-dark.png' })
}

// View ページ
await page.goto(`${BASE}/view`, { waitUntil: 'networkidle' })
await page.waitForTimeout(2500)
await page.screenshot({ path: '/tmp/auth-view-dark.png' })

console.log('screenshots written')
await browser.close()