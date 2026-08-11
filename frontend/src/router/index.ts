import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

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
    meta: { title: '登录', guestOnly: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { title: '注册', guestOnly: true },
  },
  {
    path: '/verify-email',
    name: 'VerifyEmail',
    component: () => import('@/views/VerifyEmailView.vue'),
    meta: { title: '邮箱验证', requiresAuth: false },
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/views/ForgotPasswordView.vue'),
    meta: { title: '忘记密码', requiresAuth: false },
  },
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: () => import('@/views/ResetPasswordView.vue'),
    meta: { title: '重置密码', requiresAuth: false },
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
    component: () => import('@/views/SoupCreateView.vue'),
    meta: { title: '发布海龟汤', requiresAuth: true },
  },
  {
    path: '/soups/:id/edit',
    name: 'EditSoup',
    component: () => import('@/views/SoupEditView.vue'),
    meta: { title: '修改海龟汤', requiresAuth: true },
  },
  {
    path: '/soups/:id',
    name: 'SoupDetail',
    component: () => import('@/views/SoupDetailView.vue'),
    meta: { title: '海龟汤详情' },
  },
  {
    path: '/collections/:id',
    name: 'CollectionDetail',
    component: () => import('@/views/CollectionDetailView.vue'),
    meta: { title: '合集详情' },
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
    component: () => import('@/views/PostListView.vue'),
    meta: { title: '论坛' },
  },
  {
    path: '/posts/:id/edit',
    name: 'EditPost',
    component: () => import('@/views/PostEditView.vue'),
    meta: { title: '修改帖子', requiresAuth: true },
  },
  {
    path: '/posts/:id',
    name: 'PostDetail',
    component: () => import('@/views/PostDetailView.vue'),
    meta: { title: '帖子详情' },
  },
  {
    path: '/competitions',
    name: 'Competitions',
    component: () => import('@/views/CompetitionListView.vue'),
    meta: { title: '比赛列表' },
  },
  {
    path: '/competitions/create',
    name: 'CreateCompetition',
    component: () => import('@/views/CompetitionCreateView.vue'),
    meta: { title: '发布比赛', requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/competitions/:id/edit',
    name: 'EditCompetition',
    component: () => import('@/views/CompetitionEditView.vue'),
    meta: { title: '修改比赛', requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/competitions/:id',
    name: 'CompetitionDetail',
    component: () => import('@/views/CompetitionDetailView.vue'),
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
    meta: { title: '私信', requiresAuth: true },
  },
  {
    path: '/system-messages',
    name: 'SystemMessages',
    component: () => import('@/views/SystemMessageView.vue'),
    meta: { title: '系统消息', requiresAuth: true },
  },
  {
    path: '/admin/broadcasts',
    name: 'BroadcastCenter',
    component: () => import('@/views/admin/BroadcastCenterView.vue'),
    meta: { title: '广播中心', requiresAuth: true, requiresRoot: true },
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
  {
    path: '/error/:code(4\\d\\d|5\\d\\d)',
    name: 'Error',
    component: () => import('@/views/ErrorView.vue'),
    meta: { title: '错误' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/ErrorView.vue'),
    meta: { title: '页面不存在' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach(async (to, _from, next) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - 汤吧社区` : '汤吧社区'

  const auth = useAuthStore()
  await auth.init()
  const token = auth.accessToken
  const requiresAuth = to.meta.requiresAuth === true
  const guestOnly = to.meta.guestOnly === true
  const requiresAdmin = to.meta.requiresAdmin === true
  const requiresRoot = to.meta.requiresRoot === true
  
  if (requiresAuth && !token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }

  if (guestOnly && token) {
    next({ name: 'Home' })
    return
  }
  
  if (requiresAdmin) {
    // 这里可以检查用户角色
    const userRole = auth.user?.role
    if (userRole !== 'admin' && userRole !== 'root') {
      next({ name: 'Home' })
      return
    }
  }

  if (requiresRoot && auth.user?.role !== 'root') {
    next({ name: 'Home' })
    return
  }
  
  next()
})

export default router
