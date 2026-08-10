<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { BoldIcon, CodeBracketIcon, ItalicIcon, LinkIcon, PhotoIcon, UnderlineIcon } from '@heroicons/vue/24/outline'
import { uploadApi } from '@/api/upload'
import { extractApiError } from '@/utils/auth'

const props = defineProps<{ modelValue: string; imageAssetIds: number[] }>()
const emit = defineEmits<{
  'update:modelValue': [value: string]
  'update:imageAssetIds': [value: number[]]
}>()
const editor = ref<HTMLElement | null>(null)
const htmlMode = ref(false)
const uploading = ref(false)
const error = ref('')

function syncFromDom() {
  if (!htmlMode.value && editor.value) emit('update:modelValue', editor.value.innerHTML)
}
function exec(command: string, value?: string) {
  if (htmlMode.value || !editor.value) return
  editor.value.focus()
  document.execCommand(command, false, value)
  syncFromDom()
}
function insertLink() {
  const value = window.prompt('链接地址')
  if (value) exec('createLink', value)
}
function setHtml(value: string) {
  if (editor.value && editor.value.innerHTML !== value) editor.value.innerHTML = value
}
function toggleMode() {
  if (htmlMode.value) {
    htmlMode.value = false
    void nextTick(() => setHtml(props.modelValue))
  } else {
    syncFromDom()
    htmlMode.value = true
  }
}
async function insertImage(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  uploading.value = true
  error.value = ''
  try {
    const response = await uploadApi.image(file)
    emit('update:imageAssetIds', [...new Set([...props.imageAssetIds, response.data.asset_id])])
    exec('insertImage', response.data.url)
  } catch (cause) {
    error.value = extractApiError(cause, '图片上传失败')
  } finally {
    uploading.value = false
  }
}
watch(() => props.modelValue, (value) => { if (!htmlMode.value) setHtml(value) })
onMounted(() => setHtml(props.modelValue))
</script>

<template>
  <div class="overflow-hidden border border-slate-300 dark:border-neutral-700">
    <div class="flex flex-wrap items-center gap-1 border-b border-slate-200 bg-slate-50 p-2 dark:border-neutral-800 dark:bg-neutral-900">
      <button class="editor-tool" type="button" title="加粗" aria-label="加粗" :disabled="htmlMode" @click="exec('bold')"><BoldIcon class="h-4 w-4" /></button>
      <button class="editor-tool" type="button" title="斜体" aria-label="斜体" :disabled="htmlMode" @click="exec('italic')"><ItalicIcon class="h-4 w-4" /></button>
      <button class="editor-tool" type="button" title="下划线" aria-label="下划线" :disabled="htmlMode" @click="exec('underline')"><UnderlineIcon class="h-4 w-4" /></button>
      <button class="editor-tool" type="button" title="插入链接" aria-label="插入链接" :disabled="htmlMode" @click="insertLink"><LinkIcon class="h-4 w-4" /></button>
      <label class="editor-tool cursor-pointer" title="插入图片" aria-label="插入图片"><PhotoIcon class="h-4 w-4" /><input class="sr-only" type="file" accept="image/jpeg,image/png,image/webp,image/gif" :disabled="uploading || htmlMode" @change="insertImage"></label>
      <button class="editor-tool ml-auto gap-1 px-2 text-xs" type="button" @click="toggleMode"><CodeBracketIcon class="h-4 w-4" />{{ htmlMode ? '可视化' : 'HTML' }}</button>
    </div>
    <textarea v-if="htmlMode" :value="modelValue" class="min-h-48 w-full resize-y border-0 bg-white p-4 font-mono text-sm outline-none dark:bg-neutral-950" maxlength="50000" @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"></textarea>
    <div v-else ref="editor" class="min-h-48 bg-white p-4 leading-7 outline-none dark:bg-neutral-950" contenteditable="true" @input="syncFromDom"></div>
    <p v-if="error" class="border-t border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">{{ error }}</p>
  </div>
</template>

<style scoped>
.editor-tool { display: inline-flex; min-height: 2rem; min-width: 2rem; align-items: center; justify-content: center; gap: .25rem; color: rgb(71 85 105); }
.editor-tool:hover:not(:disabled) { background: rgb(226 232 240); color: rgb(15 23 42); }
.editor-tool:disabled { opacity: .45; }
</style>
