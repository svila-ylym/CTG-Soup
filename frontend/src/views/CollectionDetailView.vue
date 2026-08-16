<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { collectionApi } from '@/api/collections'
import { useAuthStore } from '@/stores/auth'
import { extractApiError } from '@/utils/auth'
import { competitionBorderStyle } from '@/utils/competitionBorder'
import { parseUtcDateTime } from '@/utils/datetime'
import type { SoupCollectionDetail } from '@/types'
import LinkifiedText from '@/components/LinkifiedText.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const collection = ref<SoupCollectionDetail | null>(null)
const page = ref(1)
const loading = ref(true)
const error = ref('')

function collectionId(): number | null {
  const id = Number(route.params.id)
  return Number.isInteger(id) && id > 0 ? id : null
}

async function load(targetPage = page.value) {
  const id = collectionId()
  if (id === null) {
    await router.replace({ name: 'Error', params: { code: '404' } })
    return
  }
  loading.value = true
  error.value = ''
  try {
    const response = await collectionApi.get(id, targetPage, 20)
    collection.value = response.data
    page.value = response.data.soups.page
  } catch (cause) {
    if ((cause as any)?.response?.status === 404) {
      await router.replace({ name: 'Error', params: { code: '404' } })
      return
    }
    error.value = extractApiError(cause, '合集加载失败')
  } finally {
    loading.value = false
  }
}

async function changePage(targetPage: number) {
  if (targetPage < 1 || targetPage > (collection.value?.soups.total_pages ?? 1)) return
  await load(targetPage)
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeZone: 'Asia/Shanghai',
  }).format(parseUtcDateTime(value))
}

watch(
  () => route.params.id,
  () => {
    page.value = 1
    collection.value = null
    void load(1)
  },
  { immediate: true },
)
</script>

<template>
  <main class="page-shell">
    <div class="page-container max-w-5xl">
      <p v-if="loading && !collection" class="py-20 text-center text-slate-500">正在加载合集…</p>
      <div v-else-if="error && !collection" class="py-20 text-center">
        <p class="text-red-600">{{ error }}</p>
        <button class="btn-secondary mt-4" type="button" @click="load()">重试</button>
      </div>
      <template v-else-if="collection">
        <header class="border-b border-slate-200 pb-7 dark:border-neutral-800">
          <h1 class="break-words text-3xl font-bold sm:text-4xl"><LinkifiedText :text="collection.name" /></h1>
          <p class="mt-3 text-sm text-slate-500">
            由
            <router-link class="font-medium text-blue-600 hover:underline" :to="`/profile/${collection.owner_uid}`">{{ collection.author.nickname || collection.author.username }}</router-link>
            创建 · {{ collection.soup_count }} 篇公开作品
          </p>
          <p v-if="collection.description" class="mt-5 max-w-3xl break-words whitespace-pre-wrap leading-7 text-slate-700 dark:text-slate-300"><LinkifiedText :text="collection.description" /></p>
        </header>

        <section class="py-7">
          <h2 class="section-title">合集作品</h2>
          <div v-if="collection.soups.items.length" class="mt-5 space-y-3">
            <router-link v-for="soup in collection.soups.items" :key="soup.id" :to="`/soups/${soup.id}`" class="competition-border-surface block rounded-md border border-slate-200 p-4 dark:border-neutral-800" :style="competitionBorderStyle(soup.competition_colors)">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div class="min-w-0 flex-1">
                  <strong class="block break-words text-lg" :class="soup.is_hall_of_fame ? 'hall-title' : ''">{{ soup.title }}</strong>
                  <p class="mt-2 line-clamp-2 break-words text-sm text-slate-600 dark:text-slate-300">{{ soup.puzzle_excerpt }}</p>
                  <div class="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <span>{{ soup.genre }}</span><span aria-hidden="true">·</span><span>{{ soup.soup_color }}</span><span aria-hidden="true">·</span><span>{{ soup.average_score.toFixed(1) }} 分 / {{ soup.rating_count }} 人评分</span><span aria-hidden="true">·</span><span>{{ soup.like_count }} 赞</span>
                  </div>
                </div>
                <time class="shrink-0 text-xs text-slate-400">{{ formatDate(soup.created_at) }}</time>
              </div>
            </router-link>
          </div>
          <div v-else class="mt-5 border-y border-slate-200 py-10 text-center dark:border-neutral-800">
            <p class="text-sm text-slate-500">这个合集还没有公开作品。</p>
            <router-link v-if="auth.user?.uid === collection.owner_uid" class="btn-primary mt-4" to="/soups/create">发布海龟汤</router-link>
          </div>
          <p v-if="error" class="mt-4 text-sm text-red-600">{{ error }}</p>
          <div v-if="(collection.soups.total_pages ?? 0) > 1" class="mt-7 flex items-center justify-center gap-4">
            <button class="btn-secondary" type="button" :disabled="page <= 1 || loading" @click="changePage(page - 1)">上一页</button>
            <span class="text-sm text-slate-500">{{ page }} / {{ collection.soups.total_pages }}</span>
            <button class="btn-secondary" type="button" :disabled="page >= (collection.soups.total_pages ?? 1) || loading" @click="changePage(page + 1)">下一页</button>
          </div>
        </section>
      </template>
    </div>
  </main>
</template>
