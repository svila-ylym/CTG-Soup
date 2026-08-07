<template>
  <nav class="bg-white dark:bg-gray-800 shadow-md sticky top-0 z-50">
    <div class="container mx-auto px-4">
      <div class="flex items-center justify-between h-16">
        <!-- Logo -->
        <router-link to="/" class="flex items-center space-x-2">
          <span class="text-2xl">🐢</span>
          <span class="text-xl font-bold text-gray-800 dark:text-white">海龟汤社区</span>
        </router-link>

        <!-- 导航链接 -->
        <div class="hidden md:flex items-center space-x-6">
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
        <div class="flex-1 max-w-md mx-4">
          <div class="relative">
            <input
              v-model="searchQuery"
              @keyup.enter="handleSearch"
              type="text"
              placeholder="搜索海龟汤、帖子、用户..."
              class="w-full px-4 py-2 pl-10 rounded-full border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <svg class="absolute left-3 top-2.5 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>

        <!-- 用户操作 -->
        <div class="flex items-center space-x-4">
          <template v-if="authStore.isAuthenticated">
            <!-- 通知图标 -->
            <button @click="$router.push('/notifications')" class="relative p-2 text-gray-600 dark:text-gray-300 hover:text-blue-500">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              <span v-if="unreadCount > 0" class="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                {{ unreadCount }}
              </span>
            </button>

            <!-- 消息图标 -->
            <button @click="$router.push('/messages')" class="p-2 text-gray-600 dark:text-gray-300 hover:text-blue-500">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </button>

            <!-- 发布按钮 -->
            <router-link to="/soups/create" class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition">
              发布海龟汤
            </router-link>

            <!-- 用户菜单 -->
            <div class="relative">
              <button @click="showUserMenu = !showUserMenu" class="flex items-center space-x-2">
                <div class="w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center text-white font-semibold">
                  {{ userInitial }}
                </div>
              </button>

              <!-- 下拉菜单 -->
              <transition name="fade">
                <div v-if="showUserMenu" class="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg py-2 border border-gray-200 dark:border-gray-700">
                  <router-link :to="`/profile/${authStore.user?.uid}`" class="block px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700">
                    个人主页
                  </router-link>
                  <router-link to="/settings" class="block px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700">
                    设置
                  </router-link>
                  <template v-if="authStore.isAdmin">
                    <router-link to="/admin" class="block px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700">
                      管理后台
                    </router-link>
                  </template>
                  <hr class="my-2 border-gray-200 dark:border-gray-700" />
                  <button @click="handleLogout" class="w-full text-left px-4 py-2 text-red-500 hover:bg-gray-100 dark:hover:bg-gray-700">
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
          <button @click="toggleDarkMode" class="p-2 text-gray-600 dark:text-gray-300 hover:text-blue-500">
            <svg v-if="!isDark" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
            <svg v-else class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const searchQuery = ref('')
const showUserMenu = ref(false)
const unreadCount = ref(0)
const isDark = ref(false)

const userInitial = computed(() => {
  return authStore.user?.nickname?.charAt(0).toUpperCase() || 'U'
})

const handleSearch = () => {
  if (searchQuery.value.trim()) {
    router.push({ path: '/search', query: { q: searchQuery.value } })
    searchQuery.value = ''
  }
}

const handleLogout = () => {
  authStore.logout()
  router.push('/')
  showUserMenu.value = false
}

const toggleDarkMode = () => {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('dark')
  localStorage.setItem('darkMode', isDark.value.toString())
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
  // 读取暗黑模式偏好
  isDark.value = localStorage.getItem('darkMode') === 'true'
  if (isDark.value) {
    document.documentElement.classList.add('dark')
  }
})

onUnmounted(() => {
  document.removeEventListener('click', closeMenu)
})
</script>
