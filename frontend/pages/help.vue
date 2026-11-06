<script setup lang="ts">
import {
  HelpCircle,
  FolderOpen,
  Layers,
  Compass,
  Sparkles,
  Keyboard,
  Folder,
  Tag,
  MousePointer2,
  Hand,
  Wand2,
  ZoomIn,
  Move,
  RotateCw,
  FlipHorizontal,
  FlipVertical,
  SunMoon,
  Lock,
  Copy,
  Trash2,
  AlignLeft,
  AlignCenter,
  AlignRight,
  AlignHorizontalJustifyCenter,
  LayoutGrid,
  Maximize2,
  ExternalLink,
  CheckCircle2,
  Shield,
  FileText,
  Info,
  ChevronRight,
  Bookmark,
  Plus,
  Upload,
} from 'lucide-vue-next'
import AppHeader from '~/components/ui/AppHeader.vue'

useHead({
  title: '使い方・操作ガイド（ヘルプ） | RefLens.io',
  meta: [
    {
      name: 'description',
      content: 'RefLens.ioの基本機能、資料のブックマーク・フォルダ・タグ管理、無限キャンバスでの直感操作、pixiv連携、AI解析、キーボードショートカット一覧を詳しく解説します。'
    }
  ]
})

const TOC_ITEMS = [
  { id: 'help-manager', label: 'Manager（資料管理）', icon: FolderOpen },
  { id: 'help-canvas', label: 'Canvas（無限キャンバス）', icon: Layers },
  { id: 'help-view', label: 'View（pixiv連携）', icon: Compass },
  { id: 'help-insight', label: 'AI解析 & パレット', icon: Sparkles },
  { id: 'help-shortcuts', label: 'ショートカット & マウス操作', icon: Keyboard },
  { id: 'help-organize', label: 'フォルダ・タグ・一括管理', icon: Folder },
  { id: 'help-account', label: 'アカウント・保存', icon: Shield },
  { id: 'help-site', label: 'サイト情報・ポリシー', icon: Info },
] as const

const SHORTCUT_GROUPS = [
  {
    title: 'キャンバス基本操作',
    icon: Hand,
    items: [
      { keys: ['Space', '+ ドラッグ'], desc: 'キャンバスをパン（縦横に移動）' },
      { keys: ['ホイール / 2本指'], desc: 'キャンバスをスクロール移動' },
      { keys: ['Cmd / Ctrl', '+ ホイール'], desc: 'カーソル位置を中心に拡大・縮小' },
      { keys: ['+', '/ -'], desc: 'ズームイン / ズームアウト' },
      { keys: ['Cmd / Ctrl', '+ 0'], desc: 'ズーム倍率を100%に等倍リセット' },
      { keys: ['F'], desc: '全アイテムが画面に収まるよう自動フィット' },
      { keys: ['ダブルクリック'], desc: 'その資料を中心にして拡大フォーカス' },
    ]
  },
  {
    title: '選択と編集',
    icon: MousePointer2,
    items: [
      { keys: ['クリック'], desc: '資料アイテムを選択' },
      { keys: ['空地をドラッグ'], desc: 'ラバーバンド（矩形）でまとめて範囲選択' },
      { keys: ['Shift', '+ クリック'], desc: '複数選択の追加 / 除外' },
      { keys: ['Cmd / Ctrl', '+ A'], desc: 'キャンバス上のすべての資料を選択' },
      { keys: ['↑ ↓ ← →'], desc: '選択アイテムを1px移動（Shift併用で10px）' },
      { keys: ['Cmd / Ctrl', '+ D'], desc: '選択中の資料を同じ位置に複製' },
      { keys: ['Delete / Backspace'], desc: '選択中の資料をキャンバスから削除' },
      { keys: ['Esc'], desc: '選択解除 / パネルやモーダルを閉じる' },
    ]
  },
  {
    title: '変形・表示調整',
    icon: Layers,
    items: [
      { keys: ['4隅ハンドルドラッグ'], desc: '縦横比を維持したまま拡大・縮小' },
      { keys: ['上部ハンドルドラッグ'], desc: '自由回転（Shift併用で15°スナップ）' },
      { keys: ['R'], desc: '90°時計回りに回転' },
      { keys: ['H'], desc: '左右反転（デッサンやパースの狂いチェック）' },
      { keys: ['V'], desc: '上下反転' },
      { keys: ['G'], desc: 'グレースケール（明度・バリューのみを比較）' },
      { keys: [']', '/ ['], desc: '重なり順を 前面へ移動 / 背面へ移動' },
      { keys: ['L'], desc: '位置とサイズを固定（誤操作防止のロック）' },
    ]
  },
  {
    title: '取り込み・機能呼び出し',
    icon: Wand2,
    items: [
      { keys: ['Cmd / Ctrl', '+ V'], desc: 'クリップボードの画像を直接キャンバスへ貼り付け' },
      { keys: ['Cmd / Ctrl', '+ Z'], desc: '元に戻す（Undo）' },
      { keys: ['Cmd', '+ Shift', '+ Z'], desc: 'やり直し（Redo）' },
      { keys: ['B'], desc: 'ブックマークブラウザを開閉' },
      { keys: ['I'], desc: '選択アイテムのAI解析パネルを開閉' },
      { keys: ['/'], desc: '検索入力欄に素早くフォーカス' },
      { keys: ['D'], desc: 'ライトテーマ / ダークテーマの切り替え' },
      { keys: ['?'], desc: 'クイックショートカット一覧を表示' },
    ]
  }
]
</script>

<template>
  <div class="min-h-screen bg-canvas-bg text-ink flex flex-col antialiased selection:bg-brand selection:text-brand-fg">
    <AppHeader />

    <main class="flex-1 w-full max-w-4xl mx-auto px-4 sm:px-6 py-8 sm:py-12 space-y-6">
      <!-- 1. ヘッダーカード（Tunedrop風の明確なアイコン・見出し・説明） -->
      <header class="p-6 sm:p-8 rounded-2xl bg-canvas-panel border border-canvas-border-strong shadow-card flex flex-col sm:flex-row items-start sm:items-center gap-5 sm:gap-6">
        <div class="w-14 h-14 rounded-2xl bg-brand-soft text-brand flex items-center justify-center shrink-0 shadow-sm border border-brand/20">
          <HelpCircle class="w-8 h-8" />
        </div>
        <div class="space-y-1.5 flex-1 min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="text-[10px] font-mono font-bold tracking-widest uppercase text-brand bg-brand-soft px-2 py-0.5 rounded-md border border-brand/20">
              RefLens.io / Guide & Docs
            </span>
            <span class="text-[10px] font-mono text-ink-subtle">更新日: 2026年11月6日</span>
          </div>
          <h1 class="text-xl sm:text-2xl font-bold tracking-tight text-ink">
            RefLens.io の使い方・操作マニュアル
          </h1>
          <p class="text-xs sm:text-sm text-ink-muted leading-relaxed">
            イラスト・デザイン参考資料の収集、フォルダ・タグ分類から、PureRefのように広大な無限キャンバスでの自由な並べ替え、pixiv連携、AI構図・色彩解析までを徹底解説した総合ガイドです。
          </p>
        </div>
      </header>

      <!-- 2. 目次（Tunedropの .help-toc 風ピル型アンカーリンク） -->
      <nav class="flex flex-wrap gap-2 py-1 select-none" aria-label="ヘルプ目次">
        <a
          v-for="item in TOC_ITEMS"
          :key="item.id"
          :href="`#${item.id}`"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold text-ink bg-canvas-panel hover:bg-canvas-hover border border-canvas-border-strong hover:border-brand hover:text-brand transition-all shadow-sm"
        >
          <component :is="item.icon" class="w-3.5 h-3.5 text-brand shrink-0" />
          <span>{{ item.label }}</span>
        </a>
      </nav>

      <!-- 3. 各セクション詳細 -->
      <div class="space-y-6">
        <!-- 3-1. Manager（資料管理） -->
        <section id="help-manager" class="scroll-mt-20 p-6 sm:p-8 rounded-2xl bg-canvas-panel border border-canvas-border-strong shadow-card space-y-5">
          <div class="flex items-center gap-3 border-b border-canvas-border pb-3">
            <div class="p-2 rounded-xl bg-brand-soft text-brand shrink-0">
              <FolderOpen class="w-5 h-5" />
            </div>
            <div>
              <h2 class="text-base sm:text-lg font-bold text-ink flex items-center gap-2">
                1. Manager（資料・ブックマーク管理）
              </h2>
              <p class="text-xs text-ink-muted">画像やWebの参考資料を集約し、フォルダやタグでいつでも引き出せるように整理する画面です。</p>
            </div>
          </div>

          <div class="space-y-4 text-xs sm:text-sm text-ink-muted leading-relaxed">
            <div>
              <h3 class="text-xs font-bold text-brand uppercase tracking-wider mb-1.5">資料を追加・保存する3つの方法</h3>
              <ol class="list-decimal list-inside space-y-1.5 pl-1">
                <li><strong class="text-ink">Webの画像URLを保存:</strong> 画面上部の「+ URL保存」に画像やWebページのURLを貼り付けると、タイトルとサムネイルを自動取得してライブラリに追加します。</li>
                <li><strong class="text-ink">端末の画像を直接アップロード:</strong> PCやスマートフォンから画像ファイル（PNG, JPG, WebP, GIF等）をドラッグ＆ドロップ、またはファイル選択で一括追加できます。</li>
                <li><strong class="text-ink">pixiv検索（View画面）から保存:</strong> pixiv連携画面で気に入ったイラストを、指定フォルダへワンクリックで直接保存できます。</li>
              </ol>
            </div>

            <div class="p-3.5 rounded-xl bg-canvas-bg border border-canvas-border text-xs text-ink-muted space-y-1">
              <p class="font-bold text-ink flex items-center gap-1.5">
                <Bookmark class="w-3.5 h-3.5 text-brand" />
                <span>対応URL・ファイル形式</span>
              </p>
              <p>一般的な画像URL（<code>.png</code>, <code>.jpg</code>, <code>.webp</code>, <code>.gif</code>）、pixiv作品ページ、Danbooru等の画像URLに対応しています。</p>
            </div>

            <div>
              <h3 class="text-xs font-bold text-brand uppercase tracking-wider mb-1.5">フォルダによるカテゴリ分類</h3>
              <ul class="list-disc list-inside space-y-1.5 pl-1">
                <li>サイドバーの「フォルダ」タブから、用途に応じたフォルダ（例: 「ポーズ」「配色」「背景・パース」「キャラクター衣装」等）を無制限に作成できます。</li>
                <li>フォルダには好みのアクセントカラーを設定でき、一目で識別できます。</li>
                <li>カードをつかんで目的のフォルダへドラッグ＆ドロップするだけで、素早く移動できます。</li>
              </ul>
            </div>

            <div>
              <h3 class="text-xs font-bold text-brand uppercase tracking-wider mb-1.5">タグ機能（自動タグON/OFF・手動タグ編集）</h3>
              <ul class="list-disc list-inside space-y-1.5 pl-1">
                <li><strong class="text-ink">自動タグ機能:</strong> 画面のスイッチで自動タグのON/OFFをいつでも切り替えられます。ONにしておくと保存時にAIが画像の特徴（ポーズ、アングル、衣装等）を自動推測してタグを付与します。</li>
                <li><strong class="text-ink">手動タグ編集:</strong> 資料カードの詳細メニューから、自分好みのカスタムタグを何個でも追加・削除できます。</li>
                <li><strong class="text-ink">タグでの一括絞り込み:</strong> タグをクリックすると、そのタグを持つ資料だけが瞬時にフィルタリングされます。</li>
              </ul>
            </div>

            <div>
              <h3 class="text-xs font-bold text-brand uppercase tracking-wider mb-1.5">複数選択と一括操作</h3>
              <p>
                カード右上のチェックボックスを選択すると複数選択モードになり、選択した資料をまとめて「<strong>一括フォルダ移動</strong>」「<strong>一括タグ付け</strong>」「<strong>一括削除</strong>」できます。大量の資料整理も一瞬で行えます。
              </p>
            </div>
          </div>
        </section>

        <!-- 3-2. Canvas（無限キャンバス） -->
        <section id="help-canvas" class="scroll-mt-20 p-6 sm:p-8 rounded-2xl bg-canvas-panel border border-canvas-border-strong shadow-card space-y-5">
          <div class="flex items-center gap-3 border-b border-canvas-border pb-3">
            <div class="p-2 rounded-xl bg-brand-soft text-brand shrink-0">
              <Layers class="w-5 h-5" />
            </div>
            <div>
              <h2 class="text-base sm:text-lg font-bold text-ink flex items-center gap-2">
                2. Canvas（無限キャンバス・リファレンスボード）
              </h2>
              <p class="text-xs text-ink-muted">PureRefのように、縦横無尽に広がるキャンバス上で資料を並べ、見比べながら作画やモデリングに集中できます。</p>
            </div>
          </div>

          <div class="space-y-4 text-xs sm:text-sm text-ink-muted leading-relaxed">
            <div>
              <h3 class="text-xs font-bold text-brand uppercase tracking-wider mb-1.5">キャンバスの基本移動・ズーム</h3>
              <ul class="list-disc list-inside space-y-1.5 pl-1">
                <li><strong class="text-ink">パン（画面移動）:</strong> <kbd class="px-1.5 py-0.5 rounded bg-canvas-card border border-canvas-border-strong text-xs font-mono">Space</kbd> キーを押しながらドラッグ、またはマウスホイール押し込みドラッグ。トラックパッドでは2本指スクロールで自由自在に移動できます。</li>
                <li><strong class="text-ink">ズーム:</strong> 右上の「- / +」ボタン、または <kbd class="px-1.5 py-0.5 rounded bg-canvas-card border border-canvas-border-strong text-xs font-mono">Cmd/Ctrl</kbd> + ホイールで滑らかに拡大・縮小します。</li>
                <li><strong class="text-ink">100%等倍リセット:</strong> 右上の倍率数値（例: 42%）をクリック、または <kbd class="px-1.5 py-0.5 rounded bg-canvas-card border border-canvas-border-strong text-xs font-mono">Cmd/Ctrl + 0</kbd>。</li>
                <li><strong class="text-ink">全体表示フィット（<kbd class="px-1.5 py-0.5 rounded bg-canvas-card border border-canvas-border-strong text-xs font-mono">F</kbd>）:</strong> 下部ドックの全体表示ボタン、またはキーボードの <kbd>F</kbd> を押すと、キャンバス上の全資料が画面内に美しく収まる位置と倍率に自動調整されます。</li>
                <li><strong class="text-ink">個別フォーカス:</strong> 画像をダブルクリックすると、その画像が画面中央に大きくフォーカスされます。</li>
              </ul>
            </div>

            <div>
              <h3 class="text-xs font-bold text-brand uppercase tracking-wider mb-1.5">キャンバスへの資料配置方法</h3>
              <ol class="list-decimal list-inside space-y-1.5 pl-1">
                <li><strong class="text-ink">ブックマークブラウザから配置:</strong> 左上の「ブックマーク」ボタンを押すと、保存済み資料の一覧が横からスライド表示されます。クリックでキャンバスにワンタップ配置できるほか、キャンバス上の好きな位置へ直接ドラッグ＆ドロップも可能です。</li>
                <li><strong class="text-ink">PCからの直ドラッグ＆ドロップ:</strong> デスクトップやFinderから画像ファイルをキャンバスへ直接ドロップすると、即座にアップロードされてその位置に配置されます。</li>
                <li><strong class="text-ink">クリップボード貼り付け:</strong> Webブラウザやお絵描きソフトで画像をコピー（Cmd+C）した状態でキャンバス上で <kbd class="px-1.5 py-0.5 rounded bg-canvas-card border border-canvas-border-strong text-xs font-mono">Cmd/Ctrl + V</kbd> を押すと、直接貼り付けられます。</li>
              </ol>
            </div>

            <div>
              <h3 class="text-xs font-bold text-brand uppercase tracking-wider mb-1.5">選択中アイテムの編集・変形ツール（上部固定バー）</h3>
              <p>資料をクリックすると、画面上部に**固定操作バー**が表示されます。キャンバスの回転やズームに左右されず、常に押しやすい位置で作業できます:</p>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 mt-2">
                <div class="p-3 rounded-xl bg-canvas-bg border border-canvas-border flex items-start gap-2.5">
                  <FlipHorizontal class="w-4 h-4 text-brand shrink-0 mt-0.5" />
                  <div>
                    <span class="font-bold text-ink">左右反転 [H] / 上下反転 [V]</span>
                    <p class="text-[11px] text-ink-subtle">左右を反転させてデッサンやポーズの狂いを客観的にチェックできます。</p>
                  </div>
                </div>
                <div class="p-3 rounded-xl bg-canvas-bg border border-canvas-border flex items-start gap-2.5">
                  <SunMoon class="w-4 h-4 text-brand shrink-0 mt-0.5" />
                  <div>
                    <span class="font-bold text-ink">グレースケール [G]</span>
                    <p class="text-[11px] text-ink-subtle">モノクロ化して色情報をなくし、明度（バリュー）のコントラストのみを比較。</p>
                  </div>
                </div>
                <div class="p-3 rounded-xl bg-canvas-bg border border-canvas-border flex items-start gap-2.5">
                  <RotateCw class="w-4 h-4 text-brand shrink-0 mt-0.5" />
                  <div>
                    <span class="font-bold text-ink">90°回転 [R] / 上部ハンドル</span>
                    <p class="text-[11px] text-ink-subtle">画像上部の丸ハンドルで自由回転（Shiftで15°刻みスナップ）、Rキーで90度単位回転。</p>
                  </div>
                </div>
                <div class="p-3 rounded-xl bg-canvas-bg border border-canvas-border flex items-start gap-2.5">
                  <Lock class="w-4 h-4 text-brand shrink-0 mt-0.5" />
                  <div>
                    <span class="font-bold text-ink">固定ロック [L]</span>
                    <p class="text-[11px] text-ink-subtle">誤って動かしたくない背景資料や下敷き画像を安全にピン留めします。</p>
                  </div>
                </div>
              </div>
            </div>

            <div>
              <h3 class="text-xs font-bold text-brand uppercase tracking-wider mb-1.5">複数選択と自動整列ツール</h3>
              <ul class="list-disc list-inside space-y-1.5 pl-1">
                <li>キャンバスの空地をドラッグすると、囲んだ複数の資料をまとめて選択（ラバーバンド選択）できます。</li>
                <li><kbd class="px-1.5 py-0.5 rounded bg-canvas-card border border-canvas-border-strong text-xs font-mono">Shift</kbd> または <kbd class="px-1.5 py-0.5 rounded bg-canvas-card border border-canvas-border-strong text-xs font-mono">Cmd/Ctrl</kbd> + クリックで追加選択も可能。</li>
                <li>複数選択時、上部バーに「<strong>左揃え</strong>」「<strong>中央揃え</strong>」「<strong>水平均等配置</strong>」「<strong>グリッド整列（マス目状に配置）</strong>」ツールが表示され、散らかった資料を一瞬で整頓できます。</li>
              </ul>
            </div>

            <div class="p-4 rounded-xl bg-brand-soft border border-brand/20 text-ink space-y-1.5">
              <p class="font-bold text-brand text-xs sm:text-sm flex items-center gap-1.5">
                <Folder class="w-4 h-4" />
                <span>キャンバスからフォルダへの一括セーブ & D&D移動</span>
              </p>
              <ul class="text-xs text-ink-muted space-y-1 list-disc list-inside pl-0.5">
                <li><strong class="text-ink">一括保存:</strong> 左上または下部ドックの「一括保存」ボタンから、キャンバス上に出ている全資料を指定フォルダへワンクリックで一括保管できます。作業終了前のまとめ保存に重宝します。</li>
                <li><strong class="text-ink">直感ドラッグ移動:</strong> キャンバス上の資料をつまんでドラッグすると、画面最前面に浮き上がります。そのまま左側のブックマークブラウザの各フォルダ項目（「すべての資料」「Poses」など）へドロップするだけで、そのフォルダへ移動できます。</li>
              </ul>
            </div>
          </div>
        </section>

        <!-- 3-3. View（pixiv連携） -->
        <section id="help-view" class="scroll-mt-20 p-6 sm:p-8 rounded-2xl bg-canvas-panel border border-canvas-border-strong shadow-card space-y-5">
          <div class="flex items-center gap-3 border-b border-canvas-border pb-3">
            <div class="p-2 rounded-xl bg-brand-soft text-brand shrink-0">
              <Compass class="w-5 h-5" />
            </div>
            <div>
              <h2 class="text-base sm:text-lg font-bold text-ink flex items-center gap-2">
                3. View（pixivイラスト連携）
              </h2>
              <p class="text-xs text-ink-muted">pixivの膨大なイラストの中から、構図や配色のヒントになる作品を検索・収集できます。</p>
            </div>
          </div>

          <div class="space-y-4 text-xs sm:text-sm text-ink-muted leading-relaxed">
            <div>
              <h3 class="text-xs font-bold text-brand uppercase tracking-wider mb-1.5">検索とソート</h3>
              <ul class="list-disc list-inside space-y-1.5 pl-1">
                <li>検索バーにキーワードやタグ（例: 「着物」「ポーズ」「サイバーパンク」など）を入力して検索。</li>
                <li>「おすすめ順」「人気順」「閲覧数順」「ブックマーク数順」で並び替え、評価の高い作例を効率よく探せます。</li>
              </ul>
            </div>

            <div>
              <h3 class="text-xs font-bold text-brand uppercase tracking-wider mb-1.5">複数選択保存 & フォルダ指定</h3>
              <ul class="list-disc list-inside space-y-1.5 pl-1">
                <li>選択モードをONにすると、気になるイラストを複数チェックして、目的のフォルダ（例: 「Poses & Anatomy」）へ一度にまとめて保存できます。</li>
                <li>すでに保存済みの作品には「保存済み」バッジが表示され、重複保存を防ぎます。</li>
                <li>各イラストの「キャンバスに追加」ボタンを押すと、現在開いているキャンバスへ直接送り込むことも可能です。</li>
              </ul>
            </div>

            <p class="text-xs text-ink-subtle">
              ※ pixiv連携は作品の権利者の意図と規約を尊重したプロキシ閲覧機能です。画像の著作権は各作者に帰属します。
            </p>
          </div>
        </section>

        <!-- 3-4. AI解析 & パレット -->
        <section id="help-insight" class="scroll-mt-20 p-6 sm:p-8 rounded-2xl bg-canvas-panel border border-canvas-border-strong shadow-card space-y-5">
          <div class="flex items-center gap-3 border-b border-canvas-border pb-3">
            <div class="p-2 rounded-xl bg-brand-soft text-brand shrink-0">
              <Sparkles class="w-5 h-5" />
            </div>
            <div>
              <h2 class="text-base sm:text-lg font-bold text-ink flex items-center gap-2">
                4. AI解析 & カラーパレット（Insight）
              </h2>
              <p class="text-xs text-ink-muted">資料のポーズ、骨格、ライティング、色彩設計をAIが自動解析して創作のヒントを提示します。</p>
            </div>
          </div>

          <div class="space-y-4 text-xs sm:text-sm text-ink-muted leading-relaxed">
            <div>
              <h3 class="text-xs font-bold text-brand uppercase tracking-wider mb-1.5">構図・ポーズ・ライティングのAI解析</h3>
              <p>
                キャンバス上の資料を選んで <kbd class="px-1.5 py-0.5 rounded bg-canvas-card border border-canvas-border-strong text-xs font-mono">I</kbd> キー、または上部バーの「AI解析」を押すと、右側に解析パネルが開きます。
              </p>
              <ul class="list-disc list-inside space-y-1 pl-1 mt-1.5">
                <li><strong>ポーズとアタリ:</strong> 人体の重心、コントラポスト、手足のパース、視線誘導のラインを解析。</li>
                <li><strong>光源とライティング:</strong> キーライトとフィルライトの向き、環境光、ハイライトと陰影の落ち方を解説。</li>
                <li><strong>色彩・配色の比率:</strong> メインカラー、サブカラー、アクセントカラーの調和を言語化。</li>
              </ul>
            </div>

            <div>
              <h3 class="text-xs font-bold text-brand uppercase tracking-wider mb-1.5">カラーパレット抽出・HEXワンタッチコピー</h3>
              <p>
                画像から抽出された代表色がキャンバス下部にカラーチップバーとして表示されます。チップをクリックするだけで、16進数カラーコード（HEX）がクリップボードにコピーされ、イラスト制作ソフト（CLIP STUDIO PAINT、Photoshop、Procreate等）にすぐ貼り付けて使えます。
              </p>
            </div>
          </div>
        </section>

        <!-- 3-5. キーボードショートカット & マウス操作一覧 -->
        <section id="help-shortcuts" class="scroll-mt-20 p-6 sm:p-8 rounded-2xl bg-canvas-panel border border-canvas-border-strong shadow-card space-y-5">
          <div class="flex items-center gap-3 border-b border-canvas-border pb-3">
            <div class="p-2 rounded-xl bg-brand-soft text-brand shrink-0">
              <Keyboard class="w-5 h-5" />
            </div>
            <div>
              <h2 class="text-base sm:text-lg font-bold text-ink flex items-center gap-2">
                5. 操作方法・ショートカット一覧
              </h2>
              <p class="text-xs text-ink-muted">作業スピードを劇的に上げるキーボード＆マウス操作のクイックリファレンスです。</p>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div
              v-for="grp in SHORTCUT_GROUPS"
              :key="grp.title"
              class="p-4 rounded-xl bg-canvas-bg border border-canvas-border space-y-3"
            >
              <h3 class="text-xs font-bold text-ink flex items-center gap-2">
                <component :is="grp.icon" class="w-3.5 h-3.5 text-brand" />
                <span>{{ grp.title }}</span>
              </h3>
              <div class="space-y-2 text-xs">
                <div
                  v-for="item in grp.items"
                  :key="item.desc"
                  class="flex items-center justify-between gap-2 border-b border-canvas-border/50 pb-1.5 last:border-0 last:pb-0"
                >
                  <div class="flex items-center gap-1 flex-wrap shrink-0">
                    <kbd
                      v-for="k in item.keys"
                      :key="k"
                      class="px-1.5 py-0.5 rounded bg-canvas-panel border border-canvas-border-strong text-[11px] font-mono font-bold text-ink shadow-xs"
                    >
                      {{ k }}
                    </kbd>
                  </div>
                  <span class="text-ink-muted text-right truncate text-[11px] sm:text-xs">{{ item.desc }}</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 3-6. フォルダ・タグ・一括管理のコツ -->
        <section id="help-organize" class="scroll-mt-20 p-6 sm:p-8 rounded-2xl bg-canvas-panel border border-canvas-border-strong shadow-card space-y-5">
          <div class="flex items-center gap-3 border-b border-canvas-border pb-3">
            <div class="p-2 rounded-xl bg-brand-soft text-brand shrink-0">
              <Folder class="w-5 h-5" />
            </div>
            <div>
              <h2 class="text-base sm:text-lg font-bold text-ink flex items-center gap-2">
                6. フォルダ・タグ・データ整理のコツ
              </h2>
              <p class="text-xs text-ink-muted">資料が何百枚に増えても迷子にならない、おすすめの整理術です。</p>
            </div>
          </div>

          <div class="space-y-3 text-xs sm:text-sm text-ink-muted leading-relaxed">
            <div class="p-3.5 rounded-xl bg-canvas-bg border border-canvas-border space-y-1.5">
              <h3 class="text-xs font-bold text-ink flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-brand"></span>
                <span>迷ったらまずは「未分類（All References）」へ</span>
              </h3>
              <p>閲覧中に気になった画像は、フォルダを気にせずまずは保存しておきましょう。あとから複数選択モードやキャンバス上でのドラッグ＆ドロップでまとめてフォルダ分けできます。</p>
            </div>

            <div class="p-3.5 rounded-xl bg-canvas-bg border border-canvas-border space-y-1.5">
              <h3 class="text-xs font-bold text-ink flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-brand"></span>
                <span>おすすめのフォルダ分け</span>
              </h3>
              <p>「人物ポーズ」「表情・目・手」「衣装・テクスチャ」「背景・パース・建築」「配色・トーン」「作風・テイスト」のように大まかに分けておくと、作画工程ごとに必要な資料を素早く呼び出せます。</p>
            </div>

            <div class="p-3.5 rounded-xl bg-canvas-bg border border-canvas-border space-y-1.5">
              <h3 class="text-xs font-bold text-ink flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-brand"></span>
                <span>キャンバス上の「一括セーブ」で作品ごとに保存</span>
              </h3>
              <p>特定のイラストやデザインを描くためにキャンバス上へ集めた資料群は、離れる前に「一括保存」で新規フォルダ（例: 「2026冬コミ新刊用」など）に保存しておくと、次回以降もワンクリックで再現できます。</p>
            </div>
          </div>
        </section>

        <!-- 3-7. アカウント・保存について -->
        <section id="help-account" class="scroll-mt-20 p-6 sm:p-8 rounded-2xl bg-canvas-panel border border-canvas-border-strong shadow-card space-y-5">
          <div class="flex items-center gap-3 border-b border-canvas-border pb-3">
            <div class="p-2 rounded-xl bg-brand-soft text-brand shrink-0">
              <Shield class="w-5 h-5" />
            </div>
            <div>
              <h2 class="text-base sm:text-lg font-bold text-ink flex items-center gap-2">
                7. アカウント & データの保存・同期
              </h2>
              <p class="text-xs text-ink-muted">ログインによるクラウド同期や、オフライン自動保存について解説します。</p>
            </div>
          </div>

          <div class="space-y-3 text-xs sm:text-sm text-ink-muted leading-relaxed">
            <ul class="list-disc list-inside space-y-1.5 pl-1">
              <li><strong class="text-ink">ログインなしでも利用可能:</strong> RefLens.ioはアカウント登録なしでも即座に利用できます（データはお使いの端末・ブラウザ内に保持されます）。</li>
              <li><strong class="text-ink">無料アカウント登録でクラウド同期:</strong> 右上の「ログイン」からユーザー名とパスワードで登録すると、複数のPCやタブレット間でも資料ライブラリやキャンバスが自動的に同期されます。</li>
              <li><strong class="text-ink">自動保存（オートセーブ）:</strong> キャンバス上でアイテムを動かしたり変形すると、バックグラウンドで自動保存されます。画面を再読み込みしても作業状態がそのまま復元されます。</li>
            </ul>
          </div>
        </section>

        <!-- 3-8. サイト情報・ポリシー -->
        <section id="help-site" class="scroll-mt-20 p-6 sm:p-8 rounded-2xl bg-canvas-panel border border-canvas-border-strong shadow-card space-y-5">
          <div class="flex items-center gap-3 border-b border-canvas-border pb-3">
            <div class="p-2 rounded-xl bg-brand-soft text-brand shrink-0">
              <Info class="w-5 h-5" />
            </div>
            <div>
              <h2 class="text-base sm:text-lg font-bold text-ink flex items-center gap-2">
                8. サイト情報・ポリシー
              </h2>
              <p class="text-xs text-ink-muted">RefLens.io の基本情報と関連規約へのリンクです。</p>
            </div>
          </div>

          <dl class="grid grid-cols-1 sm:grid-cols-[140px_1fr] gap-x-4 gap-y-2.5 text-xs sm:text-sm text-ink-muted">
            <dt class="font-bold text-ink">サービス名</dt>
            <dd>RefLens.io（レフレンズ）</dd>

            <dt class="font-bold text-ink">公開URL</dt>
            <dd>
              <a href="https://art.wawa-app.me/RefLens.io/" class="text-brand hover:underline font-mono">
                https://art.wawa-app.me/RefLens.io/
              </a>
            </dd>

            <dt class="font-bold text-ink">提供内容</dt>
            <dd>イラストレーター・クリエイター向け参考資料ブックマーク管理、無限キャンバス作業空間、pixiv連携、AI構図・色彩解析</dd>

            <dt class="font-bold text-ink">利用料金</dt>
            <dd>完全無料（個人開発プロジェクト）</dd>

            <dt class="font-bold text-ink">関連規約</dt>
            <dd class="flex flex-wrap gap-3">
              <NuxtLink to="/about" class="text-brand hover:underline font-semibold flex items-center gap-1">
                <span>このサイトについて</span>
                <ChevronRight class="w-3.5 h-3.5" />
              </NuxtLink>
              <NuxtLink to="/privacy" class="text-brand hover:underline font-semibold flex items-center gap-1">
                <span>プライバシーポリシー</span>
                <ChevronRight class="w-3.5 h-3.5" />
              </NuxtLink>
              <NuxtLink to="/terms" class="text-brand hover:underline font-semibold flex items-center gap-1">
                <span>利用上の注意</span>
                <ChevronRight class="w-3.5 h-3.5" />
              </NuxtLink>
            </dd>
          </dl>

          <div class="p-4 rounded-xl bg-canvas-bg border border-canvas-border text-xs text-ink-subtle">
            困ったときは、このページの内容を確認するか、表示や動作がおかしい場合はブラウザのスーパーリロード（<kbd class="px-1 py-0.5 rounded bg-canvas-panel border border-canvas-border font-mono">Cmd + Shift + R</kbd> / <kbd class="px-1 py-0.5 rounded bg-canvas-panel border border-canvas-border font-mono">Ctrl + F5</kbd>）をお試しください。
          </div>
        </section>
      </div>
    </main>

    <!-- フッター -->
    <footer class="border-t border-canvas-border bg-canvas-panel px-5 py-6 text-xs text-ink-muted mt-12">
      <nav class="max-w-4xl mx-auto flex flex-wrap items-center justify-between gap-4" aria-label="フッターナビゲーション">
        <div class="flex items-center gap-3">
          <span class="font-bold text-ink">RefLens.io</span>
          <span class="text-ink-subtle">Raindrop × pixiv × PureRef</span>
        </div>
        <div class="flex flex-wrap items-center gap-x-5 gap-y-2">
          <NuxtLink to="/help" class="text-brand font-bold hover:underline">使い方・ヘルプ</NuxtLink>
          <NuxtLink to="/about" class="hover:text-brand">このサイトについて</NuxtLink>
          <NuxtLink to="/privacy" class="hover:text-brand">プライバシー</NuxtLink>
          <NuxtLink to="/terms" class="hover:text-brand">利用上の注意</NuxtLink>
        </div>
      </nav>
    </footer>
  </div>
</template>
