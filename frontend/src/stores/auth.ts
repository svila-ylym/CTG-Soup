import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { User, TokenResponse } from '@/types'
import { extractApiError } from '@/utils/auth'
import { applyTheme } from '@/utils/theme'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const accessToken = ref<string>(localStorage.getItem('access_token') || '')
  const refreshToken = ref<string>(localStorage.getItem('refresh_token') || '')
  const isLoading = ref(false)

  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin' || user.value?.role === 'root')
  const isRoot = computed(() => user.value?.role === 'root')

  // 登录
  async function login(username: string, password: string) {
    isLoading.value = true
    try {
      const res = await authApi.login({ username, password })
      setTokens(res.data)
      await fetchCurrentUser()
      return { success: true }
    } catch (error: any) {
      return { success: false, message: extractApiError(error, '登录失败') }
    } finally {
      isLoading.value = false
    }
  }

  // 注册
  async function register(username: string, nickname: string, password: string, email: string) {
    isLoading.value = true
    try {
      await authApi.register({ username, nickname, password, email })
      return { success: true }
    } catch (error: any) {
      return { success: false, message: extractApiError(error, '注册失败') }
    } finally {
      isLoading.value = false
    }
  }

  // 登出
  function logout() {
    user.value = null
    accessToken.value = ''
    refreshToken.value = ''
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_uid')
    localStorage.removeItem('user_role')
  }

  // 设置令牌
  function setTokens(tokens: TokenResponse) {
    accessToken.value = tokens.access_token
    refreshToken.value = tokens.refresh_token
    localStorage.setItem('access_token', tokens.access_token)
    localStorage.setItem('refresh_token', tokens.refresh_token)
  }

  // 获取当前用户
  async function fetchCurrentUser() {
    if (!accessToken.value) return
    try {
      const res = await authApi.getCurrentUser()
      user.value = res.data
      localStorage.setItem('user_uid', String(res.data.uid))
      localStorage.setItem('user_role', res.data.role)
      applyTheme(res.data.theme_preference || 'system')
    } catch (error) {
      logout()
    }
  }

  function setUser(value: User) {
    user.value = value
    localStorage.setItem('user_uid', String(value.uid))
    localStorage.setItem('user_role', value.role)
    applyTheme(value.theme_preference || 'system')
  }

  // 初始化（从本地存储恢复状态）
  function init() {
    if (accessToken.value) {
      fetchCurrentUser()
    }
  }

  return {
    user,
    accessToken,
    refreshToken,
    isLoading,
    isAuthenticated,
    isAdmin,
    isRoot,
    login,
    register,
    logout,
    fetchCurrentUser,
    setUser,
    init,
  }
})
