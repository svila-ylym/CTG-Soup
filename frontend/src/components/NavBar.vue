<template>
  <nav class="sticky top-0 z-50 border-b border-slate-200 bg-white dark:border-neutral-800 dark:bg-black" data-layout-region="navigation">
    <div class="container mx-auto px-4">
      <div class="flex min-h-16 items-center justify-between gap-3 py-2">
        <router-link to="/" class="shrink-0 text-lg font-bold text-gray-800 dark:text-white sm:text-xl">
          汤吧社区
        </router-link>

        <button
          class="mobile-menu-button xl:hidden"
          type="button"
          :aria-expanded="mobileOpen"
          :aria-label="mobileOpen ? '关闭导航菜单' : '打开导航菜单'"
          :title="mobileOpen ? '关闭导航菜单' : '打开导航菜单'"
          @click="mobileOpen = !mobileOpen"
        ><Bars3Icon class="h-6 w-6" aria-hidden="true" /></button>

        <!-- 导航链接 -->
        <div class="hidden items-center space-x-6 xl:flex">
          <router-link to="/soups" class="text-gray-600 dark:text-gray-300 hover:text-blue-500 transition">
            海龟汤
          </router-link>
          <router-link to="/leaderboard" class="text-gray-600 dark:text-gray-300 hover:text-blue-500 transition">
            排行榜
          </router-link>
          <router-link to="/posts" class="text-gray-600 dark:text-gray-300 hover:text-blue-500 transition">
            论坛
          </router-link>
          <router-link to="/competitions" class="text-gray-600 dark:text-gray-300 hover:text-blue-500 transition">
            比赛
          </router-link>
        </div>

        <!-- 搜索框 -->
        <div class="mx-1 hidden min-w-0 max-w-md flex-1 lg:mx-4 lg:block">
          <div class="relative">
            <input
              v-model="searchQuery"
              @keyup.enter="handleSearch"
              type="text"
              placeholder="搜索海龟汤、帖子、用户..."
              class="w-full rounded-md border border-gray-300 bg-white px-4 py-2 pl-10 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white"
            />
            <MagnifyingGlassIcon class="absolute left-3 top-2.5 h-5 w-5 text-gray-400" aria-hidden="true" />
          </div>
        </div>

        <!-- 用户操作 -->
        <div class="flex items-center gap-1 sm:gap-4">
          <template v-if="authStore.isAuthenticated">
            <SigninControl class="hidden lg:block" />
            <!-- 通知图标 -->
            <button @click="$router.push('/notifications')" class="relative flex h-10 w-10 items-center justify-center text-gray-600 hover:text-blue-500 dark:text-gray-300" type="button" aria-label="通知" title="通知">
              <BellIcon class="h-6 w-6" aria-hidden="true" />
              <span v-if="unreadCount > 0" class="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] text-white">
                {{ unreadLabel }}
              </span>
            </button>

            <button @click="$router.push('/system-messages')" class="hidden h-10 w-10 items-center justify-center text-gray-600 hover:text-blue-500 dark:text-gray-300 sm:flex" type="button" aria-label="系统消息" title="系统消息">
              <InboxIcon class="h-6 w-6" aria-hidden="true" />
            </button>

            <button @click="$router.push('/messages')" class="hidden h-10 w-10 items-center justify-center text-gray-600 hover:text-blue-500 dark:text-gray-300 sm:flex" type="button" aria-label="私信" title="私信">
              <ChatBubbleLeftRightIcon class="h-6 w-6" aria-hidden="true" />
            </button>

            <!-- 发布按钮 -->
            <router-link to="/soups/create" class="hidden rounded-lg bg-blue-500 px-4 py-2 text-white transition hover:bg-blue-600 sm:inline-flex">
              发布
            </router-link>

            <!-- 用户菜单 -->
            <div class="relative">
              <button @click="showUserMenu = !showUserMenu" class="flex items-center space-x-2">
                <div class="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 font-semibold text-white">
                  {{ userInitial }}
                </div>
              </button>

              <!-- 下拉菜单 -->
              <transition name="fade">
                <div v-if="showUserMenu" class="absolute right-0 mt-2 w-48 bg-white dark:bg-neutral-900 rounded-lg shadow-lg py-2 border border-gray-200 dark:border-neutral-800">
                  <router-link :to="`/profile/${authStore.user?.uid}`" class="block px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-neutral-800">
                    个人主页
                  </router-link>
                  <router-link to="/settings" class="block px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-neutral-800">
                    设置
                  </router-link>
                  <template v-if="authStore.isAdmin">
                    <router-link to="/admin" class="block px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-neutral-800">
                      管理后台
                    </router-link>
                  </template>
                  <router-link v-if="authStore.isRoot" :to="{ path: '/admin/broadcasts', query: { tab: 'email' } }" class="block px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-neutral-800">
                    邮件群发
                  </router-link>
                  <hr class="my-2 border-gray-200 dark:border-neutral-800" />
                  <button @click="handleLogout" class="w-full text-left px-4 py-2 text-red-500 hover:bg-gray-100 dark:hover:bg-neutral-800">
                    退出登录
                  </button>
                </div>
              </transition>
            </div>
          </template>

          <template v-else>
            <router-link to="/login" class="px-4 py-2 text-gray-600 dark:text-gray-300 hover:text-blue-500 transition">
              登录
            </router-link>
            <router-link to="/register" class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition">
              注册
            </router-link>
          </template>

          <!-- 暗黑模式切换 -->
          <button @click="toggleDarkMode" class="flex h-10 w-10 items-center justify-center text-gray-600 hover:text-blue-500 dark:text-gray-300" type="button" aria-label="切换主题" title="切换主题">
            <MoonIcon v-if="!isDark" class="h-6 w-6" aria-hidden="true" />
            <SunIcon v-else class="h-6 w-6" aria-hidden="true" />
          </button>
        </div>
      </div>
      <div v-if="mobileOpen" class="mobile-nav xl:hidden">
        <router-link v-for="item in mobileLinks" :key="item.to" :to="item.to" @click="mobileOpen = false">{{ item.label }}</router-link>
        <router-link v-if="authStore.isAuthenticated" to="/messages" @click="mobileOpen = false">私信</router-link>
        <router-link v-if="authStore.isAuthenticated" to="/system-messages" @click="mobileOpen = false">系统消息</router-link>
        <router-link v-if="authStore.isAuthenticated" to="/notifications" @click="mobileOpen = false">通知</router-link>
        <router-link v-if="authStore.isRoot" :to="{ path: '/admin/broadcasts', query: { tab: 'email' } }" @click="mobileOpen = false">邮件群发</router-link>
        <router-link to="/search" @click="mobileOpen = false">搜索</router-link>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Bars3Icon, BellIcon, ChatBubbleLeftRightIcon, InboxIcon, MagnifyingGlassIcon, MoonIcon, SunIcon } from '@heroicons/vue/24/outline'
import { applyTheme, storedTheme } from '@/utils/theme'
import SigninControl from '@/components/SigninControl.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const searchQuery = ref('')
const showUserMenu = ref(false)
const unreadCount = ref(0)
const unreadLabel = computed(() => unreadCount.value > 99 ? '99+' : String(unreadCount.value))
const isDark = ref(false)
const mobileOpen = ref(false)
const mobileLinks = [
  { to: '/soups', label: '海龟汤' },
  { to: '/leaderboard', label: '排行榜' },
  { to: '/posts', label: '论坛' },
  { to: '/competitions', label: '比赛' },
]

const userInitial = computed(() => {
  return Array.from(authStore.user?.nickname || '')[0]?.toUpperCase() || 'U'
})

const handleSearch = () => {
  const query = searchQuery.value.trim()
  if (query) {
    router.push({ path: '/search', query: { q: query } })
  }
}

watch(
  () => route.query.q,
  (value) => {
    searchQuery.value = typeof value === 'string' ? value : ''
  },
  { immediate: true },
)

watch(
  () => route.fullPath,
  () => {
    mobileOpen.value = false
    showUserMenu.value = false
  },
)

const handleLogout = () => {
  authStore.logout()
  router.push('/')
  showUserMenu.value = false
}

const toggleDarkMode = () => {
  applyTheme(isDark.value ? 'light' : 'dark')
}

const syncThemeState = (event?: Event) => {
  const detail = (event as CustomEvent<{ dark: boolean }> | undefined)?.detail
  isDark.value = detail?.dark ?? document.documentElement.classList.contains('dark')
}

// 点击外部关闭菜单
const closeMenu = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  if (!target.closest('.relative')) {
    showUserMenu.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', closeMenu)
  window.addEventListener('themechange', syncThemeState)
  applyTheme(storedTheme())
  syncThemeState()
})

onUnmounted(() => {
  document.removeEventListener('click', closeMenu)
  window.removeEventListener('themechange', syncThemeState)
})
</script>
