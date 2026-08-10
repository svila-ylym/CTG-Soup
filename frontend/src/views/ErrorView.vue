<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeftIcon, HomeIcon } from '@heroicons/vue/24/outline'

const route = useRoute()
const code = computed(() => String(route.params.code || route.query.code || '404'))
const copy = computed(() => code.value === '500'
  ? { title: '服务器出了点问题', message: '服务器暂时无法完成这次请求，请稍后再试。' }
  : { title: '页面不存在', message: '你访问的页面可能已经移动，或者地址写错了。' })
</script>

<template>
  <main class="page-shell flex items-center">
    <section class="page-container w-full py-20">
      <div class="mx-auto max-w-xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-neutral-800 dark:bg-neutral-950 sm:p-12">
        <p class="text-7xl font-black tracking-tight text-sky-600">{{ code }}</p>
        <h1 class="mt-5 text-2xl font-bold text-slate-900 dark:text-white">{{ copy.title }}</h1>
        <p class="mt-3 text-slate-500 dark:text-slate-400">{{ copy.message }}</p>
        <div class="mt-8 flex flex-wrap justify-center gap-3">
          <button class="btn-secondary gap-2" type="button" @click="$router.back()"><ArrowLeftIcon class="h-4 w-4" />返回上一页</button>
          <router-link class="btn-primary gap-2" to="/"><HomeIcon class="h-4 w-4" />返回主页</router-link>
        </div>
      </div>
    </section>
  </main>
</template>
