<template>
  <Transition name="app-loader">
    <div v-if="initialLoading" class="app-loader" role="status" aria-live="polite">
      <div class="app-loader-ripple" aria-hidden="true"></div>
      <div class="app-loader-mark">
        <img src="/icon.ico" alt="" class="h-12 w-12 object-contain" />
      </div>
      <strong class="app-loader-brand">汤吧社区</strong>
      <span class="sr-only">页面加载中</span>
    </div>
  </Transition>

  <div class="route-progress" :class="`is-${routeProgressPhase}`" aria-hidden="true">
    <span></span>
  </div>
  <LiquidCursorTrail />

  <div class="app-frame flex min-h-screen flex-col bg-white text-slate-900 dark:bg-black dark:text-slate-100">
    <NavBar />
    <section v-if="visibleAnnouncements.length" class="announcement-bar" aria-label="社区公告" data-layout-region="announcement">
      <div class="page-container flex min-w-0 items-start gap-3 py-3">
        <ExclamationTriangleIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
        <div class="min-w-0 flex-1">
          <p class="truncate font-semibold"><LinkifiedText :text="visibleAnnouncements[0].title" /></p>
          <p class="announcement-copy"><LinkifiedText :text="visibleAnnouncements[0].content" /></p>
        </div>
        <button class="announcement-close" type="button" aria-label="关闭公告" title="关闭公告" @click="dismiss(visibleAnnouncements[0].id)"><XMarkIcon class="h-5 w-5" aria-hidden="true" /></button>
      </div>
    </section>
    
    <div class="relative min-w-0 flex-1" data-layout-region="content">
      <router-view v-slot="{ Component, route }">
        <transition name="route-fade">
          <component :is="Component" :key="route.fullPath" />
        </transition>
      </router-view>
    </div>

    <!-- 页脚 -->
    <Footer />

    <!-- 全局通知 -->
    <ToastContainer />
  </div>
</template>

<script setup lang="ts">
import NavBar from '@/components/NavBar.vue'
import Footer from '@/components/Footer.vue'
import ToastContainer from '@/components/ToastContainer.vue'
import LinkifiedText from '@/components/LinkifiedText.vue'
import LiquidCursorTrail from '@/components/LiquidCursorTrail.vue'
import { announcementsApi } from '@/api/announcements'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { Announcement } from '@/types'
import { ExclamationTriangleIcon, XMarkIcon } from '@heroicons/vue/24/outline'

const router = useRouter()
const announcements = ref<Announcement[]>([])
const dismissed = ref<number[]>(JSON.parse(sessionStorage.getItem('dismissed_announcements') || '[]'))
const initialLoading = ref(true)
const routeProgressPhase = ref<'idle' | 'active' | 'finishing'>('idle')
const visibleAnnouncements = computed(() => announcements.value.filter(item => !dismissed.value.includes(item.id)))
let bootTimer = 0
let bootSafetyTimer = 0
let routeTimer = 0
let loaderFinished = false

function dismiss(id: number) {
  dismissed.value = [...dismissed.value, id]
  sessionStorage.setItem('dismissed_announcements', JSON.stringify(dismissed.value))
}

function startRouteProgress() {
  window.clearTimeout(routeTimer)
  routeProgressPhase.value = 'active'
}

function finishRouteProgress() {
  if (routeProgressPhase.value === 'idle') return
  routeProgressPhase.value = 'finishing'
  window.clearTimeout(routeTimer)
  routeTimer = window.setTimeout(() => { routeProgressPhase.value = 'idle' }, 260)
}

function finishInitialLoading() {
  if (loaderFinished) return
  loaderFinished = true
  window.clearTimeout(bootTimer)
  window.clearTimeout(bootSafetyTimer)
  initialLoading.value = false
}

const removeBeforeHook = router.beforeEach(() => { startRouteProgress() })
const removeAfterHook = router.afterEach(() => { finishRouteProgress() })
const removeErrorHook = router.onError(() => { finishRouteProgress() })

onMounted(() => {
  const mountedAt = performance.now()
  bootSafetyTimer = window.setTimeout(finishInitialLoading, 2500)
  void router.isReady().finally(() => {
    const remaining = Math.max(0, 420 - (performance.now() - mountedAt))
    bootTimer = window.setTimeout(finishInitialLoading, remaining)
  })
  void announcementsApi.list({ page: 1, page_size: 5 })
    .then(response => { announcements.value = response.data.items || [] })
    .catch(() => { announcements.value = [] })
})

onBeforeUnmount(() => {
  window.clearTimeout(bootTimer)
  window.clearTimeout(bootSafetyTimer)
  window.clearTimeout(routeTimer)
  removeBeforeHook()
  removeAfterHook()
  removeErrorHook()
})
</script>
