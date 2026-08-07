<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
    <div class="container mx-auto px-4">
      <!-- 页面标题 -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">海龟汤列表</h1>
        <p class="text-gray-600 dark:text-gray-400">探索精彩的海龟汤谜题，挑战你的推理能力</p>
      </div>

      <!-- 筛选和排序 -->
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-4 mb-6">
        <div class="flex flex-wrap gap-4 items-center justify-between">
          <!-- 标签筛选 -->
          <div class="flex items-center space-x-2">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">标签:</span>
            <select
              v-model="selectedTag"
              @change="fetchSoups"
              class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">全部</option>
              <option value="悬疑">悬疑</option>
              <option value="恐怖">恐怖</option>
              <option value="搞笑">搞笑</option>
              <option value="温情">温情</option>
              <option value="烧脑">烧脑</option>
            </select>
          </div>

          <!-- 排序 -->
          <div class="flex items-center space-x-2">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">排序:</span>
            <select
              v-model="sortBy"
              @change="fetchSoups"
              class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="latest">最新发布</option>
              <option value="hot">最热</option>
              <option value="score">评分最高</option>
            </select>
          </div>

          <!-- 发布按钮 -->
          <router-link
            to="/soups/create"
            class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition flex items-center"
          >
            <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            发布海龟汤
          </router-link>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="soupStore.isLoading" class="flex justify-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>

      <!-- 错误提示 -->
      <div v-else-if="soupStore.error" class="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 p-4 rounded-lg text-center">
        {{ soupStore.error }}
      </div>

      <!-- 海龟汤列表 -->
      <div v-else-if="soupStore.soups.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="soup in soupStore.soups"
          :key="soup.id"
          class="bg-white dark:bg-gray-800 rounded-xl shadow-sm hover:shadow-md transition overflow-hidden cursor-pointer"
          @click="$router.push(`/soups/${soup.id}`)"
        >
          <!-- 卡片头部 -->
          <div class="p-6">
            <!-- 标题 -->
            <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-2 line-clamp-2">
              {{ soup.title }}
            </h3>

            <!-- 谜面预览 -->
            <p class="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-3">
              {{ soup.puzzle }}
            </p>

            <!-- 标签 -->
            <div class="flex flex-wrap gap-2 mb-4">
              <span
                v-for="tag in soup.tags.slice(0, 3)"
                :key="tag"
                class="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 text-xs rounded-full"
              >
                #{{ tag }}
              </span>
            </div>

            <!-- 统计信息 -->
            <div class="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
              <div class="flex items-center space-x-4">
                <span class="flex items-center">
                  <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                  {{ soup.avg_score.toFixed(1) }}
                </span>
                <span class="flex items-center">
                  <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                  </svg>
                  {{ soup.like_count }}
                </span>
                <span class="flex items-center">
                  <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  {{ soup.score_count }}
                </span>
              </div>
            </div>
          </div>

          <!-- 卡片底部 -->
          <div class="px-6 py-3 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-100 dark:border-gray-700">
            <div class="flex items-center justify-between">
              <div class="flex items-center">
                <div class="w-6 h-6 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center text-white text-xs font-semibold mr-2">
                  {{ soup.author?.nickname?.charAt(0).toUpperCase() || 'U' }}
                </div>
                <span class="text-sm text-gray-600 dark:text-gray-400">{{ soup.author?.nickname || '未知' }}</span>
              </div>
              <span class="text-xs text-gray-500 dark:text-gray-400">
                {{ formatDate(soup.created_at) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="text-center py-12">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">暂无海龟汤</h3>
        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">快来发布第一个海龟汤吧！</p>
        <div class="mt-6">
          <router-link
            to="/soups/create"
            class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-500 hover:bg-blue-600"
          >
            <svg class="-ml-1 mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            发布海龟汤
          </router-link>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="soupStore.soups.length > 0" class="mt-8 flex justify-center">
        <nav class="flex items-center space-x-2">
          <button
            @click="changePage(currentPage - 1)"
            :disabled="currentPage === 1"
            class="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
          >
            上一页
          </button>
          <span class="px-4 py-2 text-gray-700 dark:text-gray-300">
            第 {{ currentPage }} 页
          </span>
          <button
            @click="changePage(currentPage + 1)"
            class="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
          >
            下一页
          </button>
        </nav>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useSoupStore } from '@/stores/soup'

const soupStore = useSoupStore()

const selectedTag = ref('')
const sortBy = ref('latest')
const currentPage = ref(1)

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  
  return date.toLocaleDateString('zh-CN')
}

const fetchSoups = () => {
  currentPage.value = 1
  let sortParam = ''
  if (sortBy.value === 'latest') sortParam = 'created_at'
  else if (sortBy.value === 'hot') sortParam = 'likes'
  else if (sortBy.value === 'score') sortParam = 'score'
  
  soupStore.fetchList(1, 20, selectedTag.value || undefined, sortParam || undefined)
}

const changePage = (page: number) => {
  if (page < 1) return
  currentPage.value = page
  
  let sortParam = ''
  if (sortBy.value === 'latest') sortParam = 'created_at'
  else if (sortBy.value === 'hot') sortParam = 'likes'
  else if (sortBy.value === 'score') sortParam = 'score'
  
  soupStore.fetchList(page, 20, selectedTag.value || undefined, sortParam || undefined)
}

onMounted(() => {
  fetchSoups()
})
</script>
