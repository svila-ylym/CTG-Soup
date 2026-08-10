<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref } from 'vue'
import { searchApi } from '@/api/search'
import type { SearchUser } from '@/types'

let mentionInstanceCount = 0

const props = withDefaults(defineProps<{
  modelValue: string
  maxlength?: number
  placeholder?: string
  ariaLabel?: string
  compact?: boolean
}>(), {
  maxlength: 2000,
  placeholder: '',
  ariaLabel: '文本内容',
  compact: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const textarea = ref<HTMLTextAreaElement | null>(null)
const mentionListId = `mention-candidates-${mentionInstanceCount++}`
const candidates = ref<SearchUser[]>([])
const activeToken = ref<{ start: number; end: number; query: string } | null>(null)
const selectedIndex = ref(0)
const loading = ref(false)
const menuOpen = ref(false)
let searchTimer = 0
let requestSequence = 0

function findActiveToken(value: string, caret: number) {
  const beforeCaret = value.slice(0, caret)
  const match = beforeCaret.match(/@([^\s@]*)$/u)
  if (!match) return null
  return {
    start: caret - match[0].length,
    end: caret,
    query: match[1],
  }
}

function closeMenu() {
  window.clearTimeout(searchTimer)
  requestSequence += 1
  candidates.value = []
  activeToken.value = null
  selectedIndex.value = 0
  loading.value = false
  menuOpen.value = false
}

function updateActiveToken(value = props.modelValue, caret = textarea.value?.selectionStart ?? value.length) {
  const token = findActiveToken(value, caret)
  if (!token || !token.query) {
    closeMenu()
    return
  }

  activeToken.value = token
  menuOpen.value = true
  window.clearTimeout(searchTimer)
  const sequence = ++requestSequence
  loading.value = true
  searchTimer = window.setTimeout(async () => {
    try {
      const response = await searchApi.users(token.query, 1, 8)
      if (sequence !== requestSequence) return
      candidates.value = response.data.items || []
      selectedIndex.value = 0
    } catch {
      if (sequence !== requestSequence) return
      candidates.value = []
      menuOpen.value = false
    } finally {
      if (sequence === requestSequence) loading.value = false
    }
  }, 160)
}

function handleInput(event: Event) {
  const target = event.target as HTMLTextAreaElement
  emit('update:modelValue', target.value)
  updateActiveToken(target.value, target.selectionStart)
}

function refreshFromCaret() {
  updateActiveToken()
}

function handleBlur() {
  window.setTimeout(() => {
    if (document.activeElement !== textarea.value) closeMenu()
  }, 120)
}

function selectCandidate(candidate: SearchUser) {
  const token = activeToken.value
  if (!token) return
  const replacement = `@${candidate.username} `
  const nextValue = `${props.modelValue.slice(0, token.start)}${replacement}${props.modelValue.slice(token.end)}`
  const nextCaret = token.start + replacement.length
  emit('update:modelValue', nextValue)
  closeMenu()
  void nextTick(() => {
    textarea.value?.focus()
    textarea.value?.setSelectionRange(nextCaret, nextCaret)
  })
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && menuOpen.value) {
    event.preventDefault()
    closeMenu()
    return
  }
  if (!menuOpen.value || !candidates.value.length) return
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    selectedIndex.value = (selectedIndex.value + 1) % candidates.value.length
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    selectedIndex.value = (selectedIndex.value - 1 + candidates.value.length) % candidates.value.length
  } else if (event.key === 'Enter' || event.key === 'Tab') {
    event.preventDefault()
    selectCandidate(candidates.value[selectedIndex.value])
  }
}

onBeforeUnmount(() => {
  window.clearTimeout(searchTimer)
  requestSequence += 1
})
</script>

<template>
  <div class="relative min-w-0">
    <textarea
      ref="textarea"
      :value="modelValue"
      :maxlength="maxlength"
      :placeholder="placeholder"
      :aria-label="ariaLabel"
      aria-autocomplete="list"
      :aria-expanded="menuOpen"
      :aria-controls="mentionListId"
      class="form-control w-full resize-y"
      :class="compact ? 'min-h-20' : 'min-h-24'"
      @input="handleInput"
      @click="refreshFromCaret"
      @blur="handleBlur"
      @keydown="handleKeydown"
    >
    </textarea>

    <div
      v-if="menuOpen && (loading || candidates.length)"
      :id="mentionListId"
      class="absolute inset-x-0 top-full z-40 mt-1 max-h-60 overflow-y-auto rounded-md border border-slate-200 bg-white p-1 shadow-xl dark:border-neutral-700 dark:bg-neutral-900"
      role="listbox"
      aria-label="艾特候选用户"
    >
      <div v-if="loading" class="px-3 py-2 text-sm text-slate-500">正在搜索用户…</div>
      <template v-else>
        <button
          v-for="(candidate, index) in candidates"
          :key="candidate.uid"
          type="button"
          role="option"
          :aria-selected="selectedIndex === index"
          class="flex w-full items-center gap-3 rounded-md px-3 py-2 text-left transition hover:bg-slate-100 dark:hover:bg-neutral-800"
          :class="selectedIndex === index ? 'bg-slate-100 dark:bg-neutral-800' : ''"
          @mousedown.prevent="selectCandidate(candidate)"
          @mouseenter="selectedIndex = index"
        >
          <img v-if="candidate.avatar_url" :src="candidate.avatar_url" alt="" class="h-8 w-8 shrink-0 rounded-full object-cover">
          <span v-else class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm font-semibold text-blue-700 dark:bg-blue-950 dark:text-blue-200">{{ candidate.nickname.slice(0, 1) }}</span>
          <span class="min-w-0">
            <strong class="block truncate text-sm text-slate-900 dark:text-white">{{ candidate.nickname }}</strong>
            <span class="block truncate text-xs text-slate-500">@{{ candidate.username }}</span>
          </span>
        </button>
      </template>
    </div>
  </div>
</template>
