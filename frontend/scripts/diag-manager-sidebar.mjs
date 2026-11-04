import { chromium } from 'playwright-core'

// Manager サイドバー（Tune drop 風レイアウト）の実機確認。
//   BASE=http://localhost:3311 node scripts/diag-manager-sidebar.mjs
// スクリーンショットは /tmp/sidebar-*.png に出力する。
const EXEC = process.env.CHROME_PATH
const BASE = process.env.BASE || 'http://localhost:3000'
const EMAIL = process.env.EMAIL || `artist+${Date.now()}@example.com`
const PASSWORD = 'correct-horse-1'

const browser = await chromium.launch(EXEC ? { executablePath: EXEC, headless: true } : { channel: 'chrome', headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 950 } })

const issues = []
const logs = []
page.on('console', m => {
  const t = m.text()
  if (['error', 'warning'].includes(m.type()) && !t.includes('fonts.g')) logs.push(`[${m.type()}] ${t}`)
})
page.on('pageerror', e => logs.push(`[pageerror] ${e.message}`))

function check(label, ok, detail = '') {
  console.log(`=== ${label} === ${ok ? 'OK' : 'NG'}${detail ? ` (${detail})` : ''}`)
  if (!ok) issues.push(label)
}

const aside = page.locator('aside')

// --- 1. 新規登録してライブラリ（自分のフォルダ）を表示 ---
await page.goto(`${BASE}/`, { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(1500)
await page.locator('header button:has-text("ログイン")').first().click()
await page.waitForTimeout(500)
await page.locator('button:has-text("新規登録")').first().click()
await page.waitForTimeout(300)
await page.fill('#auth-username', 'Sidebar Check')
await page.fill('#auth-email', EMAIL)
await page.fill('#auth-password', PASSWORD)
await page.locator('[aria-modal="true"] button[type="submit"]').click()
await page.waitForTimeout(3000)

check('サイドバーが表示される', await aside.isVisible())
await aside.screenshot({ path: '/tmp/sidebar-light.png' })

// --- 2. Tune drop 風の構成要素 ---
check('新規コレクション作成ボタン', await page.locator('aside button:has-text("新規コレクション作成")').count() === 1)
check('コレクション検索', await page.locator('aside input[placeholder="コレクションを検索..."]').count() === 1)
check('並び順セレクト', await page.locator('aside select').count() === 1)
check('ホーム行', await page.locator('aside nav button:has-text("ホーム（ライブラリ）")').count() === 1)
check('ソース別ビュー（4件）', await page.locator('aside nav button').count() === 5, `${await page.locator('aside nav button').count()} 行`)

const lockedRows = await page.locator('aside [role="button"]').count()
check('既定コレクションがロック行として並ぶ', lockedRows > 0, `${lockedRows} 行`)

// --- 3. コレクション作成 → 行が増える ---
await page.locator('aside button:has-text("新規コレクション作成")').click()
await page.waitForTimeout(300)
await page.fill('aside input[placeholder="コレクション名"]', 'アナトミア')
await page.locator('aside button:has-text("作成")').click()
await page.waitForTimeout(2500)

const createdRow = page.locator('aside [role="button"]:has-text("アナトミア")')
check('作成したコレクションが行に出る', await createdRow.count() === 1)
check('作成した行だけグリップを持つ（draggable）', await createdRow.getAttribute('draggable') === 'true')
await aside.screenshot({ path: '/tmp/sidebar-after-create.png' })

// --- 4. 検索で絞り込み ---
await page.fill('aside input[placeholder="コレクションを検索..."]', 'アナト')
await page.waitForTimeout(400)
check('検索で絞り込める', await page.locator('aside [role="button"]').count() === 1, `${await page.locator('aside [role="button"]').count()} 行`)
await page.fill('aside input[placeholder="コレクションを検索..."]', '')
await page.waitForTimeout(400)

// --- 5. 並び順セレクトが資料リストに効く ---
await page.selectOption('aside select', 'title')
await page.waitForTimeout(400)
check('並び順セレクトを変更できる', await page.locator('aside select').inputValue() === 'title')


// --- 6. ⋮ メニューからリネーム ---
await createdRow.locator('button').first().click()
await page.waitForTimeout(400)
check('操作メニューが開く', await page.locator('aside [role="menu"]').count() === 1)
await page.locator('aside [role="menu"] button:has-text("名前を変更")').click()
await page.waitForTimeout(300)
await page.fill('aside [role="menu"] input', 'アナトミア改')
await page.locator('aside [role="menu"] button:has-text("保存")').click()
await page.waitForTimeout(2500)
check('リネームが反映される', await page.locator('aside [role="button"]:has-text("アナトミア改")').count() === 1)
await aside.screenshot({ path: '/tmp/sidebar-after-rename.png' })

// --- 7. ドラッグで並べ替え（自作コレクションをもう 1 つ作ってから） ---
await page.locator('aside button:has-text("新規コレクション作成")').click()
await page.waitForTimeout(300)
await page.fill('aside input[placeholder="コレクション名"]', 'ポーズ資料')
await page.locator('aside button:has-text("作成")').click()
await page.waitForTimeout(2500)

const orderBefore = await page.locator('aside [role="button"]').allInnerTexts()
await page.locator('aside [role="button"]:has-text("ポーズ資料")').dragTo(page.locator('aside [role="button"]:has-text("アナトミア改")'))
await page.waitForTimeout(600)
const orderAfter = await page.locator('aside [role="button"]').allInnerTexts()
check('ドラッグで並び順が変わる', orderBefore.join('|') !== orderAfter.join('|'))
const savedOrder = await page.evaluate(() => localStorage.getItem('reflens-folder-order'))
check('並び順を localStorage に保存', !!savedOrder, savedOrder || '')
await aside.screenshot({ path: '/tmp/sidebar-after-drag.png' })

// --- 8. ダークテーマ + リロードでも維持 ---
await page.evaluate(() => localStorage.setItem('reflens-theme', 'dark'))
await page.reload({ waitUntil: 'networkidle' })
await page.waitForTimeout(2500)
check('リロード後もログイン維持', await page.locator('header button[aria-label="アカウントメニュー"]').count() > 0)
check('並び順がリロード後も維持される', (await page.locator('aside [role="button"]').allInnerTexts()).join('|') === orderAfter.join('|'))
await aside.screenshot({ path: '/tmp/sidebar-dark.png' })

// --- 9. ⋮ メニューから削除（中の資料は All References へ） ---
await page.locator('aside [role="button"]:has-text("アナトミア改") button').first().click()
await page.waitForTimeout(400)
await page.locator('aside [role="menu"] button:has-text("コレクションを削除")').click()
await page.waitForTimeout(300)
await page.locator('aside [role="menu"] button:has-text("削除する")').click()
await page.waitForTimeout(2500)
check('削除すると行が消える', await page.locator('aside [role="button"]:has-text("アナトミア改")').count() === 0)
await aside.screenshot({ path: '/tmp/sidebar-after-delete.png' })

check('コンソールエラーなし', logs.length === 0, logs.slice(0, 5).join(' / '))

await browser.close()
console.log(issues.length ? `\nNG: ${issues.join(', ')}` : '\nすべて OK')
process.exit(issues.length ? 1 : 0)
