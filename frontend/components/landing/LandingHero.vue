<script setup lang="ts">
import { computed } from 'vue'
import {
  Compass,
  Layers,
  Bookmark,
  Sparkles,
  ArrowRight,
  LogIn,
  UserPlus,
  Eye,
  CheckCircle2,
  Palette,
  Search,
  FolderOpen
} from 'lucide-vue-next'

const emit = defineEmits<{
  (e: 'explore-demo'): void
  (e: 'open-auth', mode?: 'login' | 'register'): void
}>()

function openRegister() {
  emit('open-auth', 'register')
}

function openLogin() {
  emit('open-auth', 'login')
}

function startDemo() {
  emit('explore-demo')
}
</script>

<template>
  <div class="w-full max-w-5xl mx-auto space-y-6 sm:space-y-8 py-2 sm:py-4">
    <!-- メインヒーローカード (floppy.io風のレトロモダンな額縁スタイル) -->
    <section
      class="relative rounded-2xl border-2 border-canvas-border-strong bg-canvas-panel p-5 sm:p-8 md:p-10 shadow-pop overflow-hidden"
      aria-labelledby="hero-main-title"
    >
      <!-- 背景装飾グリッドとアクセント -->
      <div class="absolute inset-0 bg-[radial-gradient(#6366f1_1px,transparent_1px)] [background-size:16px_16px] opacity-[0.04] pointer-events-none" />
      <div class="absolute -top-24 -right-24 w-80 h-80 rounded-full bg-brand/10 blur-3xl pointer-events-none" />

      <div class="relative grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8 items-center">
        <!-- 左側コピー -->
        <div class="lg:col-span-7 space-y-4 sm:space-y-5">
          <div class="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-brand/10 border border-brand/25 text-brand text-[11px] font-bold tracking-wider uppercase">
            <span class="w-2 h-2 rounded-full bg-brand animate-ping shrink-0" />
            <span>RefLens Archive &amp; Infinite Canvas</span>
          </div>

          <div class="space-y-1">
            <h1 id="hero-main-title" class="text-2xl sm:text-3xl md:text-4xl font-extrabold text-ink tracking-tight leading-tight">
              描く人のための、<br class="hidden sm:inline">
              <span class="text-brand underline decoration-brand/30 underline-offset-6">無限の資料庫。</span>
            </h1>
          </div>

          <p class="text-xs sm:text-sm text-ink-muted leading-relaxed max-w-xl">
            Raindrop × pixiv × PureRef。Web画像、pixivイラスト、手持ちの設定資料を1枚の無限キャンバスに自由配置。<strong class="text-ink font-semibold">Ollama AI</strong> がタグの有無に関係なく被写体・色彩・構図を自動認識します。
          </p>

          <!-- アクションボタン -->
          <div class="flex flex-wrap items-center gap-2.5 sm:gap-3 pt-2">
            <button
              type="button"
              class="px-5 py-2.5 rounded-xl bg-brand hover:bg-brand-hover text-brand-fg text-xs sm:text-sm font-bold shadow-md hover:shadow-lg transition-all flex items-center gap-2 group cursor-pointer"
              @click="openRegister"
            >
              <UserPlus class="w-4 h-4" />
              <span>アカウントを作る</span>
              <ArrowRight class="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
            </button>

            <button
              type="button"
              class="px-4 py-2.5 rounded-xl bg-canvas-card hover:bg-canvas-hover text-ink border border-canvas-border-strong text-xs sm:text-sm font-bold transition-all flex items-center gap-2 cursor-pointer shadow-2xs"
              @click="startDemo"
            >
              <Eye class="w-4 h-4 text-brand" />
              <span>デモを体験する</span>
            </button>

            <button
              type="button"
              class="px-3 py-2.5 rounded-xl text-ink-muted hover:text-ink text-xs font-semibold transition-colors flex items-center gap-1.5 cursor-pointer ml-auto sm:ml-0"
              @click="openLogin"
            >
              <LogIn class="w-3.5 h-3.5" />
              <span>ログイン</span>
            </button>
          </div>

          <!-- メトリクスフッター (floppy風のステータス) -->
          <div class="pt-4 border-t border-canvas-border grid grid-cols-3 gap-2 text-left font-mono">
            <div>
              <span class="text-[10px] text-ink-subtle uppercase block">Canvas</span>
              <span class="text-xs font-bold text-ink">INFINITE</span>
            </div>
            <div>
              <span class="text-[10px] text-ink-subtle uppercase block">AI Search</span>
              <span class="text-xs font-bold text-brand">OLLAMA</span>
            </div>
            <div>
              <span class="text-[10px] text-ink-subtle uppercase block">Prediction</span>
              <span class="text-xs font-bold text-ink">0 ms</span>
            </div>
          </div>
        </div>

        <!-- 右側ビジュアルダイアグラム (floppy.io風の枠線グラフィクス) -->
        <div class="lg:col-span-5 flex justify-center">
          <div class="w-full max-w-sm rounded-xl border-2 border-canvas-border-strong bg-canvas-card p-4 shadow-sm relative space-y-3">
            <div class="flex items-center justify-between text-[10px] font-mono border-b border-canvas-border pb-2 text-ink-subtle">
              <span>[READY] REFLENS_CANVAS_01</span>
              <span class="text-brand font-bold">ONLINE</span>
            </div>

            <!-- キャンバスのミニチュアイラスト -->
            <div class="aspect-4/3 rounded-lg bg-canvas-sunken border border-canvas-border relative overflow-hidden p-2 flex flex-col justify-between">
              <!-- グリッド背景 -->
              <div class="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:12px_12px]" />

              <!-- サンプルリファレンスカード1 -->
              <div class="relative w-28 p-1.5 rounded-md bg-canvas-panel border border-brand shadow-xs space-y-1 transform -rotate-2">
                <div class="w-full h-14 rounded bg-brand/10 border border-brand/20 flex items-center justify-center text-[9px] font-bold text-brand">
                  1girl / Pose
                </div>
                <div class="flex items-center justify-between text-[8px] text-ink-subtle">
                  <span>#立ち絵</span>
                  <span class="w-1.5 h-1.5 rounded-full bg-brand" />
                </div>
              </div>

              <!-- サンプルリファレンスカード2 (重なり) -->
              <div class="relative self-end w-32 p-1.5 rounded-md bg-canvas-panel border border-canvas-border-strong shadow-xs space-y-1 transform rotate-3 -mt-6">
                <div class="w-full h-12 rounded bg-pixiv/10 border border-pixiv/20 flex items-center justify-center text-[9px] font-bold text-pixiv">
                  Lighting &amp; Color
                </div>
                <div class="flex items-center gap-1">
                  <span class="w-2 h-2 rounded-full bg-[#38bdf8]" />
                  <span class="w-2 h-2 rounded-full bg-[#f43f5e]" />
                  <span class="w-2 h-2 rounded-full bg-[#fbbf24]" />
                  <span class="text-[8px] font-mono text-ink-subtle ml-auto">pixiv</span>
                </div>
              </div>

              <!-- AI検知オーバーレイバッジ -->
              <div class="relative z-10 self-start px-2 py-0.5 rounded-full bg-brand text-brand-fg text-[9px] font-bold flex items-center gap-1 shadow-xs">
                <Sparkles class="w-2.5 h-2.5" />
                <span>Ollama AI: 「女の子」「水着」</span>
              </div>
            </div>

            <div class="flex items-center justify-between text-[10px] text-ink-muted pt-1">
              <span class="flex items-center gap-1">
                <Compass class="w-3 h-3 text-brand" />
                PureRef Like Controls
              </span>
              <span class="font-mono text-ink-subtle">NO LIMITS</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 下部 3 つのフィーチャーカード (floppy.io の 01 / 02 / 03 相当) -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-3.5 sm:gap-4" aria-label="RefLens.io の主な機能">
      <!-- 01 / INFINITE CANVAS -->
      <div class="rounded-2xl border border-canvas-border bg-canvas-panel p-4 sm:p-5 flex flex-col justify-between shadow-2xs hover:border-brand/40 transition-colors">
        <div class="space-y-2">
          <div class="flex items-center justify-between border-b border-canvas-border pb-2">
            <span class="text-[10px] font-mono font-bold text-brand uppercase tracking-wider">01 / CANVAS</span>
            <span class="text-[10px] font-mono text-ink-subtle">INFINITE</span>
          </div>
          <h2 class="text-sm sm:text-base font-bold text-ink flex items-center gap-1.5">
            <Layers class="w-4 h-4 text-brand shrink-0" />
            <span>PureRef風の無限キャンバス。</span>
          </h2>
          <p class="text-xs text-ink-muted leading-relaxed">
            自由な拡大縮小・回転・配置・パレット抽出。描画作業中も見失わない、クリエイター専用のワークスペースです。
          </p>
        </div>
        <div class="pt-3 mt-3 border-t border-canvas-border flex items-center justify-between text-[10px] font-mono text-ink-subtle">
          <span>UNLIMITED VIEWPORT</span>
          <span class="text-ink font-semibold">100% ZOOM</span>
        </div>
      </div>

      <!-- 02 / SMART STOCK -->
      <div class="rounded-2xl border border-canvas-border bg-canvas-panel p-4 sm:p-5 flex flex-col justify-between shadow-2xs hover:border-brand/40 transition-colors">
        <div class="space-y-2">
          <div class="flex items-center justify-between border-b border-canvas-border pb-2">
            <span class="text-[10px] font-mono font-bold text-pixiv uppercase tracking-wider">02 / STOCK</span>
            <span class="text-[10px] font-mono text-ink-subtle">DROP &amp; STASH</span>
          </div>
          <h2 class="text-sm sm:text-base font-bold text-ink flex items-center gap-1.5">
            <Bookmark class="w-4 h-4 text-pixiv shrink-0" />
            <span>pixiv・Webから1クリック保存。</span>
          </h2>
          <p class="text-xs text-ink-muted leading-relaxed">
            URLを貼るか画像をドロップするだけ。フォルダカラーやタグ付けで、思考を止めずにインスピレーションをストック。
          </p>
        </div>
        <div class="pt-3 mt-3 border-t border-canvas-border flex items-center justify-between text-[10px] font-mono text-ink-subtle">
          <span>PIXIV x WEB x LOCAL</span>
          <span class="text-ink font-semibold">FAST STASH</span>
        </div>
      </div>

      <!-- 03 / OLLAMA AI -->
      <div class="rounded-2xl border border-canvas-border bg-canvas-panel p-4 sm:p-5 flex flex-col justify-between shadow-2xs hover:border-brand/40 transition-colors">
        <div class="space-y-2">
          <div class="flex items-center justify-between border-b border-canvas-border pb-2">
            <span class="text-[10px] font-mono font-bold text-brand uppercase tracking-wider">03 / AI VISION</span>
            <span class="text-[10px] font-mono text-ink-subtle">OLLAMA</span>
          </div>
          <h2 class="text-sm sm:text-base font-bold text-ink flex items-center gap-1.5">
            <Sparkles class="w-4 h-4 text-brand shrink-0" />
            <span>タグなしでも被写体をAI認識。</span>
          </h2>
          <p class="text-xs text-ink-muted leading-relaxed">
            「女の子」「水着」「猫」など自然な言葉で瞬時に検索サジェスト。タグ付けの手間なく探したい資料がすぐ見つかります。
          </p>
        </div>
        <div class="pt-3 mt-3 border-t border-canvas-border flex items-center justify-between text-[10px] font-mono text-ink-subtle">
          <span>ZERO-TAG SEARCH</span>
          <span class="text-brand font-semibold">PREDICTIVE</span>
        </div>
      </div>
    </section>
  </div>
</template>
