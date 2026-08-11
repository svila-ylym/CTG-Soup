<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { searchApi } from '@/api/search'
import { extractApiError } from '@/utils/auth'
import { competitionBorderStyle } from '@/utils/competitionBorder'
import type {
  SearchPost,
  SearchSectionState,
  SearchSoup,
  SearchUser,
} from '@/types'

type SearchKind = 'users' | 'posts' | 'turtle-soups'
type SearchMode = 'all' | SearchKind
type SearchItem = SearchUser | SearchPost | SearchSoup

const route = useRoute()
const router = useRouter()
const query = ref('')
const mode = ref<SearchMode>('all')
const searched = ref(false)
const requestVersion = ref(0)

const sections = reactive<{
  users: SearchSectionState<SearchUser>
  posts: SearchSectionState<SearchPost>
  'turtle-soups': SearchSectionState<SearchSoup>
}>({
  users: { items: [], loading: false, error: '' },
  posts: { items: [], loading: false, error: '' },
  'turtle-soups': { items: [], loading: false, error: '' },
})

const allKinds: SearchKind[] = ['users', 'posts', 'turtle-soups']
const visibleKinds = computed<SearchKind[]>(() =>
  mode.value === 'all' ? allKinds : [mode.value],
)
const loading = computed(() => visibleKinds.value.some((kind) => sections[kind].loading))
const hasResults = computed(() =>
  visibleKinds.value.some((kind) => sections[kind].items.length > 0),
)
const hasErrors = computed(() =>
  visibleKinds.value.some((kind) => Boolean(sections[kind].error)),
)

function requestKind(kind: SearchKind, value: string, trackEgg = false): Promise<SearchItem[]> {
  if (kind === 'users') {
    return searchApi.users(value, 1, 20, trackEgg).then((response) => response.data.items)
  }
  if (kind === 'posts') {
    return searchApi.posts(value, 1, 20, trackEgg).then((response) => response.data.items)
  }
  return searchApi.soups(value, 1, 20, trackEgg).then((response) => response.data.items)
}

function setItems(kind: SearchKind, items: SearchItem[]) {
  if (kind === 'users') sections.users.items = items as SearchUser[]
  if (kind === 'posts') sections.posts.items = items as SearchPost[]
  if (kind === 'turtle-soups') {
    sections['turtle-soups'].items = items as SearchSoup[]
  }
}

function resetSection(kind: SearchKind) {
  sections[kind].items = []
  sections[kind].loading = false
  sections[kind].error = ''
}

async function loadKinds(kinds: SearchKind[], value: string) {
  const version = ++requestVersion.value
  searched.value = true
  for (const kind of kinds) {
    sections[kind].items = []
    sections[kind].loading = true
    sections[kind].error = ''
  }

  const results = await Promise.allSettled(
    kinds.map((kind, index) => requestKind(kind, value, index === 0)),
  )
  if (version !== requestVersion.value) return

  results.forEach((result, index) => {
    const kind = kinds[index]
    if (result.status === 'fulfilled') {
      setItems(kind, result.value)
    } else {
      sections[kind].error = extractApiError(result.reason, '该分类搜索失败')
    }
    sections[kind].loading = false
  })
}

function runSearch() {
  const value = query.value.trim()
  if (!value) return
  const currentQuery = typeof route.query.q === 'string' ? route.query.q : ''
  if (currentQuery === value) {
    void loadKinds(visibleKinds.value, value)
    return
  }
  void router.push({ path: '/search', query: { q: value } })
}

function retry(kind: SearchKind) {
  const value = query.value.trim()
  if (value) void loadKinds([kind], value)
}

watch(
  () => route.query.q,
  (value) => {
    query.value = typeof value === 'string' ? value : ''
    const normalized = query.value.trim()
    if (normalized) {
      for (const kind of allKinds) resetSection(kind)
      void loadKinds(visibleKinds.value, normalized)
    } else {
      searched.value = false
      requestVersion.value += 1
      for (const kind of allKinds) resetSection(kind)
    }
  },
  { immediate: true },
)
</script>

<template>
  <main class="page-shell">
    <div class="page-container">
      <div class="mx-auto max-w-4xl">
        <h1 class="section-title text-3xl">搜索</h1>
        <form class="mt-5 flex flex-col gap-3 sm:flex-row" @submit.prevent="runSearch">
          <input
            v-model="query"
            class="form-control flex-1"
            placeholder="搜索海龟汤、帖子或用户…"
            aria-label="搜索关键词"
          >
          <select v-model="mode" class="form-control sm:w-44" aria-label="搜索分类">
            <option value="all">全部</option>
            <option value="turtle-soups">海龟汤</option>
            <option value="posts">帖子</option>
            <option value="users">用户</option>
          </select>
          <button class="btn-primary" :disabled="loading || !query.trim()">
            {{ loading ? '搜索中…' : '搜索' }}
          </button>
        </form>

        <p v-if="!searched" class="mt-10 text-center text-slate-500">
          输入关键词开始搜索。
        </p>
        <p
          v-else-if="!loading && !hasResults && !hasErrors"
          class="mt-10 break-words text-center text-slate-500"
        >
          没有找到“{{ query }}”相关结果。
        </p>

        <div v-else class="mt-8 divide-y divide-slate-200 dark:divide-neutral-800">
          <section v-if="visibleKinds.includes('users')" class="py-6">
            <div class="flex items-center justify-between">
              <h2 class="section-title">用户</h2>
              <button
                v-if="sections.users.error"
                class="text-sm text-blue-600 hover:underline"
                type="button"
                @click="retry('users')"
              >重新加载</button>
            </div>
            <p v-if="sections.users.loading" class="mt-4 text-sm text-slate-500">加载中…</p>
            <p v-else-if="sections.users.error" class="mt-4 break-words text-sm text-red-700">
              {{ sections.users.error }}
            </p>
            <div v-else class="mt-4 grid gap-2 sm:grid-cols-2">
              <router-link
                v-for="user in sections.users.items"
                :key="user.uid"
                :to="`/profile/${user.uid}`"
                class="flex items-center gap-3 p-2 hover:bg-slate-50 dark:hover:bg-neutral-800"
              >
                <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-100 font-semibold text-blue-700">
                  {{ user.nickname.slice(0, 1) || 'U' }}
                </span>
                <span class="min-w-0">
                  <strong class="block truncate">{{ user.nickname }}</strong>
                  <small class="block truncate text-slate-500">@{{ user.username }} · UID {{ user.uid }}</small>
                </span>
              </router-link>
            </div>
          </section>

          <section v-if="visibleKinds.includes('posts')" class="py-6">
            <div class="flex items-center justify-between">
              <h2 class="section-title">帖子</h2>
              <button
                v-if="sections.posts.error"
                class="text-sm text-blue-600 hover:underline"
                type="button"
                @click="retry('posts')"
              >重新加载</button>
            </div>
            <p v-if="sections.posts.loading" class="mt-4 text-sm text-slate-500">加载中…</p>
            <p v-else-if="sections.posts.error" class="mt-4 break-words text-sm text-red-700">
              {{ sections.posts.error }}
            </p>
            <div v-else class="mt-4 space-y-4">
              <router-link
                v-for="post in sections.posts.items"
                :key="post.id"
                :to="`/posts/${post.id}`"
                class="block border-b border-slate-100 pb-4 last:border-0 dark:border-neutral-800"
              >
                <strong class="block break-words">{{ post.title }}</strong>
                <span class="mt-1 line-clamp-2 block break-words text-sm text-slate-500">{{ post.excerpt }}</span>
              </router-link>
            </div>
          </section>

          <section v-if="visibleKinds.includes('turtle-soups')" class="py-6">
            <div class="flex items-center justify-between">
              <h2 class="section-title">海龟汤</h2>
              <button
                v-if="sections['turtle-soups'].error"
                class="text-sm text-blue-600 hover:underline"
                type="button"
                @click="retry('turtle-soups')"
              >重新加载</button>
            </div>
            <p v-if="sections['turtle-soups'].loading" class="mt-4 text-sm text-slate-500">加载中…</p>
            <p v-else-if="sections['turtle-soups'].error" class="mt-4 break-words text-sm text-red-700">
              {{ sections['turtle-soups'].error }}
            </p>
            <div v-else class="mt-4 space-y-4">
              <router-link
                v-for="soup in sections['turtle-soups'].items"
                :key="soup.id"
                :to="`/soups/${soup.id}`"
                class="competition-border-surface block rounded-md border border-slate-200 p-4 dark:border-neutral-800"
                :style="competitionBorderStyle(soup.competition_colors)"
              >
                <strong class="block break-words">{{ soup.title }}</strong>
                <span class="mt-1 line-clamp-2 block break-words text-sm text-slate-500">{{ soup.puzzle_excerpt }}</span>
                <small class="mt-1 block text-slate-400">
                  评分 {{ soup.rating_count ? soup.average_score.toFixed(1) : '暂无' }}
                </small>
              </router-link>
            </div>
          </section>
        </div>
      </div>
    </div>
  </main>
</template>
