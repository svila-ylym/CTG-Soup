<template>
  <div class="fixed bottom-4 right-4 z-50 space-y-2">
    <transition-group name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="[
          'px-6 py-3 rounded-lg shadow-lg text-white max-w-sm',
          toast.type === 'success' ? 'bg-green-500' : '',
          toast.type === 'error' ? 'bg-red-500' : '',
          toast.type === 'warning' ? 'bg-yellow-500' : '',
          toast.type === 'info' ? 'bg-blue-500' : ''
        ]"
      >
        <div class="flex items-center justify-between">
          <span>{{ toast.message }}</span>
          <button @click="removeToast(toast.id)" class="ml-4 text-white hover:text-gray-200">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </transition-group>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

interface Toast {
  id: number
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
  duration: number
}

const toasts = ref<Toast[]>([])
let toastId = 0

// 监听自定义事件
const addToast = (message: string, type: Toast['type'] = 'info', duration = 3000) => {
  const id = ++toastId
  toasts.value.push({ id, message, type, duration })
  
  setTimeout(() => {
    removeToast(id)
  }, duration)
}

const removeToast = (id: number) => {
  const index = toasts.value.findIndex(t => t.id === id)
  if (index > -1) {
    toasts.value.splice(index, 1)
  }
}

// 暴露全局方法
onMounted(() => {
  window.addEventListener('toast' as any, (event: any) => {
    addToast(event.detail.message, event.detail.type, event.detail.duration)
  })
})

onUnmounted(() => {
  window.removeEventListener('toast' as any)
})

// 导出供外部调用
window.showToast = (message: string, type: Toast['type'] = 'info', duration = 3000) => {
  addToast(message, type, duration)
}
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
