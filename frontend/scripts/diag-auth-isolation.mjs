import { chromium } from 'playwright-core'

// 起動するブラウザは CHROME_PATH で上書き可能。未指定なら OS に入っている Google Chrome を使う
// （実行端末に依存する絶対パスは書かない）。
const EXEC = process.env.CHROME_PATH
const BASE = process.env.BASE || 'http://localhost:3000'
const EMAIL = `artist+${Date.now()}@example.com`
const PASSWORD = 'correct-horse-1'

const browser = await chromium.launch(EXEC ? { executablePath: EXEC, headless: true } : { channel: 'chrome', headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

const issues = []
function check(label, ok, detail = '') {
  console.log(`=== ${label} === ${ok ? 'OK' : 'NG'}${detail ? ` (${detail})` : ''}`)
  if (!ok) issues.push(label)
}

// avatar の title は「<name> でログイン中」なので、
// has-text('ログイン') では両方Tengoにマッチしてしまう。完全一致で出し分ける。
const menuBtn = () => page.locator('header button[title$="でログイン中"]')
const loginBtn = () => page.locator('header button').filter({ hasText: /^ログイン$/ })

async function logoutIfNeeded() {
  if (await menuBtn().count()) {
    await menuBtn().first().click()
    await page.waitForTimeout(400)
    await page.locator('[role="menu"] button:has-text("ログアウト")').click()
    await page.waitForTimeout(2500)
  }
}

async function register(name, email) {
  await loginBtn().click()
  await page.waitForTimeout(500)
  await page.locator('button:has-text("新規登録")').first().click()
  await page.waitForTimeout(300)
  await page.fill('#auth-username', name)
  await page.fill('#auth-email', email)
  await page.fill('#auth-password', PASSWORD)
  await page.locator('[aria-modal="true"] button[type="submit"]').click()
  await page.waitForTimeout(3500)
}

/**
 * 図の枚数が期待値になるまでポーリングする。
 *
 * POST /bookmarks/add は画像をダウンロードし、ollama のバックグラウンド解析が
 * 終わるまで続く GET /bookmarks/ を数秒〜十数秒ブロックする（既存挙動）。
 * そのため固定 sleep ではなく「UI に反映されるまで」を待つ。
 */
async function waitForFigures(expected, timeoutMs = 90000) {
  const deadline = Date.now() + timeoutMs
  let last = await page.locator('figure').count()
  while (Date.now() < deadline) {
    if (last === expected) return { ok: true, n: last }
    await page.waitForTimeout(1000)
    last = await page.locator('figure').count()
  }
  return { ok: false, n: last, timedOut: true }
}

/** トークン付きでバックエンドを直接叩く（UI とは独立に確認する） */
function apiFetch(path) {
  return page.evaluate(async (p) => {
    const t = localStorage.getItem('reflens-auth-token')
    return fetch(`http://127.0.0.1:8080/api/v1${p}`, {
      headers: t ? { Authorization: `Bearer ${t}` } : {},
    }).then(x => x.json())
  }, path)
}

// --- Manager へ ---
await page.goto(`${BASE}/`, { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2000)
await logoutIfNeeded()

// 登録前のゲスト件数を控えておき、ログアウト後に戻ったか比較する
const guestBefore = await page.locator('figure').count()
console.log(`   (登録前のゲスト件数: ${guestBefore})`)

// --- ユーザーAを登録し、URLを保存 ---
await register('Alice', EMAIL)
check('ユーザーAを登録', await menuBtn().count() > 0)

// 登録直後の再読み込み（board-refresh プラグイン）が落ち着くまで待つ
await page.waitForTimeout(3000)

// A のライブラリに URL を保存し、そのデータが本人にだけ見えるかを見る
const dropUrl = page.locator('input[aria-label="URLをライブラリへ保存"]')
await dropUrl.fill('https://example.com/artist-alice-only.jpg')
await page.locator('button:has-text("保存")').first().click()

const aliceUi = await waitForFigures(1)
const aliceApi = await apiFetch('/bookmarks/')
check(
  'A のライブラリに保存される',
  aliceApi.length === 1 && aliceUi.ok,
  `api=${aliceApi.length} ui=${aliceUi.n}${aliceUi.timedOut ? ' (タイムアウト)' : ''}`
)

// --- ログアウトして、B を登録 ---
await logoutIfNeeded()
const guestUi = await waitForFigures(guestBefore)
check(
  'ログアウト後はゲストのデータ',
  guestUi.ok,
  `${guestBefore} → ${guestUi.n} 件${guestUi.timedOut ? ' (タイムアウト)' : ''}`
)

await register('Bob', `bob+${Date.now()}@example.com`)
check('ユーザーBを登録', await menuBtn().count() > 0)

const bobUi = await waitForFigures(0)
check('B はAのデータを見ない（分離）', bobUi.ok, `${bobUi.n} 件`)

// --- B のボードを確認 ---
const boards = await apiFetch('/boards/')
check(
  'B に初期ボードがある',
  Array.isArray(boards) && boards.length === 1 && boards[0].title === 'My Reference Board',
  JSON.stringify(boards)
)

// --- /auth/me が本人を返すか ---
const meAsB = await apiFetch('/auth/me')
check('/auth/me が B を返す', meAsB?.username === 'Bob', JSON.stringify(meAsB))

// --- 壊れたトークンはゲストへフォールバック ---
const badToken = await page.evaluate(async () => {
  const r = await fetch('http://127.0.0.1:8080/api/v1/auth/me', {
    headers: { Authorization: 'Bearer not-a-real-token' },
  }).then(x => x.json())
  return r.username
})
check('無効トークンはゲスト扱い', badToken === 'RefLens Studio', badToken)

console.log('\n=== 検出された問題 ===')
console.log(issues.length ? issues.map(i => '  ✗ ' + i).join('\n') : '  なし ✓')
console.log(`\ncleanup email: ${EMAIL}`)
await browser.close()