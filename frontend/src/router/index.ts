import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomeView.vue'),
    meta: { title: '首页' },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '登录', requiresAuth: false },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { title: '注册', requiresAuth: false },
  },
  {
    path: '/soups',
    name: 'Soups',
    component: () => import('@/views/soup/SoupListView.vue'),
    meta: { title: '海龟汤列表' },
  },
  {
    path: '/soups/create',
    name: 'CreateSoup',
    component: () => import('@/views/soup/SoupCreateView.vue'),
    meta: { title: '发布海龟汤', requiresAuth: true },
  },
  {
    path: '/soups/:id',
    name: 'SoupDetail',
    component: () => import('@/views/soup/SoupDetailView.vue'),
    meta: { title: '海龟汤详情' },
  },
  {
    path: '/leaderboard',
    name: 'Leaderboard',
    component: () => import('@/views/LeaderboardView.vue'),
    meta: { title: '排行榜' },
  },
  {
    path: '/posts',
    name: 'Posts',
    component: () => import('@/views/post/PostListView.vue'),
    meta: { title: '论坛' },
  },
  {
    path: '/posts/:id',
    name: 'PostDetail',
    component: () => import('@/views/post/PostDetailView.vue'),
    meta: { title: '帖子详情' },
  },
  {
    path: '/competitions',
    name: 'Competitions',
    component: () => import('@/views/competition/CompetitionListView.vue'),
    meta: { title: '比赛列表' },
  },
  {
    path: '/competitions/:id',
    name: 'CompetitionDetail',
    component: () => import('@/views/competition/CompetitionDetailView.vue'),
    meta: { title: '比赛详情' },
  },
  {
    path: '/profile/:uid',
    name: 'Profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { title: '个人主页' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { title: '设置', requiresAuth: true },
  },
  {
    path: '/messages',
    name: 'Messages',
    component: () => import('@/views/MessageView.vue'),
    meta: { title: '消息', requiresAuth: true },
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('@/views/admin/AdminDashboard.vue'),
    meta: { title: '管理后台', requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/search',
    name: 'Search',
    component: () => import('@/views/SearchView.vue'),
    meta: { title: '搜索' },
  },
  {
    path: '/notifications',
    name: 'Notifications',
    component: () => import('@/views/NotificationView.vue'),
    meta: { title: '通知', requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = `${to.meta.title || '海龟汤社区'} - Turtle Soup`
  
  const token = localStorage.getItem('access_token')
  const requiresAuth = to.meta.requiresAuth !== false
  const requiresAdmin = to.meta.requiresAdmin === true
  
  if (requiresAuth && !token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }
  
  if (requiresAdmin) {
    // 这里可以检查用户角色
    const userRole = localStorage.getItem('user_role')
    if (userRole !== 'admin' && userRole !== 'root') {
      next({ name: 'Home' })
      return
    }
  }
  
  next()
})

export default router
