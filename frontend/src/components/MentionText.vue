<script setup lang="ts">
import { computed } from 'vue'
import type { MentionRef } from '@/types'

const props = defineProps<{
  text: string
  mentions?: MentionRef[]
}>()

interface TextPart {
  text: string
  mention?: MentionRef
}

const parts = computed<TextPart[]>(() => {
  const characters = Array.from(props.text)
  const mentions = [...(props.mentions || [])].sort(
    (first, second) => first.start_offset - second.start_offset,
  )
  const result: TextPart[] = []
  let cursor = 0
  for (const mention of mentions) {
    if (
      mention.start_offset < cursor
      || mention.end_offset <= mention.start_offset
      || mention.end_offset > characters.length
    ) continue
    if (mention.start_offset > cursor) {
      result.push({ text: characters.slice(cursor, mention.start_offset).join('') })
    }
    result.push({
      text: characters.slice(mention.start_offset, mention.end_offset).join(''),
      mention,
    })
    cursor = mention.end_offset
  }
  if (cursor < characters.length) {
    result.push({ text: characters.slice(cursor).join('') })
  }
  return result.length ? result : [{ text: props.text }]
})
</script>

<template>
  <span><template v-for="(part, index) in parts" :key="index"><router-link
    v-if="part.mention"
    :to="`/profile/${part.mention.uid}`"
    class="font-medium text-blue-600 hover:underline"
    @click.stop
  >{{ part.text }}</router-link><template v-else>{{ part.text }}</template></template></span>
</template>
