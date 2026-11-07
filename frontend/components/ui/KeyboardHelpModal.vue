<script setup lang="ts">
import { computed } from 'vue'
import { X, Keyboard, MousePointer2, Hand, Layers, Wand2, ZoomIn, HelpCircle } from 'lucide-vue-next'
import { useHelpStore } from '~/stores/helpStore'
import { useDialogA11y } from '~/composables/useDialogA11y'

const helpStore = useHelpStore()

// モーダル共通のキーボード操作とフォーカス管理。
const { dialogRef } = useDialogA11y(computed(() => helpStore.isOpen), () => helpStore.close())

interface ShortcutGroup {
  title: string
  icon: any
  items: { keys: string[]; label: string }[]
}

const GROUPS: ShortcutGroup[] = [
  {
    title: 'キャンバス操作',
    icon: Hand,
    items: [
      { keys: ['Space', '+ ドラッグ'], label: 'キャンバスをパン（移動）' },
      { keys: ['ホイール', '2本指スクロール'], label: 'パン' },
      { keys: ['Cmd', '+ ホイール'], label: 'カーソル位置を中心にズーム' },
      { keys: ['+', '/ -'], label: 'ズームイン / ズームアウト' },
      { keys: ['Cmd/Ctrl', '+ 0'], label: 'ズームを100%に戻す' },
      { keys: ['ダブルクリック'], label: 'その資料に拡大フォーカス' },
    ],
  },
  {
    title: '選択と編集',
    icon: MousePointer2,
    items: [
      { keys: ['クリック'], label: 'アイテムを選択' },
      { keys: ['Shift', '+ クリック'], label: '複数選択の追加 / 解除' },
      { keys: ['Shift', '+ 空地をドラッグ'], label: '矩形選択' },
      { keys: ['↑↓←→'], label: '選択アイテムを1px移動（Shiftで10px）' },
      { keys: ['Cmd/Ctrl', '+ A'], label: 'すべて選択' },
      { keys: ['Esc'], label: '選択解除 / パネルを閉じる' },
      { keys: ['Delete'], label: '選択中のアイテムを削除' },
    ],
  },
  {
    title: '画像の変形・重なり順',
    icon: Layers,
    items: [
      { keys: ['H'], label: '左右反転（デッサンの確認）' },
      { keys: ['V'], label: '上下反転' },
      { keys: ['G'], label: 'グレースケール（バリュースタディ）' },
      { keys: ['R'], label: '90°回転' },
      { keys: ['[', '/ ]'], label: '背面へ移動 / 前面へ移動' },
      { keys: ['角ハンドル'], label: 'サイズ変更（縦横比は維持）' },
      { keys: ['上部ハンドル'], label: '回転（Shift で15°スナップ）' },
    ],
  },
  {
    title: '取り込みと整理',
    icon: Wand2,
    items: [
      { keys: ['Cmd/Ctrl', '+ V'], label: 'クリップボードから画像を追加' },
      { keys: ['Cmd/Ctrl', '+ Z'], label: '元に戻す（Undo）' },
      { keys: ['Cmd', '+ Shift', '+ Z'], label: 'やり直し（Redo）' },
      { keys: ['B'], label: '資料ライブラリ（Library）を開閉' },
      { keys: ['I'], label: 'AI 解析パネルを開閉' },
      { keys: ['F'], label: '全アイテムを画面にフィット' },
      { keys: ['←', '/ →'], label: 'クイックルックで前後の資料へ移動' },
    ],
  },
  {
    title: '検索・表示',
    icon: ZoomIn,
    items: [
      { keys: ['/'], label: '現在のページの検索欄にフォーカス' },
      { keys: ['D'], label: 'ライト / ダークテーマを切り替え' },
      { keys: ['?'], label: 'このショートカット一覧を表示' },
    ],
  },
]

const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent)

</script>

<template>
  <Teleport to="body">
    <div
      v-if="helpStore.isOpen"
      class="fixed inset-0 z-[80] flex items-start justify-center overflow-y-auto scrim p-4 md:p-8 animate-fade-in"
      @click.self="helpStore.close()"
    >
      <div
        class="w-full max-w-4xl rounded-2xl border border-canvas-border bg-canvas-panel shadow-pop animate-scale-in"
        ref="dialogRef" role="dialog"
        aria-modal="true"
        aria-label="キーボードショートカット一覧"
      >
        <!-- ヘッダー -->
        <div class="flex items-center justify-between px-5 py-4 border-b border-canvas-border">
          <div class="flex items-center gap-2.5">
            <div class="p-1.5 rounded-lg bg-brand-soft text-brand">
              <Keyboard class="w-4 h-4" />
            </div>
            <div>
              <h2 class="text-sm font-semibold text-ink">キーボードショートカット</h2>
              <p class="text-[11px] text-ink-subtle">
                {{ isMac ? '⌘ は Ctrl と同じ動作です' : 'Ctrl と同時押しで操作します' }}
              </p>
            </div>
          </div>
          <button
            class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
            aria-label="閉じる"
            @click="helpStore.close()"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <!-- ショートカット一覧 -->
        <div class="px-5 py-5 grid gap-4 md:grid-cols-2">
          <section
            v-for="group in GROUPS"
            :key="group.title"
            class="rounded-xl border border-canvas-border bg-canvas-card p-3.5"
          >
            <h3 class="flex items-center gap-1.5 text-xs font-semibold text-ink mb-2.5">
              <component :is="group.icon" class="w-3.5 h-3.5 text-brand" />
              {{ group.title }}
            </h3>
            <ul class="space-y-1.5">
              <li
                v-for="item in group.items"
                :key="item.label"
                class="flex items-center gap-2 text-[11px] leading-relaxed"
              >
                <span class="flex items-center gap-1 shrink-0">
                  <kbd
                    v-for="key in item.keys"
                    :key="key"
                    class="px-1.5 py-0.5 rounded border border-canvas-border-strong bg-canvas-raised font-mono text-[10px] text-ink whitespace-nowrap"
                  >
                    {{ key }}
                  </kbd>
                </span>
                <span class="text-ink-muted">{{ item.label }}</span>
              </li>
            </ul>
          </section>
        </div>

        <!-- 補足 & 総合マニュアルへのリンク -->
        <div class="px-5 pb-5 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <div class="rounded-xl border border-canvas-border bg-canvas-card px-4 py-2.5 text-[11px] text-ink-muted leading-relaxed flex-1">
            <span class="font-semibold text-ink">ヒント: </span>
            <span>文字入力中やダイアログ表示中はショートカットは無効になります。「+」表記はキーを押しながら次のキーを押す操作です。</span>
          </div>
          <NuxtLink
            to="/help"
            class="px-3.5 py-2 rounded-xl text-xs font-bold bg-brand text-brand-fg hover:bg-brand-hover transition-colors flex items-center justify-center gap-1.5 shrink-0 shadow-sm"
            @click="helpStore.close()"
          >
            <HelpCircle class="w-3.5 h-3.5" />
            <span>詳しい使い方・操作ガイドを見る</span>
          </NuxtLink>
        </div>
      </div>
    </div>
  </Teleport>
</template>
