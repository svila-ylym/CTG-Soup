<template>
  <TransitionRoot appear :show="open" as="template">
    <Dialog as="div" class="relative z-[70]" @close="requestClose">
      <TransitionChild
        as="template"
        enter="duration-150 ease-out"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="duration-100 ease-in"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="fixed inset-0 bg-black/45" />
      </TransitionChild>

      <div class="fixed inset-0 overflow-y-auto p-4">
        <div class="flex min-h-full items-center justify-center">
          <TransitionChild
            as="template"
            enter="duration-150 ease-out"
            enter-from="opacity-0 translate-y-2"
            enter-to="opacity-100 translate-y-0"
            leave="duration-100 ease-in"
            leave-from="opacity-100 translate-y-0"
            leave-to="opacity-0 translate-y-2"
          >
            <DialogPanel class="w-full max-w-lg rounded-md bg-white p-5 shadow-xl dark:bg-neutral-900 sm:p-6">
              <div class="flex items-start justify-between gap-3">
                <DialogTitle class="min-w-0 break-words text-lg font-semibold text-slate-900 dark:text-white">
                  “{{ soupTitle }}”的评分人
                </DialogTitle>
                <button class="shrink-0 text-sm text-slate-500 hover:text-slate-800 dark:hover:text-white" type="button" @click="requestClose">
                  关闭
                </button>
              </div>

              <div v-if="loading && !ratings.length" class="py-8 text-center text-sm text-slate-500">加载中…</div>
              <div v-else-if="error" class="py-6 text-center">
                <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
                <button class="btn-secondary mt-4" type="button" @click="loadRatings(page)">重新加载</button>
              </div>
              <p v-else-if="!ratings.length" class="py-8 text-center text-sm text-slate-500">暂无公开评分。</p>
              <div v-else class="mt-4 divide-y divide-slate-200 border-y border-slate-200 dark:divide-neutral-800 dark:border-neutral-800">
                <div v-for="rating in ratings" :key="`${rating.user_uid}-${rating.created_at}`" class="flex items-center justify-between gap-4 py-3">
                  <div class="min-w-0">
                    <router-link :to="`/profile/${rating.user_uid}`" class="block truncate font-medium text-blue-600 hover:underline">
                      {{ rating.nickname || rating.username }}
                    </router-link>
                    <p class="mt-0.5 truncate text-xs text-slate-500">
                      @{{ rating.username }} · {{ formatChinaDateTime(rating.created_at) }}
                    </p>
                  </div>
                  <span class="shrink-0 font-semibold text-amber-600 dark:text-amber-400">{{ rating.score.toFixed(1) }} 分</span>
                </div>
              </div>

              <div v-if="total" class="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-slate-500">
                <span>共 {{ total }} 人评分 · 第 {{ page }}/{{ totalPages }} 页</span>
                <div class="flex items-center gap-2">
                  <button class="btn-secondary px-2.5 py-1.5" type="button" :disabled="loading || page <= 1" @click="loadRatings(page - 1)">
                    上一页
                  </button>
                  <button class="btn-secondary px-2.5 py-1.5" type="button" :disabled="loading || page >= totalPages" @click="loadRatings(page + 1)">
                    下一页
                  </button>
                </div>
              </div>
            </DialogPanel>
          </TransitionChild>
        </div>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
import { soupApi } from '@/api/soup'
import type { SoupRating } from '@/types'
import { extractApiError } from '@/utils/auth'
import { formatChinaDateTime } from '@/utils/datetime'

const props = defineProps<{
  open: boolean
  soupId: number | null
  soupTitle: string
}>()

const emit = defineEmits<{
  close: []
}>()

const ratings = ref<SoupRating[]>([])
const loading = ref(false)
const error = ref('')
const page = ref(1)
const total = ref(0)
const totalPages = ref(1)
let requestSerial = 0

function requestClose() {
  emit('close')
}

async function loadRatings(targetPage: number) {
  const soupId = props.soupId
  if (!props.open || soupId == null) return

  const serial = ++requestSerial
  loading.value = true
  error.value = ''
  try {
    const response = (await soupApi.listRatings(soupId, { page: targetPage, page_size: 50 })).data
    if (serial !== requestSerial || soupId !== props.soupId || !props.open) return
    ratings.value = response.items || []
    page.value = response.page
    total.value = response.total
    totalPages.value = Math.max(response.total_pages ?? 1, 1)
  } catch (cause) {
    if (serial !== requestSerial || soupId !== props.soupId || !props.open) return
    ratings.value = []
    error.value = extractApiError(cause, '评分列表加载失败')
  } finally {
    if (serial === requestSerial) loading.value = false
  }
}

watch(
  () => [props.open, props.soupId] as const,
  ([open, soupId]) => {
    requestSerial += 1
    ratings.value = []
    loading.value = false
    error.value = ''
    page.value = 1
    total.value = 0
    totalPages.value = 1
    if (open && soupId != null) void loadRatings(1)
  },
  { immediate: true },
)
</script>
