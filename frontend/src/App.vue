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
import LiquidCursorTrail from '@/components/LiquidCursorTrail.vue'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const initialLoading = ref(true)
const routeProgressPhase = ref<'idle' | 'active' | 'finishing'>('idle')
let bootTimer = 0
let bootSafetyTimer = 0
let routeTimer = 0
let loaderFinished = false

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
