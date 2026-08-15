<template>
  <nav class="glass-nav sticky top-0 z-50 border-b" data-layout-region="navigation">
    <div class="container mx-auto px-4">
      <div class="flex min-h-16 items-center gap-5 py-2">
        <router-link to="/" class="flex shrink-0 items-center gap-2 text-lg font-bold text-gray-800 dark:text-white sm:text-xl">
          <img src="/icon.ico" alt="汤吧社区图标" class="h-8 w-8 object-contain" />
          <span>汤吧社区</span>
        </router-link>

        <div class="hidden items-center gap-6 xl:flex">
          <router-link v-for="item in browseLinks.slice(1)" :key="item.path" :to="item.path" class="text-gray-600 transition hover:text-blue-500 dark:text-gray-300">
            {{ item.label }}
          </router-link>
        </div>

        <div class="mx-4 hidden min-w-0 max-w-md flex-1 xl:block">
          <form class="relative" @submit.prevent="handleSearch">
            <input
              v-model="searchQuery"
              type="search"
              placeholder="搜索海龟汤、帖子、用户..."
              class="glass-control w-full rounded-md px-4 py-2 pl-10 text-gray-900 outline-none dark:text-white"
            >
            <MagnifyingGlassIcon class="absolute left-3 top-2.5 h-5 w-5 text-gray-400" aria-hidden="true" />
          </form>
        </div>

        <div class="ml-auto hidden items-center gap-4 xl:flex">
          <template v-if="authStore.isAuthenticated">
            <SigninControl />
            <button class="nav-icon-button relative h-10 w-10 dark:text-gray-300" type="button" aria-label="通知" title="通知" @click="$router.push('/notifications')">
              <BellIcon class="h-6 w-6" aria-hidden="true" />
              <span v-if="unreadStore.hasNotifications" class="absolute right-1 top-1 h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-white dark:ring-black" aria-label="有未读通知"></span>
            </button>
            <button class="nav-icon-button relative h-10 w-10 dark:text-gray-300" type="button" aria-label="系统消息" title="系统消息" @click="$router.push('/system-messages')">
              <InboxIcon class="h-6 w-6" aria-hidden="true" />
              <span v-if="unreadStore.hasSystemMessages" class="absolute right-1 top-1 h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-white dark:ring-black" aria-label="有未读系统消息"></span>
            </button>
            <button class="nav-icon-button relative h-10 w-10 dark:text-gray-300" type="button" aria-label="私信" title="私信" @click="$router.push('/messages')">
              <ChatBubbleLeftRightIcon class="h-6 w-6" aria-hidden="true" />
              <span v-if="chatStore.hasUnreadMessages" class="absolute right-1 top-1 h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-white dark:ring-black" aria-label="有未读私信"></span>
            </button>
            <router-link to="/soups/create" class="liquid-primary inline-flex min-h-10 items-center px-4 py-2 text-sm font-bold">发布</router-link>

            <div class="relative">
              <button class="glass-button flex h-10 w-10 items-center justify-center p-1" type="button" aria-label="打开账号菜单" title="账号菜单" @click="showUserMenu = !showUserMenu">
                <span class="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 font-semibold text-white">{{ userInitial }}</span>
              </button>
              <transition name="fade">
                <div v-if="showUserMenu" class="glass-popover absolute right-0 mt-2 w-48 overflow-hidden rounded-md py-2">
                  <router-link :to="`/profile/${authStore.user?.uid}`" class="block px-4 py-2 text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-neutral-800">个人主页</router-link>
                  <router-link to="/settings" class="block px-4 py-2 text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-neutral-800">设置</router-link>
                  <router-link v-if="authStore.isAdmin" to="/admin" class="block px-4 py-2 text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-neutral-800">管理后台</router-link>
                  <router-link v-if="authStore.isRoot" :to="{ path: '/admin/broadcasts', query: { tab: 'email' } }" class="block px-4 py-2 text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-neutral-800">邮件群发</router-link>
                  <hr class="my-2 border-gray-200 dark:border-neutral-800">
                  <button class="w-full px-4 py-2 text-left text-red-500 transition hover:bg-white/60 dark:hover:bg-white/10" type="button" @click="handleLogout">退出登录</button>
                </div>
              </transition>
            </div>
          </template>

          <template v-else>
            <router-link to="/login" class="glass-button inline-flex min-h-10 items-center px-4 py-2 text-gray-600 dark:text-gray-300">登录</router-link>
            <router-link to="/register" class="liquid-primary inline-flex min-h-10 items-center px-4 py-2 font-bold">注册</router-link>
          </template>

          <ThemeToggle id="theme-toggle-btn" :is-dark="isDark" @toggle="toggleDarkMode" />
        </div>

        <button
          ref="mobileMenuButton"
          class="mobile-menu-button glass-button ml-auto xl:hidden"
          type="button"
          :aria-expanded="mobileOpen"
          :aria-label="mobileOpen ? '关闭导航侧栏' : '打开导航侧栏'"
          :title="mobileOpen ? '关闭导航侧栏' : '打开导航侧栏'"
          @click="mobileOpen = true"
        >
          <Bars3Icon class="h-6 w-6" aria-hidden="true" />
        </button>
      </div>
    </div>
  </nav>

  <Teleport to="body">
    <Transition name="mobile-drawer">
      <div v-if="mobileOpen" class="fixed inset-0 z-[80] xl:hidden" role="dialog" aria-modal="true" aria-label="移动端导航">
        <button class="mobile-drawer-backdrop absolute inset-0" type="button" aria-label="关闭导航侧栏" @click="closeMobileMenu"></button>
        <aside class="mobile-drawer-panel glass-drawer absolute bottom-2 right-2 top-2 flex w-[min(23rem,calc(100%-1rem))] flex-col overflow-hidden rounded-2xl">
          <header class="drawer-glass-header flex items-center justify-between gap-4 border-b px-5 pb-4 pt-[calc(1rem+env(safe-area-inset-top))]">
            <div class="flex min-w-0 items-center gap-2">
              <img src="/icon.ico" alt="汤吧社区图标" class="h-8 w-8 shrink-0 object-contain" />
              <div class="min-w-0">
                <p class="truncate text-lg font-bold text-slate-900 dark:text-white">汤吧社区</p>
                <p class="mt-0.5 text-xs text-slate-500">完整导航</p>
              </div>
            </div>
            <button ref="mobileCloseButton" class="glass-button flex h-10 w-10 shrink-0 items-center justify-center text-slate-500 hover:text-slate-900 dark:hover:text-white" type="button" aria-label="关闭导航侧栏" title="关闭" @click="closeMobileMenu">
              <XMarkIcon class="h-6 w-6" aria-hidden="true" />
            </button>
          </header>

          <div class="border-b border-slate-200 p-4 dark:border-neutral-800">
            <form class="drawer-search-panel" role="search" @submit.prevent="handleMobileSearch">
              <div class="drawer-search-field">
                <MagnifyingGlassIcon class="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" aria-hidden="true" />
                <input v-model="searchQuery" class="drawer-search-input form-control glass-control" type="search" placeholder="搜索海龟汤、帖子、用户" aria-label="搜索">
              </div>
              <button class="drawer-search-submit liquid-primary" type="submit" :disabled="!searchQuery.trim()" aria-label="提交搜索">
                <span>搜索</span>
                <ArrowRightIcon class="h-4 w-4" aria-hidden="true" />
              </button>
            </form>
          </div>

          <div class="min-h-0 flex-1 overflow-y-auto px-4 pb-[calc(1.25rem+env(safe-area-inset-bottom))]">
            <div v-if="authStore.isAuthenticated" class="glass-card mt-4 flex items-center gap-3 p-3">
              <span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-blue-600 font-bold text-white">{{ userInitial }}</span>
              <div class="min-w-0">
                <strong class="block truncate text-sm text-slate-900 dark:text-white">{{ authStore.user?.nickname }}</strong>
                <span class="block truncate text-xs text-slate-500">@{{ authStore.user?.username }} · UID {{ authStore.user?.uid }}</span>
              </div>
            </div>

            <section class="drawer-appearance glass-card mt-4 flex items-center justify-between gap-4 p-3.5" aria-labelledby="drawer-appearance-heading">
              <div class="min-w-0">
                <h2 id="drawer-appearance-heading" class="text-sm font-bold text-slate-900 dark:text-white">外观主题</h2>
                <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{{ isDark ? '深色模式' : '浅色模式' }}</p>
              </div>
              <ThemeToggle id="theme-toggle-sidebar" :is-dark="isDark" @toggle="toggleDarkMode" />
            </section>

            <section class="mobile-drawer-section">
              <h2 class="mobile-drawer-heading">浏览</h2>
              <router-link v-for="item in browseLinks" :key="item.path" :to="item.path" class="mobile-drawer-link" :class="isActivePath(item.path) ? 'mobile-drawer-link-active' : ''" @click="closeMobileMenu">
                <component :is="item.icon" class="h-5 w-5 shrink-0" aria-hidden="true" />
                <span>{{ item.label }}</span>
              </router-link>
            </section>

            <section v-if="authStore.isAuthenticated" class="mobile-drawer-section">
              <h2 class="mobile-drawer-heading">消息</h2>
              <router-link to="/notifications" class="mobile-drawer-link" :class="isActivePath('/notifications') ? 'mobile-drawer-link-active' : ''" @click="closeMobileMenu">
                <BellIcon class="h-5 w-5 shrink-0" aria-hidden="true" /><span>通知</span><span v-if="unreadStore.hasNotifications" class="ml-auto h-2.5 w-2.5 rounded-full bg-red-500" aria-label="有未读通知"></span>
              </router-link>
              <router-link to="/messages" class="mobile-drawer-link" :class="isActivePath('/messages') ? 'mobile-drawer-link-active' : ''" @click="closeMobileMenu">
                <ChatBubbleLeftRightIcon class="h-5 w-5 shrink-0" aria-hidden="true" /><span>私信</span><span v-if="chatStore.hasUnreadMessages" class="ml-auto h-2.5 w-2.5 rounded-full bg-red-500" aria-label="有未读私信"></span>
              </router-link>
              <router-link to="/system-messages" class="mobile-drawer-link" :class="isActivePath('/system-messages') ? 'mobile-drawer-link-active' : ''" @click="closeMobileMenu">
                <InboxIcon class="h-5 w-5 shrink-0" aria-hidden="true" /><span>系统消息</span><span v-if="unreadStore.hasSystemMessages" class="ml-auto h-2.5 w-2.5 rounded-full bg-red-500" aria-label="有未读系统消息"></span>
              </router-link>
            </section>

            <section v-if="authStore.isAuthenticated" class="mobile-drawer-section">
              <h2 class="mobile-drawer-heading">创作</h2>
              <router-link to="/soups/create" class="mobile-drawer-link" :class="isActivePath('/soups/create') ? 'mobile-drawer-link-active' : ''" @click="closeMobileMenu">
                <PlusCircleIcon class="h-5 w-5 shrink-0" aria-hidden="true" /><span>发布海龟汤</span>
              </router-link>
              <router-link v-if="authStore.isAdmin" to="/competitions/create" class="mobile-drawer-link" :class="isActivePath('/competitions/create') ? 'mobile-drawer-link-active' : ''" @click="closeMobileMenu">
                <SparklesIcon class="h-5 w-5 shrink-0" aria-hidden="true" /><span>发布比赛</span>
              </router-link>
            </section>

            <section v-if="authStore.isAdmin" class="mobile-drawer-section">
              <h2 class="mobile-drawer-heading">管理</h2>
              <router-link to="/admin" class="mobile-drawer-link" :class="isActivePath('/admin') ? 'mobile-drawer-link-active' : ''" @click="closeMobileMenu">
                <ShieldCheckIcon class="h-5 w-5 shrink-0" aria-hidden="true" /><span>管理后台</span>
              </router-link>
              <router-link v-if="authStore.isRoot" :to="{ path: '/admin/broadcasts', query: { tab: 'email' } }" class="mobile-drawer-link" @click="closeMobileMenu">
                <MegaphoneIcon class="h-5 w-5 shrink-0" aria-hidden="true" /><span>邮件群发</span>
              </router-link>
            </section>

            <section class="mobile-drawer-section">
              <h2 class="mobile-drawer-heading">账号</h2>
              <template v-if="authStore.isAuthenticated">
                <router-link :to="`/profile/${authStore.user?.uid}`" class="mobile-drawer-link" @click="closeMobileMenu"><UserCircleIcon class="h-5 w-5 shrink-0" aria-hidden="true" /><span>个人主页</span></router-link>
                <router-link to="/settings" class="mobile-drawer-link" :class="isActivePath('/settings') ? 'mobile-drawer-link-active' : ''" @click="closeMobileMenu"><Cog6ToothIcon class="h-5 w-5 shrink-0" aria-hidden="true" /><span>设置</span></router-link>
                <div class="px-3 py-2"><SigninControl /></div>
              </template>
              <template v-else>
                <router-link to="/login" class="mobile-drawer-link" @click="closeMobileMenu"><ArrowRightOnRectangleIcon class="h-5 w-5 shrink-0" aria-hidden="true" /><span>登录</span></router-link>
                <router-link to="/register" class="mobile-drawer-link" @click="closeMobileMenu"><UserPlusIcon class="h-5 w-5 shrink-0" aria-hidden="true" /><span>注册</span></router-link>
              </template>
              <button v-if="authStore.isAuthenticated" class="mobile-drawer-link w-full text-red-600 dark:text-red-400" type="button" @click="handleLogout"><ArrowLeftOnRectangleIcon class="h-5 w-5 shrink-0" aria-hidden="true" /><span>退出登录</span></button>
            </section>
          </div>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeftOnRectangleIcon,
  ArrowRightIcon,
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  BellIcon,
  ChatBubbleLeftRightIcon,
  Cog6ToothIcon,
  HomeIcon,
  InboxIcon,
  MagnifyingGlassIcon,
  MegaphoneIcon,
  PlusCircleIcon,
  PuzzlePieceIcon,
  RectangleStackIcon,
  ShieldCheckIcon,
  SparklesIcon,
  TrophyIcon,
  UserCircleIcon,
  UserPlusIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { useUnreadStore } from '@/stores/unread'
import { applyTheme, storedTheme } from '@/utils/theme'
import SigninControl from '@/components/SigninControl.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const chatStore = useChatStore()
const unreadStore = useUnreadStore()

const searchQuery = ref('')
const showUserMenu = ref(false)
const isDark = ref(false)
const mobileOpen = ref(false)
const mobileMenuButton = ref<HTMLButtonElement | null>(null)
const mobileCloseButton = ref<HTMLButtonElement | null>(null)
let previousBodyOverflow = ''

const browseLinks = [
  { path: '/', label: '首页', icon: HomeIcon },
  { path: '/soups', label: '海龟汤', icon: PuzzlePieceIcon },
  { path: '/leaderboard', label: '排行榜', icon: TrophyIcon },
  { path: '/posts', label: '论坛', icon: RectangleStackIcon },
  { path: '/competitions', label: '比赛', icon: SparklesIcon },
]

const userInitial = computed(() => Array.from(authStore.user?.nickname || '')[0]?.toUpperCase() || 'U')

function isActivePath(path: string) {
  return path === '/' ? route.path === '/' : route.path === path || route.path.startsWith(`${path}/`)
}

function handleSearch() {
  const query = searchQuery.value.trim()
  if (query) void router.push({ path: '/search', query: { q: query } })
}

function handleMobileSearch() {
  const query = searchQuery.value.trim()
  if (!query) return
  closeMobileMenu()
  void router.push({ path: '/search', query: { q: query } })
}

function closeMobileMenu() {
  mobileOpen.value = false
}

function handleLogout() {
  closeMobileMenu()
  unreadStore.reset()
  chatStore.reset()
  authStore.logout()
  void router.push('/')
  showUserMenu.value = false
}

function toggleDarkMode() {
  applyTheme(isDark.value ? 'light' : 'dark')
}

function syncThemeState(event?: Event) {
  const detail = (event as CustomEvent<{ dark: boolean }> | undefined)?.detail
  isDark.value = detail?.dark ?? document.documentElement.classList.contains('dark')
}

function closeUserMenu(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest('.relative')) showUserMenu.value = false
}

function closeOnEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') closeMobileMenu()
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
    closeMobileMenu()
    showUserMenu.value = false
  },
)

watch(mobileOpen, async (open) => {
  if (open) {
    previousBodyOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    await nextTick()
    mobileCloseButton.value?.focus()
  } else {
    document.body.style.overflow = previousBodyOverflow
    await nextTick()
    mobileMenuButton.value?.focus()
  }
})

watch(
  () => authStore.user?.uid ?? null,
  (uid) => {
    unreadStore.reset()
    chatStore.reset()
    if (uid === null || !authStore.accessToken) return
    unreadStore.startPolling()
    void chatStore.loadConversations()
    chatStore.connect()
  },
  { immediate: true },
)

onMounted(() => {
  document.addEventListener('click', closeUserMenu)
  window.addEventListener('keydown', closeOnEscape)
  window.addEventListener('themechange', syncThemeState)
  applyTheme(storedTheme())
  syncThemeState()
})

onUnmounted(() => {
  document.removeEventListener('click', closeUserMenu)
  window.removeEventListener('keydown', closeOnEscape)
  window.removeEventListener('themechange', syncThemeState)
  document.body.style.overflow = previousBodyOverflow
  unreadStore.stopPolling()
  chatStore.disconnect()
})
</script>

<style scoped>
.mobile-drawer-enter-active,
.mobile-drawer-leave-active {
  transition: opacity 220ms ease;
}

.mobile-drawer-enter-active .mobile-drawer-panel,
.mobile-drawer-leave-active .mobile-drawer-panel {
  transition: transform 280ms cubic-bezier(.2, .75, .25, 1);
}

.mobile-drawer-enter-from,
.mobile-drawer-leave-to {
  opacity: 0;
}

.mobile-drawer-enter-from .mobile-drawer-panel,
.mobile-drawer-leave-to .mobile-drawer-panel {
  transform: translateX(calc(100% + 1rem));
}

.mobile-drawer-backdrop {
  background: rgba(15, 23, 42, .42);
  -webkit-backdrop-filter: blur(4px) saturate(110%);
  backdrop-filter: blur(4px) saturate(110%);
}

:global(.dark) .mobile-drawer-backdrop {
  background: rgba(0, 0, 0, .64);
}

.drawer-glass-header {
  border-color: color-mix(in srgb, var(--border) 68%, transparent);
  background: rgba(255, 255, 255, .24);
  box-shadow: inset 0 -1px 0 rgba(255, 255, 255, .3);
}

:global(.dark) .drawer-glass-header {
  background: rgba(255, 255, 255, .025);
  box-shadow: inset 0 -1px 0 rgba(255, 255, 255, .05);
}

.drawer-search-panel {
  display: grid;
  gap: .625rem;
  padding: .625rem;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--glass-border) 88%, var(--liquid-accent));
  border-radius: .875rem;
  background: color-mix(in srgb, var(--glass-card) 88%, transparent);
  box-shadow: inset 0 1px 0 var(--glass-highlight), 0 12px 30px rgba(15, 23, 42, .08);
  -webkit-backdrop-filter: blur(22px) saturate(145%);
  backdrop-filter: blur(22px) saturate(145%);
}

.drawer-search-field {
  position: relative;
}

.drawer-search-input {
  width: 100%;
  height: 2.875rem;
  padding: .625rem .875rem .625rem 2.75rem;
  border-radius: .625rem;
  color: rgb(15 23 42);
  outline: none;
}

.drawer-search-submit {
  display: inline-flex;
  width: 100%;
  min-height: 2.75rem;
  align-items: center;
  justify-content: center;
  gap: .5rem;
  padding: .625rem 1rem;
  font-size: .875rem;
  font-weight: 700;
}

.drawer-search-submit:disabled {
  cursor: not-allowed;
  opacity: .45;
  transform: none;
  box-shadow: inset 0 1px 0 var(--glass-highlight), 0 3px 9px rgba(15, 23, 42, .06);
}

:global(.dark) .drawer-search-panel {
  background: color-mix(in srgb, var(--glass-card) 84%, transparent);
  box-shadow: inset 0 1px 0 var(--glass-highlight), 0 14px 34px rgba(0, 0, 0, .28);
}

:global(.dark) .drawer-search-input {
  color: rgb(248 250 252);
}
</style>
