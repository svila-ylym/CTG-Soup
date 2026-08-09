<template>
  <main class="flex min-h-screen items-center justify-center bg-white px-4 py-12 dark:bg-black">
    <div class="max-w-md w-full">
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">创建账号</h1>
      </div>

      <!-- 注册表单 -->
      <div class="border-y border-slate-200 bg-white py-8 dark:border-neutral-800 dark:bg-black sm:px-8">
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
              class="form-control mt-1"
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
              class="form-control mt-1"
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
              class="form-control mt-1"
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
              class="form-control mt-1"
              placeholder="请再次输入密码"
            />
          </div>

          <!-- 错误提示 -->
          <div v-if="errorMessage" class="break-words rounded-lg bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
            {{ errorMessage }}
          </div>

          <!-- 提交按钮 -->
          <button
            type="submit"
            :disabled="isLoading"
            class="flex w-full justify-center rounded-md border border-transparent bg-blue-600 px-4 py-3 text-sm font-medium text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span v-if="isLoading">注册中…</span>
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
  </main>
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

  const result = await authStore.register(
    formData.username,
    formData.username,
    formData.password,
    formData.email,
  )

  if (result.success) {
    // 显示成功提示
    if ((window as any).showToast) {
      (window as any).showToast('注册成功！请登录', 'success')
    }
    router.push({ path: '/verify-email', query: { email: formData.email } })
  } else {
    errorMessage.value = result.message || '注册失败，请稍后重试'
  }

  isLoading.value = false
}
</script>
