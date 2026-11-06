<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { HelpCircle, Info, Shield, FileText, Keyboard, X } from 'lucide-vue-next'
import { useHelpStore } from '~/stores/helpStore'

const helpStore = useHelpStore()
const isOpen = ref(false)
const activeTab = ref<'about' | 'privacy' | 'terms'>('about')

const TABS = [
  { id: 'about', label: 'このサイトについて', shortLabel: '概要', icon: Info },
  { id: 'privacy', label: 'プライバシーポリシー', shortLabel: 'プライバシー', icon: Shield },
  { id: 'terms', label: '利用上の注意', shortLabel: '利用規約', icon: FileText },
] as const

function close() {
  isOpen.value = false
}

function openModal(tab: 'about' | 'privacy' | 'terms' = 'about') {
  activeTab.value = tab
  isOpen.value = true
}

function onEscape(event: KeyboardEvent) {
  if (event.key === 'Escape' && isOpen.value) close()
}

function onOpenSiteInfoEvent(event: Event) {
  const detail = (event as CustomEvent<'about' | 'privacy' | 'terms' | undefined>).detail
  openModal(detail || 'about')
}

function openShortcuts() {
  close()
  helpStore.toggle()
}

onMounted(() => {
  window.addEventListener('keydown', onEscape)
  window.addEventListener('reflens:open-site-info', onOpenSiteInfoEvent as EventListener)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onEscape)
  window.removeEventListener('reflens:open-site-info', onOpenSiteInfoEvent as EventListener)
})
</script>

<template>
  <div class="relative shrink-0">
    <button
      type="button"
      class="p-2 rounded-xl text-ink hover:text-brand hover:bg-canvas-hover border border-canvas-border-strong transition-colors flex items-center justify-center"
      title="サイト情報・利用規約"
      aria-label="サイト情報・利用規約を開く"
      aria-haspopup="dialog"
      :aria-expanded="isOpen"
      @click="openModal('about')"
    >
      <HelpCircle class="w-4 h-4" />
    </button>

    <Teleport to="body">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[85] flex items-end sm:items-center justify-center p-2 sm:p-4 scrim animate-fade-in"
        @click.self="close"
      >
        <div
          class="w-full max-w-xl max-h-[88dvh] rounded-2xl border border-canvas-border bg-canvas-panel shadow-pop flex flex-col overflow-hidden animate-scale-in"
          role="dialog"
          aria-modal="true"
          aria-labelledby="site-info-modal-title"
        >
          <!-- モーダルヘッダー -->
          <div class="px-4 py-3 border-b border-canvas-border flex items-center justify-between gap-2 shrink-0">
            <h2 id="site-info-modal-title" class="text-sm font-bold text-ink flex items-center gap-2">
              <Info class="w-4 h-4 text-brand shrink-0" />
              <span>RefLens.io サイト情報</span>
            </h2>
            <button
              type="button"
              class="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-canvas-hover transition-colors"
              aria-label="閉じる"
              @click="close"
            >
              <X class="w-4 h-4" />
            </button>
          </div>

          <!-- タブ切り替え（アクセシブルな tablist） -->
          <div
            class="px-4 pt-3 pb-2 border-b border-canvas-border bg-canvas-bg/60 grid grid-cols-3 gap-1.5 shrink-0"
            role="tablist"
            aria-label="サイト情報タブ"
          >
            <button
              v-for="tab in TABS"
              :key="tab.id"
              :id="`site-info-tab-${tab.id}`"
              type="button"
              role="tab"
              :aria-selected="activeTab === tab.id"
              :aria-controls="`site-info-panel-${tab.id}`"
              class="flex items-center justify-center gap-1.5 px-2.5 py-2 rounded-xl text-xs transition-colors border"
              :class="activeTab === tab.id
                ? 'bg-brand text-brand-fg border-brand font-bold shadow-sm'
                : 'bg-canvas-panel text-ink border-canvas-border-strong font-medium hover:bg-canvas-hover'"
              @click="activeTab = tab.id"
            >
              <component :is="tab.icon" class="w-3.5 h-3.5 shrink-0" />
              <span class="sm:hidden truncate">{{ tab.shortLabel }}</span>
              <span class="hidden sm:inline truncate">{{ tab.label }}</span>
            </button>
          </div>

          <!-- タブパネル本文 -->
          <div
            :id="`site-info-panel-${activeTab}`"
            role="tabpanel"
            :aria-labelledby="`site-info-tab-${activeTab}`"
            class="p-4 sm:p-5 overflow-y-auto space-y-4 text-xs sm:text-sm leading-relaxed text-ink-muted flex-1 min-h-0"
          >
            <!-- このサイトについて -->
            <template v-if="activeTab === 'about'">
              <p class="text-ink font-medium">
                RefLens.io は、画像やWeb上の参考資料をライブラリにまとめ、キャンバス上で並べて見られる制作支援ツールです。
              </p>
              <section class="p-3.5 rounded-xl bg-canvas-bg border border-canvas-border space-y-1.5">
                <h3 class="text-xs sm:text-sm font-bold text-ink">主な機能</h3>
                <p>Managerで資料を整理し、ViewでPixiv作品を閲覧し、Canvasで資料を自由配置できます。対応する画像には構図・光・色などのAI解析を表示できます。</p>
              </section>
              <section class="p-3.5 rounded-xl bg-canvas-bg border border-canvas-border space-y-1.5">
                <h3 class="text-xs sm:text-sm font-bold text-ink">外部サービスとの関係</h3>
                <p>Pixiv連携は非公式の機能であり、RefLens.ioはPixiv、Danbooru、Instagramの公式サービスではありません。各サービスの利用条件と作品の権利を尊重して利用してください。</p>
              </section>
            </template>

            <!-- プライバシーポリシー -->
            <template v-else-if="activeTab === 'privacy'">
              <p class="text-[11px] text-ink-subtle font-mono">更新日: 2026年10月7日</p>
              <section class="p-3.5 rounded-xl bg-canvas-bg border border-canvas-border space-y-1.5">
                <h3 class="text-xs sm:text-sm font-bold text-ink">取得・保存する情報</h3>
                <p>アカウント登録時のメールアドレス、ユーザー名、パスワードのハッシュ値、ログイン情報を扱います。保存した画像・参照元URL・ブックマーク・ボード・AI解析結果もサーバーに保存されます。</p>
                <p>ブラウザにはログイン用トークンとテーマ設定を保存します。</p>
              </section>
              <section class="p-3.5 rounded-xl bg-canvas-bg border border-canvas-border space-y-1.5">
                <h3 class="text-xs sm:text-sm font-bold text-ink">利用目的・外部通信</h3>
                <p>ログイン状態の維持、ライブラリ・キャンバスの表示と保存、外部サービス連携、画像の取得・キャッシュ、AI解析のために利用します。AI解析の設定によっては画像がGoogle Gemini APIやローカルOllamaで処理されます。</p>
              </section>
              <section class="p-3.5 rounded-xl bg-canvas-bg border border-canvas-border space-y-1.5">
                <h3 class="text-xs sm:text-sm font-bold text-ink">ゲスト利用に関する注意</h3>
                <p>未ログイン時は共通のゲストアカウントが使われます。共用環境ではゲスト領域に個人情報や非公開資料を保存しないでください。</p>
              </section>
            </template>

            <!-- 利用上の注意 -->
            <template v-else>
              <p class="text-[11px] text-ink-subtle font-mono">更新日: 2026年10月7日</p>
              <section class="p-3.5 rounded-xl bg-canvas-bg border border-canvas-border space-y-1.5">
                <h3 class="text-xs sm:text-sm font-bold text-ink">作品と外部サービス</h3>
                <p>作品の権利は各権利者に帰属します。画像の保存、再配布、二次利用については、作者の意思と各サービスの利用条件に従ってください。</p>
              </section>
              <section class="p-3.5 rounded-xl bg-canvas-bg border border-canvas-border space-y-1.5">
                <h3 class="text-xs sm:text-sm font-bold text-ink">AI解析について</h3>
                <p>AI解析は作品の利用許諾を判断する機能ではありません。Pixiv作品に明示的なAI学習禁止の記載がある場合は解析を停止します。解析結果は誤ることがあります。</p>
              </section>
              <section class="p-3.5 rounded-xl bg-canvas-bg border border-canvas-border space-y-1.5">
                <h3 class="text-xs sm:text-sm font-bold text-ink">動作・保存について</h3>
                <p>外部サービスの仕様変更や通信障害により、閲覧・取り込み・解析が利用できない場合があります。重要な資料は元サービスや手元の環境でも管理してください。</p>
              </section>
            </template>
          </div>

          <!-- モーダルフッター -->
          <div class="px-4 py-3 border-t border-canvas-border bg-canvas-bg/40 flex items-center justify-between gap-2 shrink-0">
            <div class="flex items-center gap-2">
              <NuxtLink
                to="/help"
                class="px-3 py-1.5 rounded-xl text-xs font-bold bg-brand-soft hover:bg-brand text-brand hover:text-brand-fg border border-brand/30 transition-colors flex items-center gap-1.5"
                @click="close"
              >
                <HelpCircle class="w-3.5 h-3.5 shrink-0" />
                <span>使い方・操作マニュアル</span>
              </NuxtLink>

              <button
                type="button"
                class="hidden sm:inline-flex px-3 py-1.5 rounded-xl text-xs font-semibold bg-canvas-panel hover:bg-canvas-hover text-ink border border-canvas-border-strong transition-colors items-center gap-1.5"
                @click="openShortcuts"
              >
                <Keyboard class="w-3.5 h-3.5 text-brand" />
                <span>ショートカット</span>
              </button>
            </div>

            <button
              type="button"
              class="px-4 py-1.5 rounded-xl text-xs font-bold bg-brand text-brand-fg hover:bg-brand-hover transition-colors"
              @click="close"
            >
              閉じる
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
