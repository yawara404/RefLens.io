import { defineNitroPlugin } from 'nitropack/runtime'

const ROBOTS_TXT = `# RefLens.io robots.txt
# https://art.wawa-app.me/RefLens.io/
#
# クロール方針:
# - 公開画面 (Manager, Canvas, Pixiv View, このサイトについて, 利用上の注意, プライバシーポリシー) を許可
# - 内部API (/RefLens.io/api/*) と個人管理ページ (/RefLens.io/account) は検索インデックスから除外
# - 静的アセット (/RefLens.io/_nuxt/*) はレンダリングに必要なためブロックしない

User-agent: *
Allow: /RefLens.io/
Allow: /RefLens.io/canvas
Allow: /RefLens.io/view
Allow: /RefLens.io/about
Allow: /RefLens.io/terms
Allow: /RefLens.io/privacy
Disallow: /RefLens.io/api/
Disallow: /RefLens.io/account

Sitemap: https://art.wawa-app.me/RefLens.io/sitemap.xml
`

const SITEMAP_XML = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  <!-- RefLens.io ホーム / Manager -->
  <url>
    <loc>https://art.wawa-app.me/RefLens.io/</loc>
    <lastmod>2026-11-05</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
    <image:image>
      <image:loc>https://art.wawa-app.me/RefLens.io/favicon-card.png</image:loc>
      <image:title>RefLens.io - Smart Infinite Canvas for Artists</image:title>
      <image:caption>Raindrop × pixiv × PureRef。イラストレーター・創作者のためのAI解析・参照資料ブックマーク＆無限キャンバス</image:caption>
    </image:image>
  </url>

  <!-- 無限キャンバス -->
  <url>
    <loc>https://art.wawa-app.me/RefLens.io/canvas</loc>
    <lastmod>2026-11-05</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>

  <!-- Pixiv ビューワー -->
  <url>
    <loc>https://art.wawa-app.me/RefLens.io/view</loc>
    <lastmod>2026-11-05</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>

  <!-- このサイトについて -->
  <url>
    <loc>https://art.wawa-app.me/RefLens.io/about</loc>
    <lastmod>2026-11-05</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>

  <!-- 利用上の注意 -->
  <url>
    <loc>https://art.wawa-app.me/RefLens.io/terms</loc>
    <lastmod>2026-11-05</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.3</priority>
  </url>

  <!-- プライバシーポリシー -->
  <url>
    <loc>https://art.wawa-app.me/RefLens.io/privacy</loc>
    <lastmod>2026-11-05</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.3</priority>
  </url>
</urlset>
`

export default defineNitroPlugin((nitroApp) => {
  nitroApp.hooks.hook('request', async (event) => {
    const url = event.node.req.url?.split('?')[0]
    // ホスト直下の /robots.txt
    if (url === '/robots.txt') {
      event.node.res.statusCode = 200
      event.node.res.setHeader('Content-Type', 'text/plain; charset=utf-8')
      event.node.res.setHeader('Cache-Control', 'public, max-age=14400')
      event.node.res.end(ROBOTS_TXT)
      event.handled = true
    }
    // ホスト直下の /sitemap.xml
    else if (url === '/sitemap.xml') {
      event.node.res.statusCode = 200
      event.node.res.setHeader('Content-Type', 'application/xml; charset=utf-8')
      event.node.res.setHeader('Cache-Control', 'public, max-age=14400')
      event.node.res.end(SITEMAP_XML)
      event.handled = true
    }
  })
})

