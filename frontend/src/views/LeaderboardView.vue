<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
    <div class="container mx-auto px-4">
      <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">海龟汤排行榜</h1>
      <p class="text-gray-600 dark:text-gray-400 mb-8">基于贝叶斯平均算法的公正排名</p>

      <!-- 排序切换 -->
      <div class="flex space-x-4 mb-6">
        <button
          @click="fetchLeaderboard('bayesian')"
          :class="[
            'px-4 py-2 rounded-lg transition',
            currentType === 'bayesian'
              ? 'bg-blue-500 text-white'
              : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
          ]"
        >
          贝叶斯评分
        </button>
        <button
          @click="fetchLeaderboard('average')"
          :class="[
            'px-4 py-2 rounded-lg transition',
            currentType === 'average'
              ? 'bg-blue-500 text-white'
              : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
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
          class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm hover:shadow-md transition cursor-pointer flex items-center"
          @click="$router.push(`/soups/${soup.id}`)"
        >
          <!-- 排名 -->
          <div :class="[
            'w-12 h-12 rounded-full flex items-center justify-center text-white font-bold mr-6',
            index === 0 ? 'bg-yellow-500' : index === 1 ? 'bg-gray-400' : index === 2 ? 'bg-orange-500' : 'bg-blue-500'
          ]">
            {{ index + 1 }}
          </div>

          <!-- 内容 -->
          <div class="flex-1">
            <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">{{ soup.title }}</h3>
            <p class="text-gray-600 dark:text-gray-400 text-sm line-clamp-2">{{ soup.puzzle }}</p>
            <div class="flex items-center space-x-4 mt-2 text-sm text-gray-500 dark:text-gray-400">
              <span class="flex items-center text-yellow-500">
                <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                {{ soup.avg_score.toFixed(2) }}
              </span>
              <span>{{ soup.score_count }}人评分</span>
              <span>{{ soup.like_count }}次点赞</span>
            </div>
          </div>

          <!-- 作者 -->
          <div class="ml-6 text-right">
            <div class="w-10 h-10 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center text-white font-semibold ml-auto mb-2">
              {{ soup.author?.nickname?.charAt(0).toUpperCase() || 'U' }}
            </div>
            <span class="text-sm text-gray-600 dark:text-gray-400">{{ soup.author?.nickname || '未知' }}</span>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="text-center py-12">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">暂无数据</h3>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
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
