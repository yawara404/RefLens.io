/** @type {import('tailwindcss').Config} */

// 配色は CSS 変数（assets/css/main.css の :root / .dark）で一元管理する。
// Tailwind のクラス名を変えずにライト/ダークを切り替えられるようにするのが目的。
const token = (name) => `var(--${name})`

export default {
  darkMode: 'class',
  content: [
    './components/**/*.{js,vue,ts}',
    './layouts/**/*.vue',
    './pages/**/*.vue',
    './plugins/**/*.{js,ts}',
    './app.vue',
    './error.vue'
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Outfit', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },

      colors: {
        // ライト/ダークで自動的に切り替わるトークン
        canvas: {
          // ページ背景（キャンバス地の最背面）
          bg: token('surface-base'),
          // パネル（ヘッダー・サイドバー・モーダル）
          panel: token('surface-panel'),
          // カード（各アイテムの枠）
          card: token('surface-card'),
          // さらに持ち上がった面（ドロップダウン・ツールチップ）
          raised: token('surface-raised'),
          // 画像プレビューを載せる地（暗め固定）
          sunken: token('surface-sunken'),
          border: token('border-subtle'),
          'border-strong': token('border-strong'),
          hover: token('surface-hover'),
        },

        // テキスト
        ink: {
          DEFAULT: token('text-primary'),
          muted: token('text-muted'),
          subtle: token('text-subtle'),
          inverted: token('text-inverted'),
        },

        // ブランド/アクセント（フラット単色。グラデーションは使わない）
        brand: {
          DEFAULT: token('accent-default'),
          hover: token('accent-hover'),
          active: token('accent-active'),
          soft: token('accent-soft'),
          fg: token('accent-fg'),
        },
        pixiv: {
          DEFAULT: '#0096fa',
          hover: '#0086df',
          soft: token('pixiv-soft'),
        },
        instagram: {
          DEFAULT: '#d9336f',
          hover: '#c02a60',
          soft: token('instagram-soft'),
        },

        // 状態色
        ok: { DEFAULT: token('success'), soft: token('success-soft') },
        warn: { DEFAULT: token('warning'), soft: token('warning-soft') },
        danger: { DEFAULT: token('danger'), soft: token('danger-soft') },

        transparent: 'transparent',
        current: 'currentColor',
        inherit: 'inherit',
      },

      boxShadow: {
        // 発光表現は廃止し、フラットな影のみ
        panel: 'var(--shadow-panel)',
        pop: 'var(--shadow-pop)',
        'canvas-item': 'var(--shadow-canvas-item)',
      },

      borderColor: {
        DEFAULT: token('border-subtle'),
      },

      ringColor: {
        DEFAULT: token('accent-default'),
      },

      borderRadius: {
        xl: '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
      },

      animation: {
        'fade-in': 'fadeIn 0.16s ease-out',
        'slide-up': 'slideUp 0.2s ease-out',
        'slide-in-right': 'slideInRight 0.24s ease-out',
        'scale-in': 'scaleIn 0.16s ease-out',
      },

      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideInRight: {
          '0%': { opacity: '0', transform: 'translateX(16px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.97)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
    },
  },
  plugins: [],
}