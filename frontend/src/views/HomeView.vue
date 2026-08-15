<template>
  <main class="home-page min-h-screen overflow-hidden bg-[#f7fbff] text-slate-900 dark:bg-black dark:text-white">
    <section
      ref="bannerRef"
      class="home-banner relative isolate h-[17rem] overflow-hidden border-b border-sky-100 sm:h-[19rem] lg:h-[20rem] dark:border-slate-800"
      :class="`scene-${scenePeriod}`"
      data-testid="home-banner"
      @pointermove="handlePointerMove"
      @pointerleave="resetPointer"
    >
      <div class="banner-sky absolute inset-0" aria-hidden="true"></div>
      <div class="banner-sun absolute" aria-hidden="true"></div>
      <svg class="landscape absolute inset-0 h-full w-full" viewBox="0 0 1600 760" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <defs>
          <linearGradient id="banner-sky" x1="0" y1="0" x2="0" y2="1">
            <stop class="sky-stop-top" offset="0" />
            <stop class="sky-stop-middle" offset="0.58" />
            <stop class="sky-stop-bottom" offset="1" />
          </linearGradient>
          <linearGradient id="banner-far-mountain" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#9acbd2" />
            <stop offset="1" stop-color="#6b9fb4" />
          </linearGradient>
          <linearGradient id="banner-mid-mountain" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#68ad91" />
            <stop offset="1" stop-color="#387b73" />
          </linearGradient>
          <linearGradient id="banner-lake" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#83d8df" />
            <stop offset="1" stop-color="#3a8ec0" />
          </linearGradient>
          <linearGradient id="banner-foreground" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#b4d85f" />
            <stop offset="1" stop-color="#3c9b69" />
          </linearGradient>
        </defs>

        <rect width="1600" height="760" fill="url(#banner-sky)" />
        <g class="layer-cloud-back cloud-drift" fill="#fff" opacity=".76">
          <path d="M180 150c10-38 62-54 90-19 28-45 103-26 106 29 39-12 77 14 78 51H143c-7-27 8-52 37-61Z" />
          <path d="M1150 170c18-47 76-49 102-12 26-49 109-27 105 32 44-12 77 15 79 51h-337c-5-30 17-61 51-71Z" />
        </g>
        <g class="layer-far" fill="url(#banner-far-mountain)">
          <path d="M0 442 175 274l104 89 148-166 172 189 117-103 154 129 138-178 184 191 139-121 169 138v224H0Z" />
        </g>
        <g class="layer-mid" fill="url(#banner-mid-mountain)">
          <path d="M0 534 137 386l112 67 119-131 143 127 117-79 126 111 109-153 181 160 122-84 145 108 154-73 135 92v229H0Z" />
        </g>
        <g class="layer-lake">
          <path d="M0 544c217-56 429-29 656 10 227 39 485 43 944-18v224H0Z" fill="url(#banner-lake)" />
          <g fill="none" stroke="#d7ffff" stroke-linecap="round" opacity=".55">
            <path d="M230 613h210M510 647h310M1010 605h244M1170 674h216M700 593h140" stroke-width="7" />
          </g>
        </g>
        <g class="layer-front" fill="url(#banner-foreground)">
          <path d="M0 602c190-59 348-27 493 26 142 51 312 57 482-6 176-65 383-79 625-12v150H0Z" />
          <path d="M0 686c183-67 323-55 500-3 177 51 314 39 459-17 218-84 405-49 641 18v86H0Z" fill="#267a5e" opacity=".78" />
        </g>
      </svg>
      <div class="banner-wash absolute inset-0 z-[3]" aria-hidden="true"></div>

      <div class="relative z-10 mx-auto flex h-full max-w-7xl items-center px-5 sm:px-8 lg:px-10">
        <div class="banner-copy max-w-2xl">
          <p v-if="accountStatus" class="mb-3 w-fit rounded-full border px-3 py-1 text-xs font-bold" :class="accountStatus.className">{{ accountStatus.label }}</p>
          <p class="banner-kicker mb-2 inline-flex items-center gap-2 text-xs font-black uppercase tracking-[.15em] text-sky-900/75 dark:text-cyan-100/80">
            <SparklesIcon class="h-4 w-4" aria-hidden="true" />
            情境推理社区
          </p>
          <h1 class="banner-title text-4xl font-black leading-none text-sky-950 drop-shadow-sm sm:text-5xl dark:text-white">汤吧社区</h1>
          <Transition name="copy-swap" mode="out-in">
            <p :key="hitokotoText" class="banner-line mt-3 line-clamp-2 max-w-xl text-sm font-semibold leading-6 text-sky-950/80 sm:text-base dark:text-slate-100/85">{{ hitokotoText }}</p>
          </Transition>
          <div class="mt-5 flex flex-wrap gap-3">
            <router-link to="/soups" class="liquid-primary inline-flex min-h-10 items-center gap-2 px-4 py-2 text-sm font-bold">
              去解一碗汤
              <ArrowRightIcon class="h-4 w-4" aria-hidden="true" />
            </router-link>
            <router-link to="/soups/create" class="banner-secondary glass-button inline-flex min-h-10 items-center gap-2 px-4 py-2 text-sm font-bold text-sky-950 dark:text-white">
              发布谜面
              <PencilSquareIcon class="h-4 w-4" aria-hidden="true" />
            </router-link>
          </div>
        </div>
      </div>
    </section>

    <section class="px-5 py-8 sm:px-8 sm:py-10 lg:px-10 lg:py-12" aria-labelledby="discovery-heading">
      <div class="mx-auto max-w-7xl">
        <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p class="text-xs font-black uppercase tracking-[.16em] text-sky-600">社区正在发生</p>
            <h2 id="discovery-heading" class="mt-1 text-2xl font-black text-slate-950 sm:text-3xl dark:text-white">比赛与随机好汤</h2>
          </div>
          <div class="flex gap-4 text-sm font-bold">
            <router-link to="/competitions" class="text-sky-700 hover:text-sky-500 dark:text-sky-300">全部比赛</router-link>
            <router-link to="/soups" class="text-sky-700 hover:text-sky-500 dark:text-sky-300">浏览汤库</router-link>
          </div>
        </div>

        <div v-if="loading" class="grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(20rem,5fr)]" aria-busy="true" aria-label="首页内容加载中">
          <div class="glass-card min-h-[28rem] p-5">
            <div class="skeleton-block aspect-[16/7] w-full"></div>
            <div class="skeleton-block mt-5 h-7 w-2/3"></div>
            <div class="skeleton-block mt-4 h-20 w-full"></div>
          </div>
          <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
            <div v-for="index in 4" :key="index" class="glass-card min-h-48 p-4">
              <div class="skeleton-block h-5 w-2/3"></div>
              <div class="skeleton-block mt-4 h-16 w-full"></div>
              <div class="skeleton-block mt-5 h-4 w-1/2"></div>
            </div>
          </div>
        </div>

        <div v-else-if="error" class="glass-panel p-8 text-center">
          <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
          <button class="btn-secondary mt-4" type="button" @click="loadDiscovery()">重新加载</button>
        </div>

        <div v-else class="grid items-stretch gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(20rem,5fr)]">
          <router-link
            v-if="latestCompetition"
            :to="`/competitions/${latestCompetition.id}`"
            class="latest-competition glass-card glass-card-interactive group flex min-h-[28rem] flex-col overflow-hidden"
          >
            <div class="relative min-h-52 flex-1 overflow-hidden bg-slate-200 dark:bg-neutral-900">
              <img v-if="latestCompetition.cover_url" :src="latestCompetition.cover_url" :alt="`${latestCompetition.name} 比赛封面`" class="absolute inset-0 h-full w-full object-cover transition duration-500 group-hover:scale-[1.025]" loading="eager" fetchpriority="high">
              <div v-else class="absolute inset-0" :style="competitionFallback(latestCompetition.competition_color)" aria-hidden="true"></div>
              <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/25 to-transparent" aria-hidden="true"></div>
              <div class="absolute inset-x-0 bottom-0 p-5 text-white sm:p-6">
                <div class="flex flex-wrap items-center gap-2 text-xs font-bold">
                  <span class="rounded-full bg-white/18 px-2.5 py-1 backdrop-blur-md">{{ statusText(latestCompetition.status) }}</span>
                  <span>{{ latestCompetition.score_type === 'independent' ? '比赛方独评' : '社区平均分' }}</span>
                  <span>· 前 {{ latestCompetition.top_n }} 名</span>
                </div>
                <h3 class="mt-3 line-clamp-2 text-2xl font-black sm:text-3xl">{{ latestCompetition.name }}</h3>
              </div>
            </div>
            <div class="bg-white/88 p-5 backdrop-blur-xl sm:p-6 dark:bg-neutral-950/88">
              <p class="line-clamp-3 min-h-[4.5rem] text-sm leading-6 text-slate-600 dark:text-slate-300">{{ latestCompetition.description_excerpt || '查看比赛详情与参赛规则。' }}</p>
              <div v-if="latestCompetition.required_tags.length" class="mt-4 flex flex-wrap gap-2">
                <span v-for="tag in latestCompetition.required_tags.slice(0, 4)" :key="tag" class="rounded-md bg-sky-50 px-2 py-1 text-xs font-semibold text-sky-700 dark:bg-sky-950/50 dark:text-sky-300">#{{ tag }}</span>
              </div>
              <div class="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4 text-xs font-semibold text-slate-500 dark:border-neutral-800">
                <span>{{ formatChinaDateTime(latestCompetition.start_time) }} 开始</span>
                <span>{{ latestCompetition.entry_count }} 部作品</span>
              </div>
            </div>
          </router-link>

          <div v-else class="glass-card flex min-h-[28rem] flex-col items-center justify-center p-8 text-center">
            <FlagIcon class="h-10 w-10 text-slate-300" aria-hidden="true" />
            <h3 class="mt-4 text-xl font-bold">暂时没有比赛</h3>
            <p class="mt-2 text-sm text-slate-500">新比赛发布后会优先出现在这里。</p>
          </div>

          <aside aria-labelledby="random-soups-heading">
            <div class="mb-3 flex items-center justify-between gap-3">
              <h3 id="random-soups-heading" class="text-lg font-black">随机推荐</h3>
              <button class="inline-flex items-center gap-1 text-xs font-bold text-sky-700 disabled:opacity-50 dark:text-sky-300" type="button" :disabled="refreshing" @click="loadDiscovery(true)">
                <ArrowPathIcon class="h-4 w-4" :class="refreshing ? 'animate-spin' : ''" aria-hidden="true" />
                换一批
              </button>
            </div>
            <div v-if="randomSoups.length" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
              <router-link
                v-for="soup in randomSoups"
                :key="soup.id"
                :to="`/soups/${soup.id}`"
                class="competition-border-surface glass-card glass-card-interactive flex min-h-52 flex-col p-4"
                :style="competitionBorderStyle(soup.competition_colors)"
              >
                <div class="flex items-start justify-between gap-3">
                  <span class="inline-flex items-center gap-1 text-sm font-black text-amber-500"><StarIcon class="h-4 w-4" aria-hidden="true" />{{ soup.average_score.toFixed(1) }}</span>
                  <span class="text-xs text-slate-400">{{ soup.rating_count }} 人</span>
                </div>
                <h4 class="mt-3 line-clamp-2 break-words text-base font-black text-slate-900 dark:text-white">{{ soup.title }}</h4>
                <p class="mt-2 line-clamp-3 flex-1 break-words text-sm leading-5 text-slate-500 dark:text-slate-400">{{ soup.puzzle_excerpt }}</p>
                <div class="mt-4 flex flex-wrap gap-1.5">
                  <span :class="genreBadgeClass(soup.genre)">{{ soup.genre }}</span>
                  <span :class="soupColorBadgeClass(soup.soup_color)">{{ soup.soup_color }}</span>
                </div>
                <p class="mt-3 truncate border-t border-slate-100 pt-3 text-xs text-slate-400 dark:border-neutral-800">{{ soup.author_name }}</p>
              </router-link>
            </div>
            <div v-else class="glass-card flex min-h-52 items-center justify-center p-6 text-center text-sm text-slate-500">汤库还在等待第一碗汤。</div>
          </aside>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ArrowPathIcon, ArrowRightIcon, FlagIcon, PencilSquareIcon, SparklesIcon } from '@heroicons/vue/24/outline'
import { StarIcon } from '@heroicons/vue/20/solid'
import { homeApi } from '@/api/home'
import { useAuthStore } from '@/stores/auth'
import { competitionBorderStyle } from '@/utils/competitionBorder'
import { formatChinaDateTime } from '@/utils/datetime'
import { extractApiError } from '@/utils/auth'
import { genreBadgeClass, soupColorBadgeClass } from '@/utils/soupMetadata'
import type { HomeCompetitionSummary, HomeDiscovery, SoupColor, SoupGenre } from '@/types'

const authStore = useAuthStore()
const HITOKOTO_FALLBACK = '每一条线索都算数'
const discovery = ref<HomeDiscovery | null>(null)
const loading = ref(true)
const refreshing = ref(false)
const error = ref('')
const hitokotoText = ref(HITOKOTO_FALLBACK)
const bannerRef = ref<HTMLElement | null>(null)
type ScenePeriod = 'sunrise' | 'morning' | 'noon' | 'evening' | 'sunset' | 'night'
const scenePeriod = ref<ScenePeriod>('noon')
let sceneClock = 0
let pointerFrame = 0
let hitokotoTimeout = 0
let hitokotoController: AbortController | null = null

const latestCompetition = computed(() => discovery.value?.latest_competition ?? null)
const randomSoups = computed(() => (discovery.value?.random_soups ?? []).map(soup => ({
  ...soup,
  genre: soup.genre as SoupGenre,
  soup_color: soup.soup_color as SoupColor,
})))
const accountStatus = computed(() => (authStore.user?.status || authStore.restrictionStatus) === 'banned'
  ? { label: '已封禁', className: 'border-red-300 bg-red-50/90 text-red-700' }
  : (authStore.user?.status || authStore.restrictionStatus) === 'silenced'
    ? { label: '已禁言', className: 'border-amber-300 bg-amber-50/90 text-amber-800' }
    : null)

function statusText(status: HomeCompetitionSummary['status']) {
  return status === 'ongoing' ? '进行中' : status === 'pending' ? '即将开始' : '已结束'
}

function competitionFallback(color: string) {
  return { background: `linear-gradient(135deg, ${color}, color-mix(in srgb, ${color} 35%, #0f172a))` }
}

async function loadHitokoto() {
  hitokotoController?.abort()
  const controller = new AbortController()
  hitokotoController = controller
  window.clearTimeout(hitokotoTimeout)
  hitokotoTimeout = window.setTimeout(() => controller.abort(), 6000)
  try {
    const response = await fetch('https://v1.hitokoto.cn/?encode=json', { signal: controller.signal })
    if (!response.ok) return
    const payload = await response.json() as { hitokoto?: unknown }
    if (typeof payload.hitokoto === 'string' && payload.hitokoto.trim()) {
      hitokotoText.value = payload.hitokoto.trim()
    }
  } catch {
    hitokotoText.value = HITOKOTO_FALLBACK
  } finally {
    window.clearTimeout(hitokotoTimeout)
    if (hitokotoController === controller) hitokotoController = null
  }
}

async function loadDiscovery(forceRefresh = false) {
  const firstLoad = discovery.value === null
  if (firstLoad) loading.value = true
  else refreshing.value = true
  error.value = ''
  try {
    discovery.value = (await homeApi.discovery(forceRefresh)).data
  } catch (cause) {
    if (firstLoad) error.value = extractApiError(cause, '首页内容暂时无法加载')
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

function chinaMinutes(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    timeZone: 'Asia/Shanghai',
  }).formatToParts(date)
  const hour = Number(parts.find(part => part.type === 'hour')?.value || 0)
  const minute = Number(parts.find(part => part.type === 'minute')?.value || 0)
  return hour * 60 + minute
}

function updateScenePeriod() {
  const minutes = chinaMinutes()
  scenePeriod.value = minutes >= 390 && minutes < 420 ? 'sunrise'
    : minutes >= 420 && minutes < 540 ? 'morning'
      : minutes >= 540 && minutes < 1020 ? 'noon'
        : minutes >= 1020 && minutes < 1140 ? 'evening'
          : minutes >= 1140 && minutes < 1200 ? 'sunset'
            : 'night'
}

function setScenePosition(element: HTMLElement, x: number, y: number) {
  element.style.setProperty('--far-x', `${x * 1.5}px`)
  element.style.setProperty('--far-y', `${y * 0.7}px`)
  element.style.setProperty('--mid-x', `${x * 3}px`)
  element.style.setProperty('--mid-y', `${y * 1.2}px`)
  element.style.setProperty('--front-x', `${x * 5}px`)
  element.style.setProperty('--front-y', `${y * 1.8}px`)
}

function handlePointerMove(event: PointerEvent) {
  if (!bannerRef.value || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  const element = bannerRef.value
  const bounds = element.getBoundingClientRect()
  const x = (event.clientX - bounds.left) / bounds.width - 0.5
  const y = (event.clientY - bounds.top) / bounds.height - 0.5
  cancelAnimationFrame(pointerFrame)
  pointerFrame = requestAnimationFrame(() => setScenePosition(element, x, y))
}

function resetPointer() {
  cancelAnimationFrame(pointerFrame)
  if (bannerRef.value) setScenePosition(bannerRef.value, 0, 0)
}

onMounted(() => {
  updateScenePeriod()
  sceneClock = window.setInterval(updateScenePeriod, 60_000)
  void loadHitokoto()
  void loadDiscovery()
})

onBeforeUnmount(() => {
  cancelAnimationFrame(pointerFrame)
  window.clearInterval(sceneClock)
  window.clearTimeout(hitokotoTimeout)
  hitokotoController?.abort()
})
</script>

<style scoped>
.home-banner {
  --sky-top: #a7e2ff;
  --sky-middle: #d9f4ff;
  --sky-bottom: #fff4d6;
  --far-x: 0px;
  --far-y: 0px;
  --mid-x: 0px;
  --mid-y: 0px;
  --front-x: 0px;
  --front-y: 0px;
  background: var(--sky-middle);
  contain: paint;
}

.banner-sky { background: linear-gradient(180deg, var(--sky-top), var(--sky-middle) 60%, var(--sky-bottom)); }
.sky-stop-top { stop-color: var(--sky-top); }
.sky-stop-middle { stop-color: var(--sky-middle); }
.sky-stop-bottom { stop-color: var(--sky-bottom); }
.banner-sun {
  z-index: 1;
  right: 14%;
  top: 10%;
  width: 5.5rem;
  height: 5.5rem;
  border-radius: 50%;
  background: #ffe38b;
  box-shadow: 0 0 0 1rem rgba(255, 227, 139, .13), 0 0 3rem rgba(255, 230, 153, .38);
  animation: sun-breathe 10s ease-in-out infinite;
}
.landscape { z-index: 2; pointer-events: none; filter: saturate(.9); }
.layer-far { transform: translate3d(var(--far-x), var(--far-y), 0); }
.layer-mid { transform: translate3d(var(--mid-x), var(--mid-y), 0); }
.layer-front { transform: translate3d(var(--front-x), var(--front-y), 0); }
.layer-far, .layer-mid, .layer-front { transform-box: fill-box; transform-origin: center; transition: transform 400ms cubic-bezier(.2,.75,.25,1); }
.cloud-drift { animation: cloud-drift 28s ease-in-out infinite alternate; }
.banner-wash { background: linear-gradient(90deg, rgba(239, 249, 255, .82) 0%, rgba(239, 249, 255, .45) 46%, rgba(239, 249, 255, .08) 72%); }

.scene-sunrise { --sky-top: #7485ba; --sky-middle: #ffad82; --sky-bottom: #ffe5ac; }
.scene-sunrise .banner-sun { top: 48%; background: #ffb24f; }
.scene-morning { --sky-top: #c1e2e9; --sky-middle: #e8f2ed; --sky-bottom: #f6f6df; }
.scene-evening { --sky-top: #7199af; --sky-middle: #dcb886; --sky-bottom: #f6dca7; }
.scene-evening .landscape { filter: saturate(.82) brightness(.78); }
.scene-sunset { --sky-top: #343b6d; --sky-middle: #bd6269; --sky-bottom: #ff9f60; }
.scene-sunset .banner-sun { top: 51%; background: #ff875d; }
.scene-sunset .landscape { filter: sepia(.15) saturate(1.05) brightness(.58); }
.scene-night { --sky-top: #050d1b; --sky-middle: #102a40; --sky-bottom: #17374b; }
.scene-night .banner-sun { background: #e8eff1; box-shadow: inset -1.15rem -.35rem 0 #becdd4, 0 0 2rem rgba(211, 235, 242, .2); }
.scene-night .landscape { filter: hue-rotate(8deg) saturate(.52) brightness(.3); }
.scene-night .banner-wash,
:global(.dark .banner-wash) { background: linear-gradient(90deg, rgba(0, 0, 0, .72) 0%, rgba(0, 0, 0, .38) 48%, rgba(0, 0, 0, .06) 74%); }
.scene-night .banner-kicker,
.scene-sunset .banner-kicker { color: rgba(207, 250, 254, .86); }
.scene-night .banner-title,
.scene-sunset .banner-title { color: #fff; text-shadow: 0 2px 18px rgba(0, 0, 0, .36); }
.scene-night .banner-line,
.scene-sunset .banner-line { color: rgba(241, 245, 249, .9); text-shadow: 0 1px 10px rgba(0, 0, 0, .4); }
.scene-night .banner-secondary,
.scene-sunset .banner-secondary { border-color: rgba(255, 255, 255, .24); background: rgba(0, 0, 0, .34); color: #fff; }
.scene-night .banner-secondary:hover,
.scene-sunset .banner-secondary:hover { background: rgba(0, 0, 0, .5); }

.copy-swap-enter-active,
.copy-swap-leave-active { transition: opacity 220ms ease, transform 220ms ease; }
.copy-swap-enter-from { opacity: 0; transform: translateY(.35rem); }
.copy-swap-leave-to { opacity: 0; transform: translateY(-.25rem); }

@keyframes cloud-drift { to { transform: translateX(2.5rem); } }
@keyframes sun-breathe { 50% { transform: scale(1.04); opacity: .92; } }

@media (max-width: 639px) {
  .banner-wash { background: linear-gradient(90deg, rgba(239, 249, 255, .82), rgba(239, 249, 255, .5)); }
  :global(.dark .banner-wash) { background: linear-gradient(90deg, rgba(0, 0, 0, .7), rgba(0, 0, 0, .42)); }
}

@media (prefers-reduced-motion: reduce) {
  .banner-sun,
  .cloud-drift { animation: none !important; }
  .layer-far,
  .layer-mid,
  .layer-front { transform: none !important; transition: none !important; }
}
</style>
