<script setup lang="ts">
import { computed } from 'vue'
import { linkifyText } from '@/utils/linkifyText'

const props = defineProps<{ text: string }>()
const segments = computed(() => linkifyText(props.text))
</script>

<template>
  <span>
    <template v-for="(segment, index) in segments" :key="`${segment.type}-${index}`">
      <a
        v-if="segment.type === 'link'"
        :href="segment.href"
        class="break-all font-medium text-blue-600 hover:underline dark:text-blue-400"
        target="_blank"
        rel="noopener noreferrer nofollow ugc"
        @click.stop
      >{{ segment.text }}</a>
      <template v-else>{{ segment.text }}</template>
    </template>
  </span>
</template>
