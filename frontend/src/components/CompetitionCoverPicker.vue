<script setup lang="ts">
import { ref } from 'vue'
import { ArrowPathIcon, PhotoIcon, TrashIcon } from '@heroicons/vue/24/outline'
import { uploadApi } from '@/api/upload'
import { extractApiError } from '@/utils/auth'

const assetId = defineModel<number | null>('assetId', { required: true })
const url = defineModel<string | null>('url', { required: true })
const props = withDefaults(defineProps<{
  disabled?: boolean
}>(), {
  disabled: false,
})

const input = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const error = ref('')

async function selectFile(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  target.value = ''
  if (!file) return

  uploading.value = true
  error.value = ''
  try {
    const response = await uploadApi.image(file)
    assetId.value = response.data.asset_id
    url.value = response.data.url
  } catch (cause) {
    error.value = extractApiError(cause, '比赛封面上传失败')
  } finally {
    uploading.value = false
  }
}

function removeCover() {
  assetId.value = null
  url.value = null
  error.value = ''
}
</script>

<template>
  <section aria-labelledby="competition-cover-label">
    <div class="flex flex-wrap items-end justify-between gap-2">
      <div>
        <p id="competition-cover-label" class="text-sm font-medium">比赛封面</p>
        <p class="mt-1 text-xs text-slate-500">建议使用 16:7 横图，列表、详情和首页会自动裁切。</p>
      </div>
      <span class="text-xs text-slate-400">可选</span>
    </div>

    <div
      v-if="url"
      class="mt-3 aspect-[16/7] overflow-hidden rounded-xl border border-slate-200 bg-slate-100 dark:border-neutral-800 dark:bg-neutral-900"
    >
      <img :src="url" alt="当前比赛封面预览" class="h-full w-full object-cover">
    </div>
    <div
      v-else
      class="mt-3 flex aspect-[16/7] items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 text-slate-400 dark:border-neutral-700 dark:bg-neutral-900/70"
    >
      <PhotoIcon class="h-10 w-10" aria-hidden="true" />
    </div>

    <input
      ref="input"
      class="sr-only"
      type="file"
      accept="image/png,image/jpeg,image/webp,image/gif"
      :disabled="disabled || uploading"
      @change="selectFile"
    >
    <div class="mt-3 flex flex-wrap gap-3">
      <button class="btn-secondary gap-2" type="button" :disabled="disabled || uploading" @click="input?.click()">
        <ArrowPathIcon v-if="uploading" class="h-4 w-4 animate-spin" aria-hidden="true" />
        <PhotoIcon v-else class="h-4 w-4" aria-hidden="true" />
        {{ uploading ? '上传中…' : url ? '更换封面' : '上传封面' }}
      </button>
      <button v-if="url" class="btn-secondary gap-2 text-red-600 dark:text-red-400" type="button" :disabled="disabled || uploading" @click="removeCover">
        <TrashIcon class="h-4 w-4" aria-hidden="true" />
        移除封面
      </button>
    </div>
    <p v-if="error" class="mt-2 break-words text-sm text-red-600 dark:text-red-400">{{ error }}</p>
  </section>
</template>
