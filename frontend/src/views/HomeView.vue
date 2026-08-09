<template>
  <main class="min-h-screen bg-white dark:bg-black">
    <!-- Hero 区域 -->
    <div class="border-b border-slate-200 bg-white py-10 text-slate-900 dark:border-neutral-800 dark:bg-black dark:text-white sm:py-16">
      <div class="container mx-auto px-4 text-center">
        <h1 class="mb-4 text-4xl font-bold sm:text-5xl">汤吧社区</h1>
        <p class="mb-8 text-lg text-slate-600 dark:text-slate-300 sm:text-xl">情境推理游戏 · 解谜爱好者的聚集地</p>
        <div class="flex flex-col justify-center gap-3 sm:flex-row sm:gap-4">
          <router-link to="/soups" class="rounded-md bg-blue-600 px-8 py-3 font-semibold text-white transition hover:bg-blue-700">
            浏览海龟汤
          </router-link>
          <router-link to="/register" class="rounded-md border border-slate-300 px-8 py-3 font-semibold text-slate-800 transition hover:bg-slate-50 dark:border-neutral-700 dark:text-white dark:hover:bg-neutral-900">
            立即加入
          </router-link>
        </div>
      </div>
    </div>

    <!-- 热门海龟汤 -->
    <div class="container mx-auto px-4 py-10 sm:py-16">
      <div class="mb-8 flex min-w-0 items-center justify-between gap-4">
        <h2 class="min-w-0 text-2xl font-bold text-gray-900 dark:text-white sm:text-3xl">热门海龟汤</h2>
        <router-link to="/leaderboard" class="inline-flex shrink-0 items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700 sm:text-base">
          查看更多
          <ArrowRightIcon class="h-4 w-4" aria-hidden="true" />
        </router-link>
      </div>
      
      <div v-if="soupStore.isLoading" class="flex justify-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
      
      <div v-else-if="soupStore.leaderboard.length > 0" class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div
          v-for="(soup, index) in soupStore.leaderboard.slice(0, 6)"
          :key="soup.id"
          class="cursor-pointer rounded-lg border border-slate-200 bg-white p-6 transition hover:border-blue-400 dark:border-neutral-800 dark:bg-neutral-950"
          @click="$router.push(`/soups/${soup.id}`)"
        >
          <div class="flex items-start justify-between mb-4">
            <div class="flex min-w-0 items-center">
              <span :class="[
                'mr-3 flex h-8 w-8 shrink-0 items-center justify-center rounded-full font-bold text-white',
                index === 0 ? 'bg-yellow-500' : index === 1 ? 'bg-gray-400' : index === 2 ? 'bg-orange-500' : 'bg-blue-500'
              ]">
                {{ index + 1 }}
              </span>
              <h3 class="min-w-0 break-words text-lg font-semibold text-gray-900 line-clamp-1 dark:text-white">{{ soup.title }}</h3>
            </div>
          </div>
          <p class="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-2">{{ soup.puzzle }}</p>
          <div class="flex items-center justify-between text-sm">
            <span class="flex items-center text-yellow-500">
              <StarIcon class="mr-1 h-4 w-4" aria-hidden="true" />
              {{ soup.average_score.toFixed(1) }}
            </span>
            <span class="text-gray-500 dark:text-gray-400">{{ soup.rating_count }}人评分</span>
          </div>
        </div>
      </div>
      
      <div v-else class="text-center py-12 text-gray-500 dark:text-gray-400">
        暂无数据
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { ArrowRightIcon } from '@heroicons/vue/24/outline'
import { StarIcon } from '@heroicons/vue/20/solid'
import { useSoupStore } from '@/stores/soup'

const soupStore = useSoupStore()

onMounted(() => {
  soupStore.fetchLeaderboard(10, 'bayesian')
})
</script>
