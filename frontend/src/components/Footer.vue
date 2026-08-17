<template>
  <footer class="glass-footer" data-layout-region="footer">
    <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div class="flex flex-col gap-8 py-10 sm:py-12">
        <div class="flex flex-wrap items-center justify-between gap-6">
          <div class="flex items-center gap-3">
            <img src="/icon.ico" alt="汤吧社区图标" class="h-8 w-8 object-contain" />
            <strong class="text-lg text-gray-800 dark:text-white">汤吧社区</strong>
          </div>
          <nav class="flex flex-wrap gap-x-5 gap-y-2 text-sm" aria-label="页脚导航">
            <router-link to="/soups" class="footer-link">海龟汤</router-link>
            <router-link to="/leaderboard" class="footer-link">排行榜</router-link>
            <router-link to="/posts" class="footer-link">公告</router-link>
            <router-link to="/competitions" class="footer-link">比赛</router-link>
            <router-link to="/hall-of-fame" class="footer-link">殿堂</router-link>
          </nav>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-6 text-sm text-gray-500 dark:text-gray-400">
          <p class="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span>&copy; 2026 汤吧社区</span>
            <span class="text-slate-300 dark:text-neutral-600" aria-hidden="true">·</span>
            <span>版本 {{ version ? `v${version}` : '读取中…' }}</span>
          </p>
          <p class="text-xs text-gray-400 dark:text-gray-500">
            情境推理 · 海龟汤 · 谜题社区
          </p>
        </div>
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

<style scoped>
.glass-footer {
  position: relative;
  isolation: isolate;
  border-top: 1px solid color-mix(in srgb, var(--border) 50%, transparent);
  background: linear-gradient(180deg, var(--glass-panel) 0%, var(--glass-panel-fallback) 100%);
  backdrop-filter: blur(12px) saturate(130%);
  -webkit-backdrop-filter: blur(12px) saturate(130%);
  box-shadow: 0 -4px 20px rgba(15, 23, 42, 0.04);
  transition: background-color var(--transition-standard), border-color var(--transition-standard);
}

.dark .glass-footer {
  background: linear-gradient(180deg, rgba(5, 5, 5, 0.7) 0%, rgba(10, 10, 10, 0.94) 100%);
  box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.3);
}

.glass-footer::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--glass-highlight), transparent);
  opacity: 0.5;
}

.footer-link {
  position: relative;
  color: var(--muted);
  text-decoration: none;
  transition: color 0.2s ease;
}

.footer-link::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 0;
  height: 1.5px;
  background: var(--liquid-accent);
  border-radius: 1px;
  transition: width 0.25s cubic-bezier(.2, .75, .25, 1);
}

.footer-link:hover {
  color: var(--liquid-accent);
}

.footer-link:hover::after {
  width: 100%;
}
</style>
