<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <!-- Hero 区域 -->
    <div class="bg-gradient-to-r from-blue-600 to-purple-600 text-white py-20">
      <div class="container mx-auto px-4 text-center">
        <span class="text-7xl mb-6 block">🐢</span>
        <h1 class="text-5xl font-bold mb-4">海龟汤社区</h1>
        <p class="text-xl mb-8 opacity-90">情境推理游戏 · 解谜爱好者的聚集地</p>
        <div class="flex justify-center space-x-4">
          <router-link to="/soups" class="px-8 py-3 bg-white text-blue-600 rounded-lg font-semibold hover:bg-gray-100 transition">
            浏览海龟汤
          </router-link>
          <router-link to="/register" class="px-8 py-3 border-2 border-white text-white rounded-lg font-semibold hover:bg-white/10 transition">
            立即加入
          </router-link>
        </div>
      </div>
    </div>

    <!-- 特色功能 -->
    <div class="container mx-auto px-4 py-16">
      <h2 class="text-3xl font-bold text-center text-gray-900 dark:text-white mb-12">平台特色</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <!-- 特色 1 -->
        <div class="bg-white dark:bg-gray-800 rounded-xl p-8 shadow-sm hover:shadow-md transition">
          <div class="w-14 h-14 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center mb-4">
            <svg class="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">海量谜题</h3>
          <p class="text-gray-600 dark:text-gray-400">数千道精心制作的海龟汤谜题，涵盖悬疑、恐怖、搞笑、温情等多种题材</p>
        </div>

        <!-- 特色 2 -->
        <div class="bg-white dark:bg-gray-800 rounded-xl p-8 shadow-sm hover:shadow-md transition">
          <div class="w-14 h-14 bg-purple-100 dark:bg-purple-900/30 rounded-full flex items-center justify-center mb-4">
            <svg class="w-8 h-8 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">公平评分</h3>
          <p class="text-gray-600 dark:text-gray-400">采用贝叶斯平均算法，确保评分公正，排行榜真实反映作品质量</p>
        </div>

        <!-- 特色 3 -->
        <div class="bg-white dark:bg-gray-800 rounded-xl p-8 shadow-sm hover:shadow-md transition">
          <div class="w-14 h-14 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mb-4">
            <svg class="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          </div>
          <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">活跃社区</h3>
          <p class="text-gray-600 dark:text-gray-400">关注、好友、评论、比赛，与志同道合的玩家一起交流互动</p>
        </div>
      </div>
    </div>

    <!-- 热门海龟汤 -->
    <div class="container mx-auto px-4 py-16">
      <div class="flex items-center justify-between mb-8">
        <h2 class="text-3xl font-bold text-gray-900 dark:text-white">热门海龟汤</h2>
        <router-link to="/leaderboard" class="text-blue-500 hover:text-blue-600 font-medium">
          查看更多 →
        </router-link>
      </div>
      
      <div v-if="soupStore.isLoading" class="flex justify-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
      
      <div v-else-if="soupStore.leaderboard.length > 0" class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div
          v-for="(soup, index) in soupStore.leaderboard.slice(0, 6)"
          :key="soup.id"
          class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm hover:shadow-md transition cursor-pointer"
          @click="$router.push(`/soups/${soup.id}`)"
        >
          <div class="flex items-start justify-between mb-4">
            <div class="flex items-center">
              <span :class="[
                'w-8 h-8 rounded-full flex items-center justify-center text-white font-bold mr-3',
                index === 0 ? 'bg-yellow-500' : index === 1 ? 'bg-gray-400' : index === 2 ? 'bg-orange-500' : 'bg-blue-500'
              ]">
                {{ index + 1 }}
              </span>
              <h3 class="text-lg font-semibold text-gray-900 dark:text-white line-clamp-1">{{ soup.title }}</h3>
            </div>
          </div>
          <p class="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-2">{{ soup.puzzle }}</p>
          <div class="flex items-center justify-between text-sm">
            <span class="flex items-center text-yellow-500">
              <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
              {{ soup.avg_score.toFixed(1) }}
            </span>
            <span class="text-gray-500 dark:text-gray-400">{{ soup.score_count }}人评分</span>
          </div>
        </div>
      </div>
      
      <div v-else class="text-center py-12 text-gray-500 dark:text-gray-400">
        暂无数据
      </div>
    </div>

    <!-- CTA 区域 -->
    <div class="bg-blue-600 dark:bg-blue-700 text-white py-16 mt-16">
      <div class="container mx-auto px-4 text-center">
        <h2 class="text-3xl font-bold mb-4">准备好开始解谜了吗？</h2>
        <p class="text-lg mb-8 opacity-90">加入我们，发布你的第一个海龟汤，或者挑战已有的谜题</p>
        <router-link to="/register" class="inline-block px-8 py-3 bg-white text-blue-600 rounded-lg font-semibold hover:bg-gray-100 transition">
          免费注册账号
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useSoupStore } from '@/stores/soup'

const soupStore = useSoupStore()

onMounted(() => {
  soupStore.fetchLeaderboard(10, 'bayesian')
})
</script>
