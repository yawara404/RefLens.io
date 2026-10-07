# RefLens.io — Frontend (Nuxt 3)

RefLens.io のフロントエンド（Nuxt 3 + Vue 3 + TypeScript + Tailwind CSS + Pinia）。
バックエンド（FastAPI）との仕様詳細はリポジトリルートの `README.md` を参照してください。

## VS Code / Nuxtr

[Nuxtr](https://marketplace.visualstudio.com/items?itemName=Nuxtr.nuxtr-vscode)（Nuxt 公式 VS Code 拡張）に対応済みです。

- `frontend/` を直接 VS Code で開く → そのまま Nuxtr が有効（`frontend/.vscode/settings.json` に設定済み）
- リポジトリルート（`RefLens.io/`）を開く → ルートの `.vscode/settings.json` の `nuxtr.monorepoMode.DirectoryName: "frontend"` により `frontend/` を Nuxt プロジェクトとして認識

```bash
npm run typecheck   # vue-tsc による型チェック
```

### ディレクトリ構成

`srcDir` に `'.'` を指定しているため、Nuxt の標準構成はそのままリポジトリ直下に置いています（Nuxtr が生成先ディレクトリを正確に判定するため）。

```
frontend/
├── app.vue          # ルートコンポーネント（NuxtPage を描画）
├── pages/           # ルーティング（/, /board/[id]）
├── components/      # canvas / panel / ui
├── composables/     # useCanvasTransform, useImageProcessor
├── stores/          # Pinia（Options Store）
├── types/           # 共通タイプ定義
├── assets/css/      # Tailwind エントリ
├── server/          # Nitro（API はバックエンド FastAPI 側）
├── public/          # 静的ファイル
└── nuxt.config.ts
```

---

# Nuxt Minimal Starter

Look at the [Nuxt documentation](https://nuxt.com/docs/getting-started/introduction) to learn more.

## Setup

Make sure to install dependencies:

```bash
# npm
npm install

# pnpm
pnpm install

# yarn
yarn install

# bun
bun install
```

## Development Server

Start the development server on `http://localhost:3000`:

```bash
# npm
npm run dev

# pnpm
pnpm dev

# yarn
yarn dev

# bun
bun run dev
```

## Production

Build the application for production:

```bash
# npm
npm run build

# pnpm
pnpm build

# yarn
yarn build

# bun
bun run build
```

Locally preview production build:

```bash
# npm
npm run preview

# pnpm
pnpm preview

# yarn
yarn preview

# bun
bun run preview
```

Check out the [deployment documentation](https://nuxt.com/docs/getting-started/deployment) for more information.
