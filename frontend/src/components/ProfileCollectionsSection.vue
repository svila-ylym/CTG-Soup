<script setup lang="ts">
import { ref, watch } from 'vue'
import { FolderPlusIcon, PencilSquareIcon, TrashIcon } from '@heroicons/vue/24/outline'
import { collectionApi } from '@/api/collections'
import SoupCollectionDialog from '@/components/SoupCollectionDialog.vue'
import { extractApiError } from '@/utils/auth'
import type { SoupCollectionInput, SoupCollectionSummary } from '@/types'

const props = defineProps<{
  ownerUid: number
  isSelf: boolean
}>()

const items = ref<SoupCollectionSummary[]>([])
const page = ref(1)
const totalPages = ref(0)
const loading = ref(false)
const error = ref('')
const saving = ref(false)
const deletingId = ref<number | null>(null)
const dialogOpen = ref(false)
const dialogError = ref('')
const editingCollection = ref<SoupCollectionSummary | null>(null)

async function load(targetPage = page.value) {
  loading.value = true
  error.value = ''
  try {
    const response = await collectionApi.list(props.ownerUid, targetPage, 10)
    items.value = response.data.items
    page.value = response.data.page
    totalPages.value = response.data.total_pages ?? 0
  } catch (cause) {
    error.value = extractApiError(cause, '合集加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingCollection.value = null
  dialogError.value = ''
  dialogOpen.value = true
}

function openEdit(collection: SoupCollectionSummary) {
  editingCollection.value = collection
  dialogError.value = ''
  dialogOpen.value = true
}

function closeDialog() {
  if (!saving.value) dialogOpen.value = false
}

async function save(input: SoupCollectionInput) {
  saving.value = true
  dialogError.value = ''
  try {
    if (editingCollection.value) {
      await collectionApi.update(editingCollection.value.id, input)
    } else {
      await collectionApi.create(input)
    }
    await load()
    dialogOpen.value = false
  } catch (cause) {
    dialogError.value = extractApiError(cause, '合集保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(collection: SoupCollectionSummary) {
  if (!window.confirm(`确定删除合集“${collection.name}”吗？合集内海龟汤会保留并移出合集。`)) return
  deletingId.value = collection.id
  error.value = ''
  try {
    await collectionApi.delete(collection.id)
    if (items.value.length === 1 && page.value > 1) page.value -= 1
    await load()
  } catch (cause) {
    error.value = extractApiError(cause, '合集删除失败')
  } finally {
    deletingId.value = null
  }
}

watch(
  () => props.ownerUid,
  () => {
    page.value = 1
    void load(1)
  },
  { immediate: true },
)
</script>

<template>
  <section class="border-t border-slate-200 py-7 dark:border-neutral-800">
    <div class="flex items-center justify-between gap-3">
      <h2 class="section-title">合集</h2>
      <button v-if="isSelf" class="btn-secondary gap-2" type="button" @click="openCreate">
        <FolderPlusIcon class="h-4 w-4" aria-hidden="true" />创建合集
      </button>
    </div>

    <p v-if="loading && !items.length" class="mt-5 text-sm text-slate-500">正在加载合集…</p>
    <div v-else-if="items.length" class="mt-5 grid gap-3 sm:grid-cols-2">
      <router-link v-for="collection in items" :key="collection.id" :to="`/collections/${collection.id}`" class="group block rounded-md border border-slate-200 p-4 hover:border-blue-300 dark:border-neutral-800 dark:hover:border-blue-700">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <strong class="block break-words group-hover:text-blue-600">{{ collection.name }}</strong>
            <p v-if="collection.description" class="mt-1 line-clamp-2 break-words text-sm text-slate-500">{{ collection.description }}</p>
            <p class="mt-2 text-xs text-slate-400">{{ collection.soup_count }} 篇公开作品</p>
          </div>
          <div v-if="isSelf" class="flex shrink-0 items-center gap-1">
            <button class="flex h-8 w-8 items-center justify-center text-slate-500 hover:text-blue-600" type="button" title="编辑合集" aria-label="编辑合集" @click.prevent.stop="openEdit(collection)">
              <PencilSquareIcon class="h-4 w-4" aria-hidden="true" />
            </button>
            <button class="flex h-8 w-8 items-center justify-center text-slate-500 hover:text-red-600 disabled:opacity-50" type="button" title="删除合集" aria-label="删除合集" :disabled="deletingId === collection.id" @click.prevent.stop="remove(collection)">
              <TrashIcon class="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      </router-link>
    </div>
    <p v-else class="mt-5 text-sm text-slate-500">{{ isSelf ? '还没有合集，可以先创建一个再发布系列作品。' : '暂未公开合集' }}</p>
    <p v-if="error" class="mt-4 break-words text-sm text-red-600">{{ error }}</p>
    <div v-if="totalPages > 1" class="mt-6 flex items-center justify-center gap-4">
      <button class="btn-secondary" type="button" :disabled="page <= 1 || loading" @click="load(page - 1)">上一页</button>
      <span class="text-sm text-slate-500">{{ page }} / {{ totalPages }}</span>
      <button class="btn-secondary" type="button" :disabled="page >= totalPages || loading" @click="load(page + 1)">下一页</button>
    </div>

    <SoupCollectionDialog :open="dialogOpen" :collection="editingCollection" :saving="saving" :error="dialogError" @close="closeDialog" @save="save" />
  </section>
</template>
