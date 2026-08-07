<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4">
    <div class="max-w-md w-full">
      <!-- Logo -->
      <div class="text-center mb-8">
        <span class="text-6xl">🐢</span>
        <h1 class="mt-4 text-3xl font-bold text-gray-900 dark:text-white">创建账号</h1>
        <p class="mt-2 text-gray-600 dark:text-gray-400">加入海龟汤社区，开始解谜之旅</p>
      </div>

      <!-- 注册表单 -->
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8">
        <form @submit.prevent="handleRegister" class="space-y-6">
          <!-- 用户名 -->
          <div>
            <label for="username" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
              用户名
            </label>
            <input
              id="username"
              v-model="formData.username"
              type="text"
              required
              class="mt-1 block w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="支持中英文，4-20 个字符"
            />
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">支持中英文，4-20 个字符</p>
          </div>

          <!-- 邮箱 -->
          <div>
            <label for="email" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
              邮箱
            </label>
            <input
              id="email"
              v-model="formData.email"
              type="email"
              required
              class="mt-1 block w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="请输入您的邮箱"
            />
          </div>

          <!-- 密码 -->
          <div>
            <label for="password" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
              密码
            </label>
            <input
              id="password"
              v-model="formData.password"
              type="password"
              required
              class="mt-1 block w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="长度≥8 位，包含大小写字母与数字"
            />
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">长度≥8 位，包含大小写字母与数字</p>
          </div>

          <!-- 确认密码 -->
          <div>
            <label for="confirmPassword" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
              确认密码
            </label>
            <input
              id="confirmPassword"
              v-model="formData.confirmPassword"
              type="password"
              required
              class="mt-1 block w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="请再次输入密码"
            />
          </div>

          <!-- 错误提示 -->
          <div v-if="errorMessage" class="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm rounded-lg p-3">
            {{ errorMessage }}
          </div>

          <!-- 提交按钮 -->
          <button
            type="submit"
            :disabled="isLoading"
            class="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-500 hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            <span v-if="isLoading">注册中...</span>
            <span v-else>注册</span>
          </button>
        </form>

        <!-- 登录链接 -->
        <div class="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
          已有账号？
          <router-link to="/login" class="text-blue-500 hover:text-blue-600 font-medium">
            立即登录
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const formData = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
})

const isLoading = ref(false)
const errorMessage = ref('')

const handleRegister = async () => {
  // 验证密码匹配
  if (formData.password !== formData.confirmPassword) {
    errorMessage.value = '两次输入的密码不一致'
    return
  }

  // 验证密码强度
  if (formData.password.length < 8) {
    errorMessage.value = '密码长度必须大于等于 8 位'
    return
  }

  const hasUpperCase = /[A-Z]/.test(formData.password)
  const hasLowerCase = /[a-z]/.test(formData.password)
  const hasNumber = /[0-9]/.test(formData.password)

  if (!hasUpperCase || !hasLowerCase || !hasNumber) {
    errorMessage.value = '密码必须包含大小写字母和数字'
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  const result = await authStore.register(formData.username, formData.password, formData.email)

  if (result.success) {
    // 显示成功提示
    if ((window as any).showToast) {
      (window as any).showToast('注册成功！请登录', 'success')
    }
    router.push('/login')
  } else {
    errorMessage.value = result.message || '注册失败，请稍后重试'
  }

  isLoading.value = false
}
</script>
