<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" @click.self="close">
    <form class="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-neutral-900" @submit.prevent="submit">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">举报内容</h2>
        <button type="button" class="text-gray-500" @click="close">×</button>
      </div>
      <textarea v-model="reason" required minlength="2" maxlength="2000" class="mt-4 min-h-32 w-full rounded-lg border p-3 dark:border-neutral-700 dark:bg-neutral-800 dark:text-white" placeholder="请说明举报原因" />
      <p v-if="error" class="mt-2 text-sm text-red-500">{{ error }}</p>
      <div class="mt-5 flex justify-end gap-3">
        <button type="button" class="rounded-lg px-4 py-2 text-gray-600" @click="close">取消</button>
        <button :disabled="submitting" type="submit" class="rounded-lg bg-red-600 px-4 py-2 text-white disabled:opacity-50">{{ submitting ? '提交中…' : '提交举报' }}</button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { reportsApi, type ReportTarget } from '@/api/reports'
import { extractApiError } from '@/utils/auth'

const props = defineProps<{ open: boolean; targetType: ReportTarget; targetId: number }>()
const emit = defineEmits<{ close: []; submitted: [] }>()
const reason = ref('')
const error = ref('')
const submitting = ref(false)

function close() { emit('close') }
async function submit() {
  submitting.value = true
  error.value = ''
  try {
    await reportsApi.submit({ target_type: props.targetType, target_id: props.targetId, reason: reason.value.trim() })
    reason.value = ''
    emit('submitted')
    emit('close')
  } catch (cause) {
    error.value = extractApiError(cause, '举报提交失败')
  } finally {
    submitting.value = false
  }
}
</script>
