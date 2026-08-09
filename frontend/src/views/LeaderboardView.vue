<template>
  <main class="page-shell">
    <div class="page-container">
      <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">海龟汤排行榜</h1>
      <p class="text-gray-600 dark:text-gray-400 mb-8">基于贝叶斯平均算法的公正排名</p>

      <!-- 排序切换 -->
      <div class="flex space-x-4 mb-6">
        <button
          @click="fetchLeaderboard('bayesian')"
          :class="[
            'min-h-10 rounded-md px-4 py-2 transition',
            currentType === 'bayesian'
              ? 'bg-blue-500 text-white'
              : 'bg-white dark:bg-neutral-900 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-neutral-800'
          ]"
        >
          贝叶斯评分
        </button>
        <button
          @click="fetchLeaderboard('average')"
          :class="[
            'min-h-10 rounded-md px-4 py-2 transition',
            currentType === 'average'
              ? 'bg-blue-500 text-white'
              : 'bg-white dark:bg-neutral-900 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-neutral-800'
          ]"
        >
          平均分
        </button>
      </div>

      <!-- 加载状态 -->
      <div v-if="soupStore.isLoading" class="flex justify-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>

      <!-- 排行榜列表 -->
      <div v-else-if="soupStore.leaderboard.length > 0" class="space-y-4">
        <div
          v-for="(soup, index) in soupStore.leaderboard"
          :key="soup.id"
          class="grid cursor-pointer grid-cols-[3rem_minmax(0,1fr)] items-center gap-4 rounded-lg border border-slate-200 bg-white p-4 transition hover:border-blue-400 dark:border-neutral-800 dark:bg-neutral-950 sm:grid-cols-[3rem_minmax(0,1fr)_auto] sm:p-5"
          @click="$router.push(`/soups/${soup.id}`)"
        >
          <!-- 排名 -->
          <div :class="[
            'flex h-12 w-12 items-center justify-center rounded-full font-bold text-white',
            index === 0 ? 'bg-yellow-500' : index === 1 ? 'bg-gray-400' : index === 2 ? 'bg-orange-500' : 'bg-blue-500'
          ]">
            {{ index + 1 }}
          </div>

          <!-- 内容 -->
          <div class="min-w-0 flex-1">
            <h3 class="mb-2 break-words text-lg font-semibold text-gray-900 dark:text-white sm:text-xl">{{ soup.title }}</h3>
            <p class="text-gray-600 dark:text-gray-400 text-sm line-clamp-2">{{ soup.puzzle }}</p>
            <div class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-gray-500 dark:text-gray-400">
              <span class="flex items-center text-yellow-500">
                <StarIcon class="mr-1 h-4 w-4" aria-hidden="true" />
                {{ soup.average_score.toFixed(2) }}
              </span>
              <span>{{ soup.rating_count }}人评分</span>
              <span>{{ soup.like_count }}次点赞</span>
            </div>
          </div>

          <!-- 作者 -->
          <div class="col-span-2 mt-2 flex min-w-0 items-center justify-end gap-2 text-right sm:col-span-1 sm:mt-0 sm:block sm:max-w-40">
            <div class="ml-auto flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-600 font-semibold text-white sm:mb-2">
              {{ soup.author?.nickname?.charAt(0).toUpperCase() || 'U' }}
            </div>
            <span class="min-w-0 truncate text-sm text-gray-600 dark:text-gray-400" :title="soup.author?.nickname || '未知'">{{ soup.author?.nickname || '未知' }}</span>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="text-center py-12">
        <ChartBarIcon class="mx-auto h-12 w-12 text-gray-400" aria-hidden="true" />
        <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">暂无数据</h3>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ChartBarIcon } from '@heroicons/vue/24/outline'
import { StarIcon } from '@heroicons/vue/20/solid'
import { useSoupStore } from '@/stores/soup'

const soupStore = useSoupStore()
const currentType = ref<'bayesian' | 'average'>('bayesian')

const fetchLeaderboard = (type: 'bayesian' | 'average') => {
  currentType.value = type
  soupStore.fetchLeaderboard(50, type)
}

onMounted(() => {
  fetchLeaderboard('bayesian')
})
</script>
