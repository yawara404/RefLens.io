import { chromium } from 'playwright-core'

// モバイル表示の実機チェック（はみ出し・見切れ・スクロール可否）。
//   BASE=http://localhost:3000 TOKEN=<jwt> node scripts/diag-mobile.mjs
//   （TOKEN は画像入りのライブラリで確認したい場合のみ指定）
// スクリーンショットは /tmp/mobile-<width>-*.png に出力する。
const EXEC = process.env.CHROME_PATH
const BASE = process.env.BASE || 'http://localhost:3000'
const TOKEN = process.env.TOKEN || ''
const SIZES = (process.env.SIZES || '390x844,360x740,320x568,844x390')
  .split(',')
  .map(size => size.split('x').map(Number))

// 確認するルート（カンマ区切り）。Manager 固有の検査は route === '/' のときだけ行う。
const ROUTES = (process.env.ROUTES || '/')
  .split(',')
  .map(route => route.trim())
  .filter(Boolean)

const TARGETS = SIZES.flatMap(size => ROUTES.map(route => ({ width: size[0], height: size[1], route })))

const browser = await chromium.launch(EXEC ? { executablePath: EXEC, headless: true } : { channel: 'chrome', headless: true })

const issues = []

function check(label, ok, detail = '') {
  console.log(`=== ${label} === ${ok ? 'OK' : 'NG'}${detail ? ` (${detail})` : ''}`)
  if (!ok) issues.push(label)
}

for (const { width, height, route } of TARGETS) {
  const suffix = route === '/' ? '' : `-${route.replace(/\//g, '-').replace(/^-/, '')}`
  const context = await browser.newContext({
    viewport: { width, height },
    isMobile: true,
    hasTouch: true,
    deviceScaleFactor: 2,
  })
  if (TOKEN) {
    await context.addInitScript(token => {
      try {
        localStorage.setItem('reflens-auth-token', token)
      } catch {
        /* ignore */
      }
    }, TOKEN)
  }

  const page = await context.newPage()
  const logs = []
  page.on('pageerror', e => logs.push(`[pageerror] ${e.message}`))
  page.on('console', m => {
    if (m.type() === 'error' && !m.text().includes('fonts.g')) logs.push(`[console] ${m.text()}`)
  })

  await page.goto(`${BASE}${route}`, { waitUntil: 'networkidle', timeout: 60000 })
  await page.waitForTimeout(2500)

  console.log(`\n### viewport ${width}x${height} route=${route}`)

  const layout = await page.evaluate(() => {
    const vw = window.innerWidth
    // 横スクロール可能なコンテナ内は「はみ出し」ではなく意図したスクロールなので除外する
    const insideHorizontalScroller = (el) => {
      for (let node = el.parentElement; node && node !== document.body; node = node.parentElement) {
        const style = getComputedStyle(node)
        if ((style.overflowX === 'auto' || style.overflowX === 'scroll') && node.scrollWidth > node.clientWidth) return true
      }
      return false
    }
    const offenders = []
    for (const el of document.querySelectorAll('body *')) {
      const style = getComputedStyle(el)
      if (style.display === 'none' || style.visibility === 'hidden' || style.position === 'fixed') continue
      const rect = el.getBoundingClientRect()
      if (rect.width === 0 || rect.height === 0) continue
      if (rect.right > vw + 1 || rect.left < -1) {
        if (insideHorizontalScroller(el)) continue
        offenders.push({
          tag: el.tagName.toLowerCase(),
          cls: (typeof el.className === 'string' ? el.className : '').slice(0, 70),
          text: (el.textContent || '').trim().slice(0, 24),
          left: Math.round(rect.left),
          right: Math.round(rect.right),
        })
      }
    }
    const main = document.querySelector('#main-content')
    return {
      vw,
      docScrollWidth: document.documentElement.scrollWidth,
      main: main
        ? {
            clientWidth: main.clientWidth,
            scrollWidth: main.scrollWidth,
            clientHeight: main.clientHeight,
            scrollHeight: main.scrollHeight,
          }
        : null,
      offenderCount: offenders.length,
      offenders: offenders.slice(0, 12),
    }
  })

  console.log(`doc scrollWidth=${layout.docScrollWidth} / vw=${layout.vw}`)
  console.log(`main: ${JSON.stringify(layout.main)}`)
  console.log(`はみ出し要素: ${layout.offenderCount}`)
  for (const o of layout.offenders) console.log(`  - <${o.tag}> ${o.left}..${o.right} "${o.text}" ${o.cls}`)

  check(`[${width}] 横スクロールが出ない`, layout.docScrollWidth <= layout.vw)
  check(`[${width}] はみ出し要素なし`, layout.offenderCount === 0)

  // 100vh ではなく dvh が効いているか（iOS での下端見切れ対策）
  const rootInfo = await page.evaluate(() => {
    const root = document.querySelector('.h-app-screen')
    return {
      found: !!root,
      height: root ? Math.round(root.getBoundingClientRect().height) : null,
      innerHeight: window.innerHeight,
      legacyHScreenCount: document.querySelectorAll('.h-screen').length,
      classes: root ? root.className : '',
    }
  })
  check(
    `[${width}] 画面高さが dvh 基準（h-screen を使っていない）`,
    rootInfo.legacyHScreenCount === 0
      && (!rootInfo.found || Math.abs((rootInfo.height || 0) - rootInfo.innerHeight) <= 1),
    JSON.stringify(rootInfo)
  )

  await page.screenshot({ path: `/tmp/mobile-${width}${suffix}-home.png` })

  // ここから先は Manager（/）固有の検査
  if (route !== '/') {
    check(`[${width}] コンソールエラーなし`, logs.length === 0, logs.slice(0, 3).join(' / '))
    await context.close()
    continue
  }

  // メイン領域を最下部までスクロールしたとき、最後のカードが完全に見えるか
  const scrollInfo = await page.evaluate(async () => {
    const main = document.querySelector('#main-content')
    if (!main) return null
    main.scrollTop = main.scrollHeight
    await new Promise(r => setTimeout(r, 350))
    const mainRect = main.getBoundingClientRect()
    const cards = [...main.querySelectorAll('figure')]
    const last = cards[cards.length - 1]
    return {
      scrollTop: Math.round(main.scrollTop),
      maxScroll: Math.round(main.scrollHeight - main.clientHeight),
      lastCardBottom: last ? Math.round(last.getBoundingClientRect().bottom) : null,
      mainBottom: Math.round(mainRect.bottom),
      cardCount: cards.length,
    }
  })
  check(`[${width}] メインを最下部までスクロールできる`, !!scrollInfo && scrollInfo.scrollTop >= scrollInfo.maxScroll - 2, JSON.stringify(scrollInfo))
  check(
    `[${width}] 最下部のカードが見切れない`,
    !!scrollInfo && (scrollInfo.lastCardBottom === null || scrollInfo.lastCardBottom <= scrollInfo.mainBottom + 1),
    scrollInfo ? `cardBottom=${scrollInfo.lastCardBottom} / mainBottom=${scrollInfo.mainBottom}` : ''
  )
  await page.screenshot({ path: `/tmp/mobile-${width}-bottom.png` })

  // ハンバーガーメニュー（サイドバードロワー）。md 以上は常時表示なので対象外
  if (width < 768) {
    await page.evaluate(() => document.querySelector('#main-content')?.scrollTo({ top: 0 }))
    await page.locator('header button[aria-label="メニューを開く"]').click()
    await page.waitForTimeout(600)
    const drawer = await page.evaluate(() => {
      const el = document.querySelector('#manager-sidebar')
      if (!el) return null
      const rect = el.getBoundingClientRect()
      const style = getComputedStyle(el)
      return {
        top: Math.round(rect.top),
        bottom: Math.round(rect.bottom),
        height: Math.round(rect.height),
        viewportHeight: window.innerHeight,
        overflowY: style.overflowY,
        scrollHeight: el.scrollHeight,
        clientHeight: el.clientHeight,
      }
    })
    console.log(`drawer: ${JSON.stringify(drawer)}`)
    check(`[${width}] ドロワーが画面内に収まる`, !!drawer && drawer.bottom <= drawer.viewportHeight + 1 && drawer.top >= 0)
    check(`[${width}] ドロワー内をスクロールできる`, !!drawer && (drawer.scrollHeight <= drawer.clientHeight || drawer.overflowY === 'auto' || drawer.overflowY === 'scroll'), drawer ? `${drawer.scrollHeight}/${drawer.clientHeight}` : '')
    await page.screenshot({ path: `/tmp/mobile-${width}-drawer.png` })

    const drawerBottom = await page.evaluate(async () => {
      const el = document.querySelector('#manager-sidebar')
      if (!el) return null
      el.scrollTop = el.scrollHeight
      await new Promise(r => setTimeout(r, 300))
      const rect = el.getBoundingClientRect()
      const rows = [...el.querySelectorAll('[role="button"]')]
      const last = rows[rows.length - 1]
      return {
        scrollTop: Math.round(el.scrollTop),
        maxScroll: Math.round(el.scrollHeight - el.clientHeight),
        lastRowBottom: last ? Math.round(last.getBoundingClientRect().bottom) : null,
        drawerBottom: Math.round(rect.bottom),
      }
    })
    check(`[${width}] ドロワー最下行まで見られる`, !!drawerBottom && (drawerBottom.maxScroll === 0 || drawerBottom.scrollTop >= drawerBottom.maxScroll - 2), JSON.stringify(drawerBottom))
    check(
      `[${width}] ドロワー最下行が見切れない`,
      !!drawerBottom && (drawerBottom.lastRowBottom === null || drawerBottom.lastRowBottom <= drawerBottom.drawerBottom + 1),
      drawerBottom ? `rowBottom=${drawerBottom.lastRowBottom} / drawerBottom=${drawerBottom.drawerBottom}` : ''
    )
    await page.screenshot({ path: `/tmp/mobile-${width}-drawer-bottom.png` })
  }

  check(`[${width}] コンソールエラーなし`, logs.length === 0, logs.slice(0, 3).join(' / '))

  await context.close()
}

await browser.close()
console.log(issues.length ? `\nNG: ${issues.join(', ')}` : '\nすべて OK')
process.exit(issues.length ? 1 : 0)
