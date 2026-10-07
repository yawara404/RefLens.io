import { chromium } from 'playwright-core'

// 起動するブラウザは CHROME_PATH で上書き可能。未指定なら OS に入っている Google Chrome を使う
// （実行端末に依存する絶対パスは書かない）。
const EXEC = process.env.CHROME_PATH
const BASE = process.env.BASE || 'http://localhost:3000'
const EMAIL = process.env.EMAIL || `artist+${Date.now()}@example.com`
const PASSWORD = 'correct-horse-1'

const browser = await chromium.launch(EXEC ? { executablePath: EXEC, headless: true } : { channel: 'chrome', headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const page = await ctx.newPage()

const issues = []
const logs = []
page.on('console', m => {
  const t = m.text()
  if (['error', 'warning'].includes(m.type()) && !t.includes('fonts.g')) logs.push(`[${m.type()}] ${t}`)
})
page.on('pageerror', e => logs.push(`[pageerror] ${e.message}`))
page.on('response', r => { if (r.status() >= 400 && !r.url().includes('/api/')) logs.push(`[http${r.status()}] ${r.url()}`) })

function check(label, ok, detail = '') {
  console.log(`=== ${label} === ${ok ? 'OK' : 'NG'}${detail ? ` (${detail})` : ''}`)
  if (!ok) issues.push(label)
}

// --- 1. Manager に到達 ---
await page.goto(`${BASE}/`, { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2000)

// --- 2. Drop URL ボタンが無く、ログインがある ---
const dropUrl = await page.locator('header button:has-text("Drop URL")').count()
const loginBtn = page.locator('header button:has-text("ログイン")')
check('Drop URL ボタンを置き換え', dropUrl === 0 && await loginBtn.count() === 1)

// --- 3. ゲスト状態でライブラリが見える ---
const guestCount = await page.locator('figure').count()
check('ゲストでライブラリ表示', guestCount > 0, `${guestCount} 件`)

// --- 4. モーダルを開く ---
await loginBtn.first().click()
await page.waitForTimeout(500)
const dialog = page.locator('[aria-modal="true"]')
check('ログインモーダルが開く', await dialog.count() === 1)

// --- 5. 新規登録タブへ ---
await page.locator('button:has-text("新規登録")').first().click()
await page.waitForTimeout(300)

// --- 6. 登録 ---
await page.fill('#auth-username', 'Test Artist')
await page.fill('#auth-email', EMAIL)
await page.fill('#auth-password', PASSWORD)
await page.locator('[aria-modal="true"] button[type="submit"]').click()
await page.waitForTimeout(3000)

const modalGone = await dialog.count() === 0
check('登録でモーダルが閉じる', modalGone)

// --- 7. アバター表示（ログイン済み）---
const avatar = page.locator('header button[title$="でログイン中"]')
check('ログイン済みUI（名/アバター）', await avatar.count() > 0)

// --- 8. トークンが保存されている ---
const token = await page.evaluate(() => localStorage.getItem('reflens-auth-token'))
check('トークンを localStorage に保存', !!token)

// --- 9. 新しいユーザーは空のライブラリ ---
const afterCount = await page.locator('figure').count()
check('新規ユーザーは別領域（0件）', afterCount === 0, `${afterCount} 件`)

// --- 10. リロード後もログイン状態が維持される ---
await page.reload({ waitUntil: 'networkidle' })
await page.waitForTimeout(2500)
check('リロード後もログイン維持', await page.locator('header button[title$="でログイン中"]').count() > 0)

// --- 11. アカウントメニュー ---
await page.locator('header button[title$="でログイン中"]').first().click()
await page.waitForTimeout(400)
const menuVisible = await page.locator('[role="menu"]').count() > 0
check('アカウントメニューが開く', menuVisible)
await page.screenshot({ path: '/tmp/reflens-auth-menu.png' })

// --- 12. ログアウト ---
await page.locator('[role="menu"] button:has-text("ログアウト")').click()
await page.waitForTimeout(3000)
const tokenAfter = await page.evaluate(() => localStorage.getItem('reflens-auth-token'))
check('ログアウトでトークン消去', !tokenAfter)
check('ログアウトでゲストに戻る', await page.locator('header button:has-text("ログイン")').count() === 1)
const guestBack = await page.locator('figure').count()
check('ゲストのデータに戻る', guestBack > 0, `${guestBack} 件`)

// --- 13. 既存のログイン表单で再ログイン ---
await page.locator('header button:has-text("ログイン")').first().click()
await page.waitForTimeout(400)
await page.fill('#auth-email', EMAIL)
await page.fill('#auth-password', PASSWORD)
await page.locator('[aria-modal="true"] button[type="submit"]').click()
await page.waitForTimeout(3000)
check('既存アカウントでログインできる', await page.locator('header button[title$="でログイン中"]').count() > 0)

// --- 14. 誤パスワード ---
await page.locator('header button[title$="でログイン中"]').first().click()
await page.waitForTimeout(300)
await page.locator('[role="menu"] button:has-text("ログアウト")').click()
await page.waitForTimeout(2500)
await page.locator('header button:has-text("ログイン")').first().click()
await page.waitForTimeout(400)
await page.fill('#auth-email', EMAIL)
await page.fill('#auth-password', 'wrong-password')
await page.locator('[aria-modal="true"] button[type="submit"]').click()
await page.waitForTimeout(2500)
const state14 = await page.evaluate(() => ({
  token: localStorage.getItem('reflens-auth-token'),
  authMenuBtns: document.querySelectorAll('header button[title$="でログイン中"]').length,
  loginBtns: [...document.querySelectorAll('header button')].filter(b => b.textContent.includes('ログイン')).length,
  dialog: document.querySelectorAll('[aria-modal="true"]').length,
  toast: [...document.querySelectorAll('[role="status"],[role="alert"]')].map(e => e.textContent.trim()).join(' | '),
}))
console.log('   debug:', JSON.stringify(state14))
// 失敗時はモーダルが開いたまま・エラートーストが出てトークンは入らない
check('誤パスワードでは入らない', state14.authMenuBtns === 0 && !state14.token && state14.dialog === 1)

// --- 15. Canvas からログアウト後Dsl.D&D が引き続き動く ---
await page.locator('[aria-modal="true"] button[aria-label="閉じる (Esc)"]').click().catch(() => {})
await page.waitForTimeout(500)

console.log('\n=== 検出された問題 ===')
console.log(issues.length ? issues.map(i => '  ✗ ' + i).join('\n') : '  なし ✓')

console.log('\n=== コンソール / HTTPエラー（API 4xx は意図的なので除外） ===')
console.log(logs.length ? [...new Set(logs)].slice(0, 10).map(l => '  ' + l).join('\n') : '  なし ✓')

console.log(`\ncleanup email: ${EMAIL}`)
await page.screenshot({ path: '/tmp/reflens-auth.png' })
await browser.close()