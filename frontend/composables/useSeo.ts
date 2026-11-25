import { toValue, type MaybeRefOrGetter } from 'vue'
import { publicSiteUrl, SITE_NAME } from '~/utils/siteSeo'

export interface PageSeo {
  /** ページ固有のタイトル（サイト名を含めた完成形を渡す） */
  title: string
  description: string
  /** app.baseURL を含めないパス。例: '/view' */
  path: string
  /** 1200x630 のカード画像（絶対URL・サイト内パスのどちらでも可） */
  image?: string
  type?: 'website' | 'article'
  noindex?: boolean
}

const SITE_LOCALE = 'ja_JP'
const DEFAULT_IMAGE = '/card-v2.png'
const IMAGE_WIDTH = '1200'
const IMAGE_HEIGHT = '630'

/**
 * ページ単位の SEO / OGP をまとめて設定する。
 *
 * floppy.io と同じく「1200×630 のカード画像 + summary_large_image」を基本形にし、
 * og:url / canonical / twitter:* をページごとに揃える。
 * Nuxt は SSR で HTML に meta を出力するため、JS を実行しないクローラーにも内容が届く。
 */
export function useSeo(options: MaybeRefOrGetter<PageSeo>) {
  useHead(() => {
    const seo = toValue(options)
    const url = publicSiteUrl(seo.path)
    const image = publicSiteUrl(seo.image || DEFAULT_IMAGE)
    const description = seo.description
    const imageAlt = `${seo.title} のカード画像`
    const robots = seo.noindex
      ? 'noindex, nofollow'
      : 'index, follow, max-image-preview:large'

    return {
      title: seo.title,
      link: [{ rel: 'canonical', key: 'canonical', href: url }],
      meta: [
        { key: 'description', name: 'description', content: description },
        { key: 'robots', name: 'robots', content: robots },

        { key: 'og:site_name', property: 'og:site_name', content: SITE_NAME },
        { key: 'og:type', property: 'og:type', content: seo.type || 'website' },
        { key: 'og:locale', property: 'og:locale', content: SITE_LOCALE },
        { key: 'og:title', property: 'og:title', content: seo.title },
        { key: 'og:description', property: 'og:description', content: description },
        { key: 'og:url', property: 'og:url', content: url },
        { key: 'og:image', property: 'og:image', content: image },
        { key: 'og:image:secure_url', property: 'og:image:secure_url', content: image },
        { key: 'og:image:type', property: 'og:image:type', content: 'image/png' },
        { key: 'og:image:width', property: 'og:image:width', content: IMAGE_WIDTH },
        { key: 'og:image:height', property: 'og:image:height', content: IMAGE_HEIGHT },
        { key: 'og:image:alt', property: 'og:image:alt', content: imageAlt },

        { key: 'twitter:card', name: 'twitter:card', content: 'summary_large_image' },
        { key: 'twitter:title', name: 'twitter:title', content: seo.title },
        { key: 'twitter:description', name: 'twitter:description', content: description },
        { key: 'twitter:url', name: 'twitter:url', content: url },
        { key: 'twitter:image', name: 'twitter:image', content: image },
        { key: 'twitter:image:alt', name: 'twitter:image:alt', content: imageAlt },
      ],
    }
  })
}
