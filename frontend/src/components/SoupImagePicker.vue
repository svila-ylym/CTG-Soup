<script setup lang="ts">
import { ref } from 'vue'
import { ArrowLeftIcon, ArrowRightIcon, PhotoIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { uploadApi } from '@/api/upload'
import { extractApiError } from '@/utils/auth'
import type { SoupImageRef } from '@/types'

const images = defineModel<SoupImageRef[]>({ required: true })
const props = withDefaults(defineProps<{
  label: string
  disabled?: boolean
  max?: number
}>(), {
  disabled: false,
  max: 5,
})

const input = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const error = ref('')

async function selectFiles(event: Event) {
  const target = event.target as HTMLInputElement
  const files = Array.from(target.files || []).slice(0, props.max - images.value.length)
  target.value = ''
  if (!files.length) return
  uploading.value = true
  error.value = ''
  try {
    for (const file of files) {
      const response = await uploadApi.image(file)
      images.value = [
        ...images.value,
        {
          id: response.data.asset_id,
          public_url: response.data.url,
          mime_type: response.data.mime_type,
          size: response.data.size,
        },
      ]
    }
  } catch (cause) {
    error.value = extractApiError(cause, '图片上传失败')
  } finally {
    uploading.value = false
  }
}

function move(index: number, offset: number) {
  const target = index + offset
  if (target < 0 || target >= images.value.length) return
  const next = [...images.value]
  ;[next[index], next[target]] = [next[target], next[index]]
  images.value = next
}

function remove(index: number) {
  images.value = images.value.filter((_, itemIndex) => itemIndex !== index)
}
</script>

<template>
  <section class="mt-3" :aria-label="`${label}图片`">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <p class="text-sm font-medium text-slate-700 dark:text-slate-200">{{ label }}图片</p>
      <span class="text-xs text-slate-500">{{ images.length }} / {{ max }}</span>
    </div>
    <div v-if="images.length" class="mt-3 grid gap-3 sm:grid-cols-2">
      <div v-for="(image, index) in images" :key="image.id" class="border border-slate-200 p-2 dark:border-neutral-800">
        <a :href="image.public_url" target="_blank" rel="noopener noreferrer" class="block aspect-[4/3] bg-slate-50 dark:bg-neutral-900">
          <img :src="image.public_url" :alt="`${label}图片 ${index + 1}`" class="h-full w-full object-contain">
        </a>
        <div class="mt-2 flex justify-end gap-1">
          <button class="flex h-8 w-8 items-center justify-center text-slate-500 hover:text-blue-600 disabled:opacity-30" type="button" :disabled="disabled || index === 0" :aria-label="`左移${label}图片 ${index + 1}`" title="左移" @click="move(index, -1)">
            <ArrowLeftIcon class="h-4 w-4" aria-hidden="true" />
          </button>
          <button class="flex h-8 w-8 items-center justify-center text-slate-500 hover:text-blue-600 disabled:opacity-30" type="button" :disabled="disabled || index === images.length - 1" :aria-label="`右移${label}图片 ${index + 1}`" title="右移" @click="move(index, 1)">
            <ArrowRightIcon class="h-4 w-4" aria-hidden="true" />
          </button>
          <button class="flex h-8 w-8 items-center justify-center text-red-600 hover:text-red-700 disabled:opacity-30" type="button" :disabled="disabled" :aria-label="`移除${label}图片 ${index + 1}`" title="移除" @click="remove(index)">
            <XMarkIcon class="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
    <input ref="input" class="sr-only" type="file" accept="image/png,image/jpeg,image/webp,image/gif" multiple :disabled="disabled || uploading || images.length >= max" @change="selectFiles">
    <button class="btn-secondary mt-3 inline-flex items-center gap-2" type="button" :disabled="disabled || uploading || images.length >= max" @click="input?.click()">
      <PhotoIcon class="h-4 w-4" aria-hidden="true" />
      {{ uploading ? '上传中…' : images.length >= max ? '已达图片上限' : `添加${label}图片` }}
    </button>
    <p v-if="error" class="mt-2 break-words text-sm text-red-600">{{ error }}</p>
  </section>
</template>
