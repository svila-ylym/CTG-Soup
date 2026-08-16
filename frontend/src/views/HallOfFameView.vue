<template>
  <main class="page-shell">
    <div class="page-container">
      <header class="glass-panel mb-8 border-y px-5 py-8 sm:rounded-md sm:border sm:px-8">
        <p class="text-xs font-black uppercase tracking-[.18em] text-amber-700 dark:text-amber-300">HALL OF FAME</p>
        <h1 class="mt-2 text-3xl font-black hall-title sm:text-4xl">殿堂</h1>
        <p class="mt-3 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-300">评分与口碑共同留下的神汤作品。</p>
      </header>

      <div v-if="loading" class="grid gap-5 md:grid-cols-2 lg:grid-cols-3" aria-busy="true">
        <div v-for="index in 6" :key="index" class="glass-card h-48 animate-pulse bg-slate-100 dark:bg-neutral-900"></div>
      </div>
      <div v-else-if="error" class="glass-panel p-8 text-center text-sm text-red-600 dark:text-red-400">{{ error }}</div>
      <div v-else-if="items.length" class="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
        <router-link v-for="soup in items" :key="soup.id" :to="`/soups/${soup.id}`" class="glass-card glass-card-interactive group flex min-h-52 flex-col p-5">
          <div class="flex items-start justify-between gap-3">
            <span class="hall-seal">神汤</span>
            <span class="text-sm font-bold text-amber-600 dark:text-amber-300">{{ soup.average_score.toFixed(1) }} 分</span>
          </div>
          <h2 class="mt-4 line-clamp-2 break-words text-lg font-black hall-title transition group-hover:brightness-110">{{ soup.title }}</h2>
          <p class="mt-3 line-clamp-3 flex-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{{ soup.puzzle }}</p>
          <p class="mt-4 border-t border-slate-200 pt-3 text-xs text-slate-500 dark:border-neutral-800 dark:text-slate-400">{{ soup.rating_count }} 人评分</p>
        </router-link>
      </div>
      <div v-else class="glass-panel p-12 text-center text-sm text-slate-500">殿堂暂时没有作品。</div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { soupApi } from '@/api/soup'
import type { TurtleSoup } from '@/types'
import { extractApiError } from '@/utils/auth'

const items = ref<TurtleSoup[]>([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    items.value = (await soupApi.getHallOfFame({ page: 1, page_size: 60 })).data.items
  } catch (cause) {
    error.value = extractApiError(cause, '殿堂加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
