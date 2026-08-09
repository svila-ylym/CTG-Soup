<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  select: [emoji: string]
}>()

const emojiGroups: Record<string, string[]> = {
  常用: ['😀', '😂', '🥹', '😊', '😍', '🤔', '😭', '😡'],
  手势: ['👍', '👎', '👏', '🙏', '👌', '✌️', '🤝', '💪'],
  符号: ['❤️', '💔', '✨', '🎉', '🔥', '💡', '✅', '❓'],
}
const activeGroup = ref(Object.keys(emojiGroups)[0])
</script>

<template>
  <div class="absolute bottom-full left-0 z-20 mb-2 w-64 border border-slate-200 bg-white p-3 shadow-lg dark:border-neutral-800 dark:bg-neutral-950 sm:w-72">
    <div class="flex gap-1 border-b border-slate-200 pb-2 dark:border-neutral-800">
      <button
        v-for="(_, group) in emojiGroups"
        :key="group"
        class="min-h-8 flex-1 px-2 text-xs text-slate-500 transition hover:bg-slate-100 dark:hover:bg-neutral-800"
        :class="activeGroup === group ? 'border-b-2 border-blue-600 text-blue-600' : ''"
        type="button"
        @click="activeGroup = group"
      >
        {{ group }}
      </button>
    </div>
    <div class="grid grid-cols-4 gap-1 pt-3">
      <button
        v-for="emoji in emojiGroups[activeGroup]"
        :key="emoji"
        class="flex aspect-square items-center justify-center text-2xl transition hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:hover:bg-neutral-800"
        type="button"
        :aria-label="emoji"
        @click="emit('select', emoji)"
      >
        {{ emoji }}
      </button>
    </div>
  </div>
</template>
