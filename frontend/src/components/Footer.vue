<template>
  <footer class="border-t border-gray-200 bg-white dark:border-neutral-800 dark:bg-black" data-layout-region="footer">
    <div class="container mx-auto px-4 py-8">
      <div class="flex flex-wrap items-center justify-between gap-6">
        <strong class="text-lg text-gray-800 dark:text-white">汤吧社区</strong>
        <nav class="flex flex-wrap gap-x-5 gap-y-2 text-sm" aria-label="页脚导航">
          <router-link to="/soups" class="text-gray-600 hover:text-blue-600 dark:text-gray-400">海龟汤</router-link>
          <router-link to="/leaderboard" class="text-gray-600 hover:text-blue-600 dark:text-gray-400">排行榜</router-link>
          <router-link to="/posts" class="text-gray-600 hover:text-blue-600 dark:text-gray-400">论坛</router-link>
          <router-link to="/competitions" class="text-gray-600 hover:text-blue-600 dark:text-gray-400">比赛</router-link>
        </nav>
      </div>

      <div class="mt-6 border-t border-gray-200 pt-6 text-sm text-gray-600 dark:border-neutral-800 dark:text-gray-400">
        <p class="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span>&copy; 2026 汤吧社区</span>
          <span class="text-slate-400 dark:text-neutral-600" aria-hidden="true">·</span>
          <span>版本 {{ version ? `v${version}` : '读取中…' }}</span>
        </p>
      </div>
    </div>
  </footer>
</template>
<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import http from '@/api/http'

const version = ref('')
let timer: number | undefined

async function loadVersion() {
  try {
    version.value = (await http.get<{ version: string }>('/version')).data.version
  } catch {
    version.value = ''
  }
}

onMounted(() => {
  void loadVersion()
  timer = window.setInterval(loadVersion, 300000)
})
onUnmounted(() => { if (timer) window.clearInterval(timer) })
</script>
