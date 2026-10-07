<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { X, Keyboard, MousePointer2, Hand, Layers, Wand2, ZoomIn } from 'lucide-vue-next'
import { useHelpStore } from '~/stores/helpStore'

const helpStore = useHelpStore()

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
      { keys: ['ピンチ'], label: 'ズーム（タッチデバイス）' },
      { keys: ['2本指ドラッグ'], label: 'パン（タッチデバイス）' },
      { keys: ['Cmd/Ctrl', '+ 0'], label: 'ズームを100%に戻す' },
    ],
  },
  {
    title: '選択と編集',
    icon: MousePointer2,
    items: [
      { keys: ['クリック'], label: 'アイテムを選択' },
      { keys: ['Shift', '+ クリック'], label: '複数選択の追加 / 解除' },
      { keys: ['空地をドラッグ'], label: '矩形選択' },
      { keys: ['Cmd/Ctrl', '+ A'], label: 'すべて選択' },
      { keys: ['Esc'], label: '選択解除 / パネルを閉じる' },
      { keys: ['Delete'], label: '選択中のアイテムを削除' },
    ],
  },
  {
    title: '画像の変形',
    icon: Layers,
    items: [
      { keys: ['H'], label: '左右反転（デッサンの確認）' },
      { keys: ['V'], label: '上下反転' },
      { keys: ['G'], label: 'グレースケール（バリュースタディ）' },
      { keys: ['R'], label: '90°回転' },
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
      { keys: ['ドラッグ&ドロップ'], label: '画像をキャンバスへ配置' },
    ],
  },
  {
    title: '表示',
    icon: ZoomIn,
    items: [
      { keys: ['D'], label: 'ライト / ダークテーマを切り替え' },
      { keys: ['?'], label: 'このショートカット一覧を表示' },
    ],
  },
]

const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent)

function onKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    e.preventDefault()
    helpStore.close()
  }
}

onMounted(() => window.addEventListener('keydown', onKeyDown))
onUnmounted(() => window.removeEventListener('keydown', onKeyDown))
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
        role="dialog"
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

        <!-- 補足 -->
        <div class="px-5 pb-5">
          <div class="rounded-xl border border-canvas-border bg-canvas-card px-4 py-3 text-[11px] text-ink-muted leading-relaxed">
            <p class="font-semibold text-ink mb-1">ヒント</p>
            <ul class="list-disc pl-4 space-y-0.5">
              <li>URL・検索などの入力欄にフォーカス中は、ショートカットは実行されません。</li>
              <li>「+」の表記は、同時押しではなく「キーを押したまま次のキーを押す」操作です。</li>
              <li>右クリック（または長押し）でアイテムの操作メニューが開きます。</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>