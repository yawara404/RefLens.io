<script setup lang="ts">
import { LogIn, UserPlus, Compass, Layers, Sparkles } from 'lucide-vue-next'

const emit = defineEmits<{
  (e: 'open-auth', mode?: 'login' | 'register'): void
}>()
</script>

<template>
  <div class="rounded-2xl border border-canvas-border-strong bg-canvas-panel p-4 space-y-3.5 shadow-sm text-left">
    <div class="space-y-1">
      <p class="text-[10px] font-mono font-bold text-brand uppercase tracking-wider">
        WELCOME / REFERENCE READY
      </p>
      <h2 class="text-sm font-bold text-ink">
        RefLens.io へようこそ
      </h2>
      <p class="text-[11px] text-ink-muted leading-relaxed">
        Raindrop × pixiv × PureRef。創作者のためのAI解析・参照資料ブックマーク＆無限キャンバス。
      </p>
    </div>

    <!-- 登録・ログインアクション -->
    <div class="grid grid-cols-2 gap-2">
      <button
        type="button"
        class="w-full py-2 px-2.5 rounded-xl bg-brand text-brand-fg text-xs font-bold hover:bg-brand-hover transition-colors flex items-center justify-center gap-1.5 shadow-2xs cursor-pointer"
        @click="emit('open-auth', 'register')"
      >
        <UserPlus class="w-3.5 h-3.5 shrink-0" />
        <span>新規登録</span>
      </button>
      <button
        type="button"
        class="w-full py-2 px-2.5 rounded-xl bg-canvas-card border border-canvas-border-strong hover:bg-canvas-hover text-ink text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
        @click="emit('open-auth', 'login')"
      >
        <LogIn class="w-3.5 h-3.5 shrink-0 text-ink-muted" />
        <span>ログイン</span>
      </button>
    </div>

    <!-- システムステータス (floppy.io風) -->
    <div class="pt-3 border-t border-canvas-border space-y-1.5 font-mono text-[10px]">
      <div class="text-[10px] font-bold text-ink-subtle uppercase tracking-wider">SYSTEM STATUS</div>
      <div class="flex items-center justify-between text-ink-muted">
        <span>CANVAS</span>
        <b class="text-ink font-semibold">INFINITE</b>
      </div>
      <div class="flex items-center justify-between text-ink-muted">
        <span>AI SEARCH</span>
        <b class="text-brand font-semibold">OLLAMA</b>
      </div>
      <div class="flex items-center justify-between text-ink-muted">
        <span>MODE</span>
        <b class="text-amber-500 font-semibold">DEMO</b>
      </div>
    </div>

    <div class="text-[10px] text-ink-subtle font-mono border-t border-canvas-border pt-2 text-center">
      ログインしてあなた専用の資料庫を作成
    </div>
  </div>
</template>
