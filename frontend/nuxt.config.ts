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
const appBaseURL = process.env.NUXT_APP_BASE_URL || '/'
const appBase = appBaseURL.endsWith('/') ? appBaseURL : `${appBaseURL}/`

export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',

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
      title: 'RefLens.io - Smart Infinite Canvas for Artists',
      htmlAttrs: {
        lang: 'ja',
      },
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        {
          name: 'description',
          content: 'PureRef-inspired infinite reference canvas powered by Multimodal AI visual anatomy analysis & pixiv integration.'
        }
      ],
      link: [
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