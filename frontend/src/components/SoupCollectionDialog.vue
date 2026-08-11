<script setup lang="ts">
import { ref, watch } from 'vue'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
import { XMarkIcon } from '@heroicons/vue/24/outline'
import type { SoupCollectionInput, SoupCollectionSummary } from '@/types'

const props = defineProps<{
  open: boolean
  collection: SoupCollectionSummary | null
  saving: boolean
  error: string
}>()
const emit = defineEmits<{
  close: []
  save: [input: SoupCollectionInput]
}>()

const name = ref('')
const description = ref('')
const validationError = ref('')

watch(
  () => [props.open, props.collection?.id] as const,
  ([open]) => {
    if (!open) return
    name.value = props.collection?.name ?? ''
    description.value = props.collection?.description ?? ''
    validationError.value = ''
  },
)

function close() {
  if (!props.saving) emit('close')
}

function submit() {
  const normalizedName = name.value.trim()
  const normalizedDescription = description.value.trim()
  validationError.value = ''
  if (!normalizedName) validationError.value = '请输入合集名称'
  else if (normalizedName.length > 100) validationError.value = '合集名称不能超过 100 个字'
  else if (normalizedDescription.length > 2000) validationError.value = '合集简介不能超过 2000 个字'
  if (validationError.value) return
  emit('save', { name: normalizedName, description: normalizedDescription })
}
</script>

<template>
  <TransitionRoot appear :show="open" as="template">
    <Dialog as="div" class="relative z-[70]" @close="close">
      <TransitionChild as="template" enter="duration-150 ease-out" enter-from="opacity-0" enter-to="opacity-100" leave="duration-100 ease-in" leave-from="opacity-100" leave-to="opacity-0">
        <div class="fixed inset-0 bg-black/45" />
      </TransitionChild>
      <div class="fixed inset-0 overflow-y-auto p-4">
        <div class="flex min-h-full items-center justify-center">
          <TransitionChild as="template" enter="duration-150 ease-out" enter-from="opacity-0 translate-y-2" enter-to="opacity-100 translate-y-0" leave="duration-100 ease-in" leave-from="opacity-100 translate-y-0" leave-to="opacity-0 translate-y-2">
            <DialogPanel class="w-full max-w-lg rounded-md bg-white p-5 shadow-xl dark:bg-neutral-900 sm:p-6">
              <div class="flex items-center justify-between gap-3">
                <DialogTitle class="text-lg font-semibold">{{ collection ? '编辑合集' : '创建合集' }}</DialogTitle>
                <button class="flex h-9 w-9 items-center justify-center text-slate-500 hover:text-slate-900 disabled:opacity-50 dark:hover:text-white" type="button" title="关闭" aria-label="关闭" :disabled="saving" @click="close">
                  <XMarkIcon class="h-5 w-5" aria-hidden="true" />
                </button>
              </div>
              <form class="mt-5 space-y-5" @submit.prevent="submit">
                <label class="block">
                  <span class="mb-2 block text-sm font-medium">名称</span>
                  <input v-model="name" class="form-control" maxlength="100" required autofocus>
                </label>
                <label class="block">
                  <span class="mb-2 block text-sm font-medium">简介</span>
                  <textarea v-model="description" class="form-control min-h-32 resize-y" maxlength="2000"></textarea>
                </label>
                <p v-if="validationError || error" class="break-words text-sm text-red-600">{{ validationError || error }}</p>
                <div class="flex flex-wrap justify-end gap-3">
                  <button class="btn-secondary" type="button" :disabled="saving" @click="close">取消</button>
                  <button class="btn-primary" type="submit" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button>
                </div>
              </form>
            </DialogPanel>
          </TransitionChild>
        </div>
      </div>
    </Dialog>
  </TransitionRoot>
</template>
