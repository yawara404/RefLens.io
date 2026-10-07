<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useBoardStore } from '~/stores/boardStore'

const boardStore = useBoardStore()
const error = ref('')
const loading = ref(false)

async function openCanvas() {
  loading.value = true
  error.value = ''
  // 現在のボードは別アカウントの古い状態かもしれないため、APIで再確認する。
  const target = await boardStore.loadFirstBoard()

  if (target?.id) {
    await navigateTo(`/board/${target.id}`, { replace: true })
  } else {
    error.value = 'キャンバスを読み込めませんでした。APIサーバーの接続を確認して再試行してください。'
  }
  loading.value = false
}

onMounted(openCanvas)
</script>

<template>
  <div class="min-h-screen bg-canvas-bg flex flex-col items-center justify-center gap-4 text-ink-subtle text-sm px-5 text-center">
    <p>{{ error || 'キャンバスを開いています...' }}</p>
    <button v-if="error" type="button" class="rounded-lg bg-brand px-4 py-2 text-brand-fg font-semibold disabled:opacity-50" :disabled="loading" @click="openCanvas">
      再試行
    </button>
  </div>
</template>
