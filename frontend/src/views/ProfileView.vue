<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { profileApi } from '@/api/profile'
import { useAuthStore } from '@/stores/auth'
import { extractApiError } from '@/utils/auth'
import type { ProfileSoupSummary, PublicProfile } from '@/types'
import { ArrowDownIcon, ArrowUpIcon } from '@heroicons/vue/24/outline'
import SigninControl from '@/components/SigninControl.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const profile = ref<PublicProfile | null>(null)
const loading = ref(true)
const actionLoading = ref(false)
const error = ref('')
const page = ref(1)
const editingFeatured = ref(false)
const featuredIds = ref<number[]>([])

const uid = computed(() => Number(route.params.uid))
const isSelf = computed(() => profile.value?.relation.is_self === true)
const levelPercent = computed(() => {
  const user = profile.value?.user
  if (!user || user.next_level_start === null) return 100
  const span = user.next_level_start - user.level_start
  return span > 0
    ? Math.min(100, Math.max(0, ((user.experience_points - user.level_start) / span) * 100))
    : 0
})
const featuredChoices = computed<ProfileSoupSummary[]>(() => {
  if (!profile.value) return []
  const byId = new Map<number, ProfileSoupSummary>()
  for (const soup of profile.value.featured_soups) byId.set(soup.id, soup)
  for (const soup of profile.value.soups.items) byId.set(soup.id, soup)
  return [...byId.values()]
})

async function loadProfile(targetPage = page.value) {
  if (!Number.isInteger(uid.value) || uid.value <= 0) {
    error.value = '用户 UID 无效'
    loading.value = false
    return
  }
  loading.value = true
  error.value = ''
  try {
    const response = await profileApi.get(uid.value, targetPage)
    profile.value = response.data
    page.value = response.data.soups.page
    featuredIds.value = response.data.featured_soups.map((soup) => soup.id)
  } catch (reason) {
    error.value = extractApiError(reason, '个人主页加载失败')
  } finally {
    loading.value = false
  }
}

async function toggleFollow() {
  if (!auth.isAuthenticated) {
    await router.push({ name: 'Login', query: { redirect: route.fullPath } })
    return
  }
  if (!profile.value || profile.value.relation.is_blocked) return
  actionLoading.value = true
  try {
    if (profile.value.relation.is_following) {
      await profileApi.unfollow(uid.value)
      profile.value.relation.is_following = false
      profile.value.relation.is_friend = false
      profile.value.stats.follower_count = Math.max(0, profile.value.stats.follower_count - 1)
    } else {
      await profileApi.follow(uid.value)
      profile.value.relation.is_following = true
      profile.value.stats.follower_count += 1
    }
  } catch (reason) {
    error.value = extractApiError(reason, '关注操作失败')
  } finally {
    actionLoading.value = false
  }
}

function toggleFeatured(id: number) {
  const index = featuredIds.value.indexOf(id)
  if (index >= 0) {
    featuredIds.value.splice(index, 1)
  } else if (featuredIds.value.length < 5) {
    featuredIds.value.push(id)
  }
}

function moveFeatured(index: number, direction: -1 | 1) {
  const target = index + direction
  if (target < 0 || target >= featuredIds.value.length) return
  const reordered = [...featuredIds.value]
  ;[reordered[index], reordered[target]] = [reordered[target], reordered[index]]
  featuredIds.value = reordered
}

async function saveFeatured() {
  if (!profile.value) return
  actionLoading.value = true
  error.value = ''
  try {
    profile.value.featured_soups = (
      await profileApi.updateFeaturedSoups(featuredIds.value)
    ).data
    editingFeatured.value = false
  } catch (reason) {
    error.value = extractApiError(reason, '代表作保存失败')
  } finally {
    actionLoading.value = false
  }
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium' }).format(new Date(value))
}

watch(
  () => route.params.uid,
  () => {
    page.value = 1
    editingFeatured.value = false
    void loadProfile(1)
  },
  { immediate: true },
)
</script>

<template>
  <main class="page-shell">
    <div v-if="loading" class="page-container py-20 text-center text-slate-500">正在加载个人资料…</div>
    <div v-else-if="error && !profile" class="page-container py-20 text-center text-red-700">{{ error }}</div>
    <div v-else-if="profile" class="page-container max-w-5xl">
      <header class="flex flex-col gap-6 border-b border-slate-200 pb-7 dark:border-neutral-800 sm:flex-row sm:items-start sm:justify-between">
        <div class="flex min-w-0 items-center gap-5">
          <img
            v-if="profile.user.avatar_url"
            :src="profile.user.avatar_url"
            class="h-20 w-20 shrink-0 rounded-full object-cover"
            alt="头像"
          >
          <div v-else class="flex h-20 w-20 shrink-0 items-center justify-center rounded-full bg-blue-100 text-2xl font-bold text-blue-700">
            {{ profile.user.nickname.slice(0, 1) }}
          </div>
          <div class="min-w-0">
            <h1 class="break-words text-2xl font-bold">{{ profile.user.nickname }}</h1>
            <p class="break-words text-sm text-slate-500">@{{ profile.user.username }} · UID {{ profile.user.uid }}</p>
            <div class="mt-2 flex items-center gap-3 text-sm">
              <strong>Lv.{{ profile.user.level }}</strong>
              <span class="text-slate-500">{{ profile.user.experience_points }} 经验</span>
            </div>
            <div class="mt-2 h-2 w-48 max-w-full overflow-hidden bg-slate-200 dark:bg-neutral-800">
              <div class="h-full bg-blue-600" :style="{ width: `${levelPercent}%` }"></div>
            </div>
          </div>
        </div>

        <div class="flex shrink-0 gap-2">
          <template v-if="isSelf">
            <SigninControl />
            <button class="btn-secondary" type="button" @click="router.push('/settings')">编辑资料</button>
          </template>
          <template v-else>
            <button class="btn-primary" type="button" :disabled="actionLoading || profile.relation.is_blocked" @click="toggleFollow">
              {{ profile.relation.is_following ? '取消关注' : '关注' }}
            </button>
            <button class="btn-secondary" type="button" :disabled="profile.relation.is_blocked" @click="router.push({ path: '/messages', query: { uid: profile.user.uid } })">发消息</button>
          </template>
        </div>
      </header>

      <p v-if="profile.user.bio" class="max-w-3xl break-words whitespace-pre-wrap py-6 text-slate-700 dark:text-slate-300">{{ profile.user.bio }}</p>
      <p v-else class="py-6 text-sm text-slate-500">暂无个人简介</p>

      <dl class="grid grid-cols-2 border-y border-slate-200 py-5 text-center dark:border-neutral-800 sm:grid-cols-5">
        <div v-for="item in [
          ['帖子', profile.stats.post_count],
          ['海龟汤', profile.stats.soup_count],
          ['关注者', profile.stats.follower_count],
          ['关注', profile.stats.following_count],
          ['获赞', profile.stats.like_received],
        ]" :key="String(item[0])" class="px-2 py-2">
          <dd class="text-xl font-semibold">{{ item[1] }}</dd>
          <dt class="text-xs text-slate-500">{{ item[0] }}</dt>
        </div>
      </dl>

      <section class="py-7">
        <div class="flex items-center justify-between gap-3">
          <h2 class="section-title">代表作</h2>
          <button v-if="isSelf" class="text-sm text-blue-600 hover:underline" type="button" @click="editingFeatured = !editingFeatured">
            {{ editingFeatured ? '取消编辑' : '管理代表作' }}
          </button>
        </div>

        <div v-if="editingFeatured" class="mt-5 border-y border-slate-200 py-4 dark:border-neutral-800">
          <div class="space-y-2">
            <label v-for="soup in featuredChoices" :key="soup.id" class="flex items-center gap-3 py-2">
              <input type="checkbox" :checked="featuredIds.includes(soup.id)" :disabled="!featuredIds.includes(soup.id) && featuredIds.length >= 5" @change="toggleFeatured(soup.id)">
              <span class="min-w-0 flex-1 truncate">{{ soup.title }}</span>
              <template v-if="featuredIds.includes(soup.id)">
                <button class="flex h-8 w-8 shrink-0 items-center justify-center text-slate-500 hover:text-blue-600" type="button" aria-label="上移" title="上移" @click.prevent="moveFeatured(featuredIds.indexOf(soup.id), -1)"><ArrowUpIcon class="h-4 w-4" aria-hidden="true" /></button>
                <button class="flex h-8 w-8 shrink-0 items-center justify-center text-slate-500 hover:text-blue-600" type="button" aria-label="下移" title="下移" @click.prevent="moveFeatured(featuredIds.indexOf(soup.id), 1)"><ArrowDownIcon class="h-4 w-4" aria-hidden="true" /></button>
              </template>
            </label>
          </div>
          <button class="btn-primary mt-4" type="button" :disabled="actionLoading" @click="saveFeatured">保存代表作</button>
        </div>

        <div v-else-if="profile.featured_soups.length" class="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <router-link
            v-for="soup in profile.featured_soups"
            :key="soup.id"
            :to="`/soups/${soup.id}`"
            class="border border-slate-200 p-4 dark:border-neutral-800"
          >
            <strong class="line-clamp-2 block text-sm">{{ soup.title }}</strong>
            <span class="mt-2 block text-xs text-slate-500">{{ soup.genre }} · {{ soup.soup_color }}</span>
          </router-link>
        </div>
        <p v-else class="mt-4 text-sm text-slate-500">暂未设置代表作</p>
      </section>

      <section class="border-t border-slate-200 py-7 dark:border-neutral-800">
        <h2 class="section-title">已发布海龟汤</h2>
        <div class="mt-5 divide-y divide-slate-200 dark:divide-neutral-800">
          <router-link v-for="soup in profile.soups.items" :key="soup.id" :to="`/soups/${soup.id}`" class="block py-5">
            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0">
                <strong class="block truncate">{{ soup.title }}</strong>
                <p class="mt-1 line-clamp-2 text-sm text-slate-500">{{ soup.puzzle_excerpt }}</p>
              </div>
              <span class="shrink-0 text-xs text-slate-400">{{ formatDate(soup.created_at) }}</span>
            </div>
          </router-link>
        </div>
        <p v-if="!profile.soups.items.length" class="mt-4 text-sm text-slate-500">暂无已发布作品</p>
        <div v-if="profile.soups.total_pages && profile.soups.total_pages > 1" class="mt-6 flex items-center justify-center gap-4">
          <button class="btn-secondary" type="button" :disabled="page <= 1 || loading" @click="loadProfile(page - 1)">上一页</button>
          <span class="text-sm text-slate-500">{{ page }} / {{ profile.soups.total_pages }}</span>
          <button class="btn-secondary" type="button" :disabled="page >= profile.soups.total_pages || loading" @click="loadProfile(page + 1)">下一页</button>
        </div>
      </section>

      <p v-if="error" class="pb-6 text-sm text-red-700">{{ error }}</p>
    </div>
  </main>
</template>
