<template>
  <main class="page-shell">
    <div class="page-container">
      <!-- 页面标题 -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">海龟汤列表</h1>
      </div>

      <!-- 筛选和排序 -->
      <div class="mb-6 border-y border-slate-200 bg-white py-4 dark:border-neutral-800 dark:bg-black">
        <div class="flex flex-wrap gap-4 items-center justify-between">
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">分类:</span>
            <select
              v-model="selectedGenre"
              @change="fetchSoups"
              class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white"
            >
              <option value="">全部流派</option>
              <option value="本格">本格</option>
              <option value="变格">变格</option>
              <option value="鳖汤">鳖汤</option>
            </select>
            <select
              v-model="selectedColor"
              @change="fetchSoups"
              class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white"
            >
              <option value="">全部汤色</option>
              <option value="清汤">清汤</option>
              <option value="红汤">红汤</option>
              <option value="黑汤">黑汤</option>
            </select>
          </div>
          <!-- 标签筛选 -->
          <div class="flex items-center space-x-2">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">标签:</span>
            <select
              v-model="selectedTagId"
              @change="fetchSoups"
              class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white"
            >
              <option value="">全部</option>
              <option v-for="tag in availableTags" :key="tag.id" :value="tag.id">{{ tag.name }}</option>
            </select>
          </div>

          <!-- 排序 -->
          <div class="flex items-center space-x-2">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">排序:</span>
            <select
              v-model="sortBy"
              @change="fetchSoups"
              class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white"
            >
              <option value="latest">最新发布</option>
              <option value="hot">最热</option>
              <option value="score">评分最高</option>
            </select>
          </div>

          <!-- 发布按钮 -->
          <router-link
            to="/soups/create"
            class="flex min-h-10 items-center rounded-md bg-blue-600 px-4 py-2 text-white transition hover:bg-blue-700"
          >
            <PlusIcon class="mr-2 h-5 w-5" aria-hidden="true" />
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
          class="competition-border-surface cursor-pointer overflow-hidden rounded-lg border border-slate-200 bg-white transition hover:border-blue-400 dark:border-neutral-800 dark:bg-neutral-950"
          :style="competitionBorderStyle(soup.competition_colors)"
          @click="$router.push(`/soups/${soup.id}`)"
        >
          <!-- 卡片头部 -->
          <div class="p-6">
            <!-- 标题 -->
            <h3 class="mb-2 line-clamp-2 break-words text-xl font-semibold" :class="soup.is_hall_of_fame ? 'hall-title' : 'text-gray-900 dark:text-white'">
              <LinkifiedText :text="soup.title" />
            </h3>

            <div class="mb-3 flex flex-wrap gap-2">
              <span :class="genreBadgeClass(soup.genre)">流派 · {{ soup.genre }}</span>
              <span :class="soupColorBadgeClass(soup.soup_color)">汤色 · {{ soup.soup_color }}</span>
            </div>

            <!-- 谜面预览 -->
            <p class="mb-4 line-clamp-3 break-words text-sm text-gray-600 dark:text-gray-400">
              <LinkifiedText :text="soup.puzzle" />
            </p>

            <!-- 标签 -->
            <div v-if="soup.tags.length" class="mb-4 flex flex-wrap gap-2">
              <span
                v-for="tag in soup.tags.slice(0, 3)"
                :key="tag.id"
                class="max-w-full break-all rounded-full bg-blue-100 px-2 py-1 text-xs text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
              >
                #{{ tag.name }}
              </span>
              <span
                v-if="soup.tags.length > 3"
                class="inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-slate-100 px-2 text-xs text-slate-500 dark:bg-neutral-800 dark:text-slate-400"
                :title="`还有 ${soup.tags.length - 3} 个标签`"
                :aria-label="`还有 ${soup.tags.length - 3} 个标签`"
              >…</span>
            </div>

            <!-- 统计信息 -->
            <div class="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
              <div class="flex flex-wrap items-center gap-x-4 gap-y-1">
                <span class="flex items-center">
                  <StarIcon class="mr-1 h-4 w-4" aria-hidden="true" />
                  {{ soup.average_score.toFixed(1) }}
                </span>
                <button
                  class="inline-flex items-center font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                  type="button"
                  @click.stop="openRatings(soup)"
                >
                  <UserGroupIcon class="mr-1 h-4 w-4" aria-hidden="true" />
                  {{ soup.rating_count }} 人评分 · 查看评分人
                </button>
                <span class="flex items-center">
                  <HeartIcon class="mr-1 h-4 w-4" aria-hidden="true" />
                  {{ soup.like_count }}
                </span>
                <span class="flex items-center">
                  <ChatBubbleLeftRightIcon class="mr-1 h-4 w-4" aria-hidden="true" />
                  {{ soup.comment_count }}
                </span>
              </div>
            </div>
          </div>

          <!-- 卡片底部 -->
          <div class="border-t border-gray-100 bg-white px-6 py-3 dark:border-neutral-800 dark:bg-neutral-950">
            <div class="flex min-w-0 items-center justify-between gap-3">
              <router-link :to="`/profile/${soup.author_uid}`" class="flex min-w-0 items-center hover:text-blue-600" @click.stop>
                <div class="mr-2 flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white">
                  {{ soup.author?.nickname?.charAt(0).toUpperCase() || 'U' }}
                </div>
                <span class="truncate text-sm text-gray-600 dark:text-gray-400" :title="soup.author?.nickname || '未知'">{{ soup.author?.nickname || '未知' }}</span>
              </router-link>
              <span class="shrink-0 text-xs text-gray-500 dark:text-gray-400">
                {{ formatDate(soup.created_at) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="text-center py-12">
        <FaceFrownIcon class="mx-auto h-12 w-12 text-gray-400" aria-hidden="true" />
        <h3 class="mt-2 text-sm font-medium text-gray-900 dark:text-white">暂无海龟汤</h3>
        <div class="mt-6">
          <router-link
            to="/soups/create"
            class="inline-flex min-h-10 items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <PlusIcon class="mr-2 h-5 w-5" aria-hidden="true" />
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
            class="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-neutral-700 dark:text-gray-300 dark:hover:bg-neutral-800"
          >
            上一页
          </button>
          <span class="px-4 py-2 text-gray-700 dark:text-gray-300">
            第 {{ currentPage }} 页
          </span>
          <button
            v-if="currentPage < totalPages"
            @click="changePage(currentPage + 1)"
            class="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 hover:bg-slate-50 dark:border-neutral-700 dark:text-gray-300 dark:hover:bg-neutral-800"
          >
            下一页
          </button>
        </nav>
      </div>

      <SoupRatingsDialog
        :open="selectedRatingsSoup !== null"
        :soup-id="selectedRatingsSoup?.id ?? null"
        :soup-title="selectedRatingsSoup?.title ?? ''"
        @close="closeRatings"
      />
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ChatBubbleLeftRightIcon, FaceFrownIcon, HeartIcon, PlusIcon, UserGroupIcon } from '@heroicons/vue/24/outline'
import { StarIcon } from '@heroicons/vue/20/solid'
import { useSoupStore } from '@/stores/soup'
import { parseUtcDateTime } from '@/utils/datetime'
import { competitionBorderStyle } from '@/utils/competitionBorder'
import { tagApi } from '@/api/tags'
import type { CreateSoupColor, CreateSoupGenre, Tag, TurtleSoup } from '@/types'
import { genreBadgeClass, soupColorBadgeClass } from '@/utils/soupMetadata'
import SoupRatingsDialog from '@/components/SoupRatingsDialog.vue'
import LinkifiedText from '@/components/LinkifiedText.vue'

const soupStore = useSoupStore()

const selectedTagId = ref<number | ''>('')
const availableTags = ref<Tag[]>([])
const sortBy = ref('latest')
const selectedGenre = ref<CreateSoupGenre | ''>('')
const selectedColor = ref<CreateSoupColor | ''>('')
const currentPage = ref(1)
const totalPages = ref(0)
const selectedRatingsSoup = ref<TurtleSoup | null>(null)
const pageSize = 30

function openRatings(soup: TurtleSoup) {
  selectedRatingsSoup.value = soup
}

function closeRatings() {
  selectedRatingsSoup.value = null
}

const formatDate = (dateString: string) => {
  const date = parseUtcDateTime(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  
  return date.toLocaleDateString('zh-CN', { timeZone: 'Asia/Shanghai' })
}

function listFilters() {
  let sortParam = ''
  if (sortBy.value === 'latest') sortParam = 'created_at'
  else if (sortBy.value === 'hot') sortParam = 'likes'
  else if (sortBy.value === 'score') sortParam = 'score'

  return {
    tag_id: selectedTagId.value || undefined,
    genre: selectedGenre.value || undefined,
    soup_color: selectedColor.value || undefined,
    sort_by: sortParam || undefined,
  }
}

async function loadPage(page: number) {
  const result = await soupStore.fetchList(page, pageSize, listFilters())
  currentPage.value = result.page
  totalPages.value = result.total_pages ?? 0
}

async function fetchSoups() {
  await loadPage(1)
}

async function changePage(page: number) {
  if (page < 1 || (totalPages.value > 0 && page > totalPages.value)) return
  await loadPage(page)
}

async function loadTags() {
  try {
    const first = await tagApi.list({ page: 1, page_size: 100, sort_by: 'usage_count' })
    const items = [...first.data.items]
    for (let page = 2; page <= (first.data.total_pages ?? 1); page += 1) {
      const response = await tagApi.list({ page, page_size: 100, sort_by: 'usage_count' })
      items.push(...response.data.items)
    }
    availableTags.value = items
  } catch {
    availableTags.value = []
  }
}

onMounted(() => {
  void loadTags()
  void fetchSoups()
})
</script>
