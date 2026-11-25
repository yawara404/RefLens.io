import { defineNitroPlugin } from 'nitropack/runtime'
import { publicSiteUrl } from '../../utils/siteSeo'

const ROBOTS_TXT = `User-agent: *
Disallow: ${new URL(publicSiteUrl('api/')).pathname}

Sitemap: ${publicSiteUrl('sitemap.xml')}
`

export default defineNitroPlugin((nitroApp) => {
  nitroApp.hooks.hook('request', (event) => {
    const url = event.node.req.url?.split('?')[0]
    const res = event.node.res

    if (url === '/robots.txt') {
      res.statusCode = 200
      res.setHeader('Content-Type', 'text/plain; charset=utf-8')
      res.setHeader('Cache-Control', 'public, max-age=14400')
      res.end(ROBOTS_TXT)
    } else if (url === '/sitemap.xml') {
      const sitemapPath = new URL(publicSiteUrl('sitemap.xml')).pathname
      if (sitemapPath.startsWith(useRuntimeConfig(event).app.baseURL) && sitemapPath !== url) {
        res.statusCode = 301
        res.setHeader('Location', sitemapPath)
        res.end()
      }
    }
  })
})
