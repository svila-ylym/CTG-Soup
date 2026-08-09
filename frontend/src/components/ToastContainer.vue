<template>
  <div class="fixed inset-x-4 bottom-4 z-50 space-y-2 sm:left-auto sm:right-4 sm:w-full sm:max-w-sm">
    <transition-group name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="[
          'w-full rounded-lg px-4 py-3 text-white shadow-lg sm:px-6',
          toast.type === 'success' ? 'bg-green-500' : '',
          toast.type === 'error' ? 'bg-red-500' : '',
          toast.type === 'warning' ? 'bg-yellow-500' : '',
          toast.type === 'info' ? 'bg-blue-500' : ''
        ]"
      >
        <div class="flex min-w-0 items-start justify-between gap-3">
          <span class="min-w-0 flex-1 break-words">{{ toast.message }}</span>
          <button @click="removeToast(toast.id)" class="flex h-6 w-6 shrink-0 items-center justify-center text-white hover:text-gray-200" type="button" aria-label="关闭通知" title="关闭通知">
            <XMarkIcon class="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>
    </transition-group>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { XMarkIcon } from '@heroicons/vue/24/outline'

interface Toast {
  id: number
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
  duration: number
}

const toasts = ref<Toast[]>([])
let toastId = 0
const toastListener = (event: Event) => {
  const detail = (event as CustomEvent).detail || {}
  addToast(detail.message, detail.type, detail.duration)
}

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
  window.addEventListener('toast', toastListener)
})

onUnmounted(() => {
  window.removeEventListener('toast', toastListener)
})

// 导出供外部调用
;(window as any).showToast = (message: string, type: Toast['type'] = 'info', duration = 3000) => {
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
