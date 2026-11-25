import { HOME_DESCRIPTION, HOME_TITLE, publicSiteUrl, SITE_NAME, SITE_URL } from './utils/siteSeo'

// https://nuxt.com/docs/api/configuration/nuxt-config
//
// 配信パスについて
//   Cloudflare Tunnel で https://art.wawa-app.me/RefLens.io/ に公開する場合は
//     NUXT_APP_BASE_URL=/RefLens.io/ npm run dev
//   として起動する（../start.sh public が設定する）。ローカル開発は既定の / のまま。
//
// apiBase / mediaBase は「バックエンドの素のオリジン+パス」のみを持ち、
// ベースパスは app.baseURL 側だけに持たせる。両方に含めると
// /RefLens.io//uploads/... という二重スラッシュになり画像が 404 になるため。
// 結合は composables/useAppConfig.ts が実行時に行う。
const appBaseURL = process.env.NUXT_APP_BASE_URL || (process.env.NODE_ENV === 'production' ? '/RefLens.io/' : '/')
const appBase = appBaseURL.endsWith('/') ? appBaseURL : `${appBaseURL}/`

export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  // ホストのDEBUG環境変数に関わらず、公開画面へ計測ログを出さない。
  debug: false,

  // 明示的に指定しておくと、Nuxtr (VS Code 拡張) がファイル生成・IntelliSense の
  // 対象ディレクトリを確実にプロジェクトルートと判定できる。
  // （Nuxt 4 は srcDir の既定値が 'app' になるため、アップグレード後も
  //   'app/' 配下へ散らばらないようにここで固定しておく）
  srcDir: '.',
  serverDir: 'server',

  // Nuxtr のステータスバーから DevTools の ON/OFF を切り替えられるようにしておく
  devtools: { enabled: true },

  modules: [
    '@pinia/nuxt',
    '@nuxtjs/tailwindcss'
  ],

  app: {
    baseURL: appBase,

    head: {
      title: HOME_TITLE,
      htmlAttrs: {
        lang: 'ja',
      },
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1, viewport-fit=cover' },
        {
          name: 'description',
          content: HOME_DESCRIPTION
        },
        { name: 'robots', content: 'index, follow, max-image-preview:large' },
        { name: 'theme-color', content: '#4338ca' },
        { name: 'google-site-verification', content: 'QEND1wFNaZp1AQkewXw8BQcRELQNfWwU_W_G9aUs5XQ' },

        // OGP
        { property: 'og:site_name', content: SITE_NAME },
        { property: 'og:type', content: 'website' },
        { property: 'og:url', content: SITE_URL },
        { property: 'og:locale', content: 'ja_JP' },
        { property: 'og:title', content: HOME_TITLE },
        {
          property: 'og:description',
          content: HOME_DESCRIPTION
        },
        { property: 'og:image', content: publicSiteUrl('card-v2.png') },
        { property: 'og:image:secure_url', content: publicSiteUrl('card-v2.png') },
        { property: 'og:image:type', content: 'image/png' },
        { property: 'og:image:width', content: '1200' },
        { property: 'og:image:height', content: '630' },
        { property: 'og:image:alt', content: 'RefLens.io のカード画像（無限キャンバスのイメージ）' },

        // Twitter Card
        { name: 'twitter:card', content: 'summary_large_image' },
        { name: 'twitter:title', content: HOME_TITLE },
        {
          name: 'twitter:description',
          content: HOME_DESCRIPTION
        },
        { name: 'twitter:url', content: SITE_URL },
        { name: 'twitter:image', content: publicSiteUrl('card-v2.png') },
        { name: 'twitter:image:alt', content: 'RefLens.io のカード画像（無限キャンバスのイメージ）' },
      ],
      link: [
        { rel: 'canonical', key: 'canonical', href: SITE_URL },
        { rel: 'sitemap', type: 'application/xml', title: 'Sitemap', href: `${appBase}sitemap.xml` },
        { rel: 'icon', type: 'image/svg+xml', href: `${appBase}favicon.svg` },
        { rel: 'icon', type: 'image/x-icon', href: `${appBase}favicon.ico` },
        { rel: 'apple-touch-icon', href: `${appBase}favicon-card.png` },
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap' }
      ]
    }
  },

tailwindcss: {
    configPath: 'tailwind.config.js',
    // cssPath は明示しない。app.vue で CSS を import する形に一本化している。
    //
    // cssPath を指定すると @nuxtjs/tailwindcss が nuxt.options.css へ挿入したうえで
    // link タグも出力するため二重登録になる。その状態で srcDir: '.' のパスが
    // Vite の module graph に入らず、raw CSS が module script として読まれて
    // "Expected a JavaScript module but got text/css" → アプリが起動しなくなる。
  },

  // グローバルCSS（Tailwind + テーマトークン）。app.vue からの import が
  // Vite の module graph を通すので、link タグは生成されない。
  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      // バックエンドの素のオリジン+パス（ベースパスは含めない）。
      // app.baseURL との結合は composables/useAppConfig.ts が実行時に行う。
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://localhost:8080/api/v1',
      mediaBase: process.env.NUXT_PUBLIC_MEDIA_BASE || 'http://localhost:8080',

      // app.baseURL をクライアントでも使えるように載せる
      appBase,
    }
  },

  // Vite dev server の Host ヘッダ検査（DNS リバインディング対策）。
  // トンネル経由だと Host が art.wawa-app.me になるため許可しておく。
  // （../start.sh public が NUXT_DEV_ALLOWED_HOSTS を設定する）
  vite: {
    server: {
      allowedHosts: process.env.NUXT_DEV_ALLOWED_HOSTS
        ? process.env.NUXT_DEV_ALLOWED_HOSTS.split(',').map(h => h.trim()).filter(Boolean)
        : undefined,
    },
  },
})
