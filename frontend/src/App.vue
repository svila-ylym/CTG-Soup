<template>
  <div class="flex min-h-screen flex-col bg-white text-slate-900 dark:bg-black dark:text-slate-100">
    <NavBar />
    <section v-if="visibleAnnouncements.length" class="announcement-bar" aria-label="社区公告" data-layout-region="announcement">
      <div class="page-container flex min-w-0 items-start gap-3 py-3">
        <ExclamationTriangleIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
        <div class="min-w-0 flex-1">
          <p class="truncate font-semibold">{{ visibleAnnouncements[0].title }}</p>
          <p class="announcement-copy">{{ visibleAnnouncements[0].content }}</p>
        </div>
        <button class="announcement-close" type="button" aria-label="关闭公告" title="关闭公告" @click="dismiss(visibleAnnouncements[0].id)"><XMarkIcon class="h-5 w-5" aria-hidden="true" /></button>
      </div>
    </section>
    
    <div class="min-w-0 flex-1" data-layout-region="content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
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
import { announcementsApi } from '@/api/announcements'
import { ref, computed, onMounted } from 'vue'
import type { Announcement } from '@/types'
import { ExclamationTriangleIcon, XMarkIcon } from '@heroicons/vue/24/outline'

const announcements = ref<Announcement[]>([])
const dismissed = ref<number[]>(JSON.parse(sessionStorage.getItem('dismissed_announcements') || '[]'))
const visibleAnnouncements = computed(() => announcements.value.filter(item => !dismissed.value.includes(item.id)))
function dismiss(id: number) {
  dismissed.value = [...dismissed.value, id]
  sessionStorage.setItem('dismissed_announcements', JSON.stringify(dismissed.value))
}
onMounted(async () => {
  try { announcements.value = (await announcementsApi.list({ page: 1, page_size: 5 })).data.items || [] } catch { announcements.value = [] }
})

</script>
