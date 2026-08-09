<template>
  <main class="flex min-h-screen items-center justify-center bg-white px-4 py-12 dark:bg-black">
    <div class="max-w-md w-full">
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white">汤吧社区</h1>
      </div>

      <!-- 登录表单 -->
      <div class="border-y border-slate-200 bg-white py-8 dark:border-neutral-800 dark:bg-black sm:px-8">
        <form @submit.prevent="handleLogin" class="space-y-6">
          <!-- 用户名 -->
          <div>
            <label for="username" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
              用户名 / 邮箱
            </label>
            <input
              id="username"
              v-model="formData.username"
              type="text"
              required
              class="form-control mt-1"
              placeholder="请输入用户名或邮箱"
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
              placeholder="请输入密码"
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
            <span v-if="isLoading">登录中…</span>
            <span v-else>登录</span>
          </button>
        </form>

        <!-- 注册链接 -->
        <div class="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
          还没有账号？
          <router-link to="/register" class="text-blue-500 hover:text-blue-600 font-medium">
            立即注册
          </router-link>
        </div>
      </div>

    </div>
  </main>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { safeRedirect } from '@/utils/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formData = reactive({
  username: '',
  password: '',
})

const isLoading = ref(false)
const errorMessage = ref('')

const handleLogin = async () => {
  isLoading.value = true
  errorMessage.value = ''

  const result = await authStore.login(formData.username, formData.password)

  if (result.success) {
    // 存储用户角色
    if (authStore.user) {
      localStorage.setItem('user_role', authStore.user.role)
    }
    
    // 跳转到重定向页面或首页
    router.push(safeRedirect(route.query.redirect))
    
    // 显示成功提示
    if ((window as any).showToast) {
      (window as any).showToast('登录成功！', 'success')
    }
  } else {
    errorMessage.value = result.message || '登录失败，请检查用户名和密码'
  }

  isLoading.value = false
}
</script>
