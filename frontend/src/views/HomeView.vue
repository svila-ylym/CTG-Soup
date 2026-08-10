<template>
  <main class="home-page overflow-hidden bg-[#f7fbff] text-slate-900 dark:bg-[#07111f] dark:text-white">
    <section
      ref="heroRef"
      class="hero-scene relative isolate min-h-[36rem] overflow-hidden border-b border-sky-100 bg-[#dff4ff] sm:min-h-[40rem] lg:min-h-[43rem] dark:border-slate-800 dark:bg-[#071d2e]"
      :class="`scene-${scenePeriod}`"
      :style="sceneStyle"
      @pointermove="handlePointerMove"
      @pointerleave="resetPointer"
    >
      <div class="hero-sky absolute inset-0" aria-hidden="true"></div>
      <div class="hero-sun absolute" aria-hidden="true"></div>
      <div class="hero-glint hero-glint-one absolute" aria-hidden="true"></div>
      <div class="hero-glint hero-glint-two absolute" aria-hidden="true"></div>
      <div class="hero-mist absolute inset-0" aria-hidden="true"></div>

      <svg class="landscape absolute inset-0 h-full w-full" viewBox="0 0 1600 760" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <defs>
          <linearGradient id="home-sky" x1="0" y1="0" x2="0" y2="1">
            <stop class="sky-stop-top" offset="0" />
            <stop class="sky-stop-middle" offset="0.58" />
            <stop class="sky-stop-bottom" offset="1" />
          </linearGradient>
          <linearGradient id="home-far-mountain" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#9acbd2" />
            <stop offset="1" stop-color="#6b9fb4" />
          </linearGradient>
          <linearGradient id="home-mid-mountain" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#68ad91" />
            <stop offset="1" stop-color="#387b73" />
          </linearGradient>
          <linearGradient id="home-lake" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#83d8df" />
            <stop offset="1" stop-color="#3a8ec0" />
          </linearGradient>
          <linearGradient id="home-foreground" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#b4d85f" />
            <stop offset="1" stop-color="#3c9b69" />
          </linearGradient>
        </defs>

        <rect width="1600" height="760" fill="url(#home-sky)" />
        <g class="landscape-layer layer-cloud-back">
          <g class="cloud-drift cloud-drift-slow" fill="#fff" opacity=".82">
            <path d="M180 150c10-38 62-54 90-19 28-45 103-26 106 29 39-12 77 14 78 51H143c-7-27 8-52 37-61Z" />
            <path d="M1150 170c18-47 76-49 102-12 26-49 109-27 105 32 44-12 77 15 79 51h-337c-5-30 17-61 51-71Z" />
          </g>
        </g>
        <g class="landscape-layer layer-cloud-front">
          <g class="cloud-drift cloud-drift-fast" fill="#fff" opacity=".66">
            <path d="M560 92c11-28 44-35 67-14 19-34 75-17 78 25 28-7 50 13 50 36H516c-1-23 14-42 44-47Z" />
            <path d="M1375 270c9-25 40-31 58-12 18-28 62-16 66 22 26-7 47 11 47 32h-202c-1-20 11-36 31-42Z" />
          </g>
        </g>
        <g class="landscape-layer layer-far" fill="url(#home-far-mountain)">
          <path d="M0 442 175 274l104 89 148-166 172 189 117-103 154 129 138-178 184 191 139-121 169 138v224H0Z" />
        </g>
        <g class="landscape-layer layer-mid" fill="url(#home-mid-mountain)">
          <path d="M0 534 137 386l112 67 119-131 143 127 117-79 126 111 109-153 181 160 122-84 145 108 154-73 135 92v229H0Z" />
          <path d="M0 534 137 386l28 16-28 35 78-20-78 71-95 47Zm511-82 126 111 30-26-74-13 40-38-92-15Zm486-30 181 160 37-31-92-18 48-52-114-15Z" fill="#d1ed9a" opacity=".55" />
        </g>
        <g class="landscape-layer layer-lake">
          <path d="M0 544c217-56 429-29 656 10 227 39 485 43 944-18v224H0Z" fill="url(#home-lake)" />
          <g class="lake-shimmer" fill="none" stroke="#d7ffff" stroke-linecap="round" opacity=".6">
            <path d="M230 613h210M510 647h310M1010 605h244M1170 674h216M700 593h140" stroke-width="7" />
            <path d="M390 700h320M890 714h185M1270 622h170" stroke-width="4" />
          </g>
        </g>
        <g class="landscape-layer layer-foreground" fill="url(#home-foreground)">
          <path d="M0 602c190-59 348-27 493 26 142 51 312 57 482-6 176-65 383-79 625-12v150H0Z" />
          <path d="M0 686c183-67 323-55 500-3 177 51 314 39 459-17 218-84 405-49 641 18v86H0Z" fill="#267a5e" opacity=".78" />
        </g>
        <g class="landscape-layer layer-grass" fill="#e2f59b">
          <path d="M95 735c6-52 14-75 20-104 7 33 12 57 12 104ZM142 738c12-56 29-84 47-115-5 42-7 76-3 115ZM1450 736c6-57 23-90 39-117-2 43-3 77 4 117ZM1501 739c6-43 21-69 36-93 0 33 0 62 5 93Z" />
        </g>
      </svg>

      <div class="hero-container relative z-10 mx-auto grid min-h-[36rem] max-w-7xl items-center gap-8 px-5 pb-16 pt-14 sm:min-h-[40rem] sm:px-8 sm:pt-16 lg:min-h-[43rem] lg:grid-cols-[minmax(0,1.05fr)_minmax(25rem,.95fr)] lg:gap-12 lg:px-10 lg:pb-20">
        <div class="hero-copy max-w-2xl">
          <p v-if="accountStatus" class="mb-4 w-fit border px-3 py-1.5 text-sm font-black" :class="accountStatus.className">{{ accountStatus.label }}</p>
          <p class="hero-kicker mb-5 inline-flex max-w-full items-center gap-2 text-sm font-bold text-sky-800 sm:text-base dark:text-cyan-200">
            <SparklesIcon class="h-5 w-5" aria-hidden="true" />
            <span class="min-w-0 break-words">情境推理 · {{ hitokotoText }}</span>
          </p>
          <h1 class="hero-title text-[3.25rem] font-black leading-[.94] text-sky-950 sm:text-[4.8rem] lg:text-[6.2rem] dark:text-white" aria-label="汤吧社区">
            <span v-for="(character, index) in titleCharacters" :key="`${character}-${index}`" class="hero-title-character" aria-hidden="true" :style="{ animationDelay: `${180 + index * 90}ms` }">{{ character }}</span>
          </h1>
          <p class="hero-lede mt-7 max-w-xl text-base font-medium leading-7 text-sky-950/75 sm:text-xl sm:leading-8 dark:text-slate-200">
            一碗汤，一群人，一场从“为什么”开始的推理冒险。读故事、问线索、把藏起来的真相一点点拼完整。
          </p>
          <div class="hero-actions mt-8 flex flex-wrap items-center gap-3 sm:gap-4">
            <router-link to="/soups" class="hero-primary-button group inline-flex min-h-12 items-center gap-2 rounded-md bg-sky-700 px-5 py-3 font-bold text-white shadow-[0_8px_0_#155e75,0_15px_24px_rgba(14,116,144,.25)] transition hover:-translate-y-1 hover:bg-sky-600 hover:shadow-[0_10px_0_#155e75,0_19px_28px_rgba(14,116,144,.32)] active:translate-y-1 active:shadow-[0_4px_0_#155e75,0_9px_16px_rgba(14,116,144,.22)]">
              去解一碗汤
              <ArrowRightIcon class="h-5 w-5 transition-transform group-hover:translate-x-1" aria-hidden="true" />
            </router-link>
            <router-link to="/soups/create" class="hero-secondary-button inline-flex min-h-12 items-center gap-2 rounded-md border-2 border-sky-800/20 bg-white/70 px-5 py-3 font-bold text-sky-900 shadow-[0_5px_0_rgba(14,116,144,.16)] backdrop-blur-sm transition hover:-translate-y-1 hover:border-sky-800/35 hover:bg-white active:translate-y-1 active:shadow-none dark:border-cyan-400/30 dark:bg-slate-950/70 dark:text-cyan-100 dark:hover:border-cyan-300/50 dark:hover:bg-slate-900">
              发布我的谜面
              <PencilSquareIcon class="h-5 w-5" aria-hidden="true" />
            </router-link>
          </div>
          <div class="hero-quick-links mt-8 flex flex-wrap gap-x-5 gap-y-2 text-sm font-semibold text-sky-900/70 dark:text-slate-300">
            <router-link to="/leaderboard" class="inline-flex items-center gap-1 transition hover:text-sky-950 dark:hover:text-white"><TrophyIcon class="h-4 w-4" aria-hidden="true" />看排行榜</router-link>
            <router-link to="/posts" class="inline-flex items-center gap-1 transition hover:text-sky-950 dark:hover:text-white"><ChatBubbleLeftRightIcon class="h-4 w-4" aria-hidden="true" />和大家讨论</router-link>
            <router-link to="/competitions" class="inline-flex items-center gap-1 transition hover:text-sky-950 dark:hover:text-white"><FlagIcon class="h-4 w-4" aria-hidden="true" />参加比赛</router-link>
          </div>
        </div>

        <div class="hero-puzzle-stage relative mx-auto h-[25rem] w-full max-w-[31rem] sm:h-[28rem] lg:h-[31rem]" aria-label="情境推理示意图">
          <div class="puzzle-shadow absolute left-[13%] top-[30%] h-40 w-64 rotate-[-12deg] rounded-md bg-sky-900/10 blur-xl"></div>
          <div class="puzzle-note puzzle-note-back absolute left-[4%] top-[21%] w-[78%] rounded-md border-2 border-amber-900/10 bg-[#fff1ae] p-5 text-amber-950 shadow-[10px_14px_0_rgba(155,116,42,.15),0_18px_28px_rgba(43,91,111,.16)] sm:p-6">
            <div class="mb-7 flex items-center justify-between text-xs font-black uppercase tracking-[.15em] text-amber-800/60"><span>线索 01</span><span>?</span></div>
            <p class="text-lg font-extrabold leading-7 sm:text-xl">他每天都在等一场不会下的雨。</p>
            <div class="mt-8 h-1.5 w-2/3 rounded-full bg-amber-900/15"></div>
            <div class="mt-3 h-1.5 w-1/2 rounded-full bg-amber-900/10"></div>
          </div>
          <div class="puzzle-note puzzle-note-middle absolute right-[3%] top-[15%] w-[74%] rounded-md border-2 border-sky-900/10 bg-[#e9fbff] p-5 text-sky-950 shadow-[10px_14px_0_rgba(51,134,164,.14),0_18px_28px_rgba(43,91,111,.14)] sm:p-6">
            <div class="mb-7 flex items-center justify-between text-xs font-black uppercase tracking-[.15em] text-sky-800/60"><span>提问 02</span><ChatBubbleLeftRightIcon class="h-5 w-5" aria-hidden="true" /></div>
            <p class="text-lg font-extrabold leading-7 sm:text-xl">这和天气有关吗？</p>
            <div class="mt-8 flex items-end gap-2"><span class="h-2 w-2 rounded-full bg-sky-500"></span><span class="h-2 w-2 rounded-full bg-sky-300"></span><span class="h-2 w-2 rounded-full bg-sky-200"></span></div>
          </div>
          <div class="puzzle-note puzzle-note-front absolute bottom-[4%] left-[14%] w-[78%] rounded-md border-2 border-emerald-900/10 bg-[#f5ffe4] p-5 text-emerald-950 shadow-[10px_14px_0_rgba(55,130,88,.16),0_18px_28px_rgba(43,91,111,.16)] sm:p-6">
            <div class="mb-7 flex items-center justify-between text-xs font-black uppercase tracking-[.15em] text-emerald-800/60"><span>真相 03</span><CheckCircleIcon class="h-5 w-5" aria-hidden="true" /></div>
            <p class="text-lg font-extrabold leading-7 sm:text-xl">原来，他等的是一封信。</p>
            <div class="mt-6 flex items-center gap-2 text-xs font-bold text-emerald-800/65"><span class="h-2 w-2 animate-pulse rounded-full bg-emerald-500"></span>故事正在被拼完整</div>
          </div>
          <div class="puzzle-sticker absolute bottom-[1%] right-[4%] flex h-16 w-16 rotate-[12deg] items-center justify-center rounded-full border-4 border-white bg-orange-400 text-center text-xs font-black leading-4 text-orange-950 shadow-[0_8px_0_rgba(154,85,30,.22)] sm:h-20 sm:w-20">
            好奇心<br>+1
          </div>
        </div>
      </div>

      <a href="#community-intro" class="hero-scroll-cue absolute bottom-5 left-1/2 z-20 inline-flex -translate-x-1/2 flex-col items-center gap-1 text-xs font-bold text-sky-900/65 transition hover:text-sky-950 dark:text-cyan-100/70 dark:hover:text-white" aria-label="查看社区入口">
        <span>继续探索</span>
        <ChevronDownIcon class="h-4 w-4 animate-bounce" aria-hidden="true" />
      </a>
    </section>

    <section id="community-intro" class="home-section community-section scroll-mt-20 border-b border-sky-100 bg-white px-5 py-16 sm:px-8 sm:py-20 lg:px-10 dark:border-slate-800 dark:bg-slate-950">
      <div class="mx-auto max-w-7xl">
        <div class="section-heading flex flex-wrap items-end justify-between gap-5">
          <div class="max-w-2xl">
            <p class="mb-3 text-sm font-black uppercase tracking-[.2em] text-sky-600">这里不止一碗汤</p>
            <h2 class="text-3xl font-black text-slate-950 sm:text-4xl dark:text-white">把故事交给大家，<span class="text-sky-600">把线索留在这里。</span></h2>
          </div>
          <p class="max-w-sm text-sm leading-6 text-slate-500 dark:text-slate-400">从第一句谜面开始，到最后一次恍然大悟，汤吧让每一次推理都有可以落脚的地方。</p>
        </div>
        <div class="mt-10 grid gap-5 md:grid-cols-3">
          <router-link v-for="(item, index) in featureCards" :key="item.title" :to="item.to" class="feature-card group relative overflow-hidden rounded-md border border-slate-200 bg-[#f8fcff] p-6 shadow-[6px_8px_0_rgba(125,178,204,.13)] transition hover:-translate-y-2 hover:rotate-[-1deg] hover:border-sky-300 hover:shadow-[10px_14px_0_rgba(125,178,204,.2)] dark:border-slate-800 dark:bg-slate-900" :style="{ animationDelay: `${index * 100 + 160}ms` }">
            <span class="feature-index absolute right-5 top-4 text-5xl font-black text-sky-100 transition group-hover:text-sky-200 dark:text-slate-800 dark:group-hover:text-slate-700">0{{ index + 1 }}</span>
            <span class="relative flex h-12 w-12 items-center justify-center rounded-md bg-sky-100 text-sky-700 shadow-[0_4px_0_rgba(56,154,190,.18)] transition group-hover:rotate-[-8deg] group-hover:bg-sky-600 group-hover:text-white dark:bg-sky-950 dark:text-sky-300"><component :is="item.icon" class="h-6 w-6" aria-hidden="true" /></span>
            <p class="relative mt-7 text-xs font-black uppercase tracking-[.16em] text-sky-600">{{ item.eyebrow }}</p>
            <h3 class="relative mt-2 text-xl font-black text-slate-900 dark:text-white">{{ item.title }}</h3>
            <p class="relative mt-3 text-sm leading-6 text-slate-600 dark:text-slate-400">{{ item.description }}</p>
            <span class="relative mt-6 inline-flex items-center gap-1 text-sm font-bold text-sky-700 transition group-hover:gap-2 dark:text-sky-300">进入看看 <ArrowUpRightIcon class="h-4 w-4" aria-hidden="true" /></span>
          </router-link>
        </div>
      </div>
    </section>

    <section class="home-section popular-section bg-[#f7fbff] px-5 py-16 sm:px-8 sm:py-20 lg:px-10 dark:bg-[#0c1827]">
      <div class="mx-auto max-w-7xl">
        <div class="mb-9 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p class="mb-3 text-sm font-black uppercase tracking-[.2em] text-orange-500">今日值得一试</p>
            <h2 class="text-3xl font-black text-slate-950 sm:text-4xl dark:text-white">热门海龟汤</h2>
          </div>
          <router-link to="/leaderboard" class="group inline-flex items-center gap-2 text-sm font-bold text-sky-700 transition hover:text-sky-500 dark:text-sky-300">打开完整榜单 <ArrowRightIcon class="h-4 w-4 transition-transform group-hover:translate-x-1" aria-hidden="true" /></router-link>
        </div>

        <div v-if="isLeaderboardPreviewLoading" class="loading-bowl flex min-h-64 items-center justify-center rounded-md border border-sky-100 bg-white/70 dark:border-slate-800 dark:bg-slate-900/70">
          <div class="flex flex-col items-center gap-4 text-sm font-bold text-sky-700 dark:text-sky-300"><span class="soup-loader" aria-hidden="true"><span></span></span><span>正在把好汤端上来…</span></div>
        </div>
        <div v-else-if="leaderboardPreviewError" class="rounded-md border border-rose-200 bg-rose-50 p-8 text-center text-sm font-medium text-rose-700 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-300">热门汤暂时没端上来，去列表看看吧。</div>
        <div v-else-if="leaderboardPreview.length" class="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          <article v-for="(soup, index) in leaderboardPreview.slice(0, 6)" :key="soup.id" class="soup-card group relative cursor-pointer overflow-hidden rounded-md border border-slate-200 bg-white p-6 shadow-[5px_7px_0_rgba(86,139,165,.12)] transition hover:-translate-y-2 hover:shadow-[9px_13px_0_rgba(86,139,165,.2)] dark:border-slate-800 dark:bg-slate-950" :style="{ animationDelay: `${index * 80 + 120}ms` }" @click="$router.push(`/soups/${soup.id}`)">
            <div class="flex items-start justify-between gap-4">
              <span class="rank-badge flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-lg font-black text-white" :class="rankClass(index)">{{ index + 1 }}</span>
              <span class="inline-flex items-center gap-1 text-sm font-black text-amber-500"><StarIcon class="h-4 w-4" aria-hidden="true" />{{ soup.average_score.toFixed(1) }}</span>
            </div>
            <h3 class="mt-6 line-clamp-2 break-words text-xl font-black text-slate-900 dark:text-white">{{ soup.title }}</h3>
            <div class="mt-3 flex flex-wrap gap-2">
              <span :class="genreBadgeClass(soup.genre)">流派 · {{ soup.genre }}</span>
              <span :class="soupColorBadgeClass(soup.soup_color)">汤色 · {{ soup.soup_color }}</span>
            </div>
            <p class="mt-3 line-clamp-3 min-h-[4.5rem] break-words text-sm leading-6 text-slate-500 dark:text-slate-400">{{ soup.puzzle }}</p>
            <div class="mt-6 flex items-center justify-between gap-3 border-t border-slate-100 pt-4 text-xs font-semibold text-slate-400 dark:border-slate-800 dark:text-slate-500"><span class="truncate">{{ soup.author?.nickname || soup.author?.username || '匿名作者' }}</span><span class="shrink-0">{{ soup.rating_count }} 人评分</span></div>
            <span class="soup-card-shine absolute -right-16 -top-20 h-32 w-32 rounded-full bg-sky-200/35 blur-2xl transition duration-500 group-hover:right-8 group-hover:top-4 dark:bg-sky-500/10" aria-hidden="true"></span>
          </article>
        </div>
        <div v-else class="rounded-md border border-dashed border-sky-200 bg-white/70 p-12 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-400">暂无数据，成为第一个发布谜面的人吧。</div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { CSSProperties } from 'vue'
import {
  ArrowRightIcon,
  ArrowUpRightIcon,
  ChatBubbleLeftRightIcon,
  CheckCircleIcon,
  ChevronDownIcon,
  FlagIcon,
  PencilSquareIcon,
  PuzzlePieceIcon,
  SparklesIcon,
  TrophyIcon,
} from '@heroicons/vue/24/outline'
import { StarIcon } from '@heroicons/vue/20/solid'
import { useSoupStore } from '@/stores/soup'
import { useAuthStore } from '@/stores/auth'
import type { TurtleSoup } from '@/types'
import { genreBadgeClass, soupColorBadgeClass } from '@/utils/soupMetadata'

const soupStore = useSoupStore()
const authStore = useAuthStore()
const accountStatus = computed(() => (authStore.user?.status || authStore.restrictionStatus) === 'banned'
  ? { label: '已封禁', className: 'border-red-300 bg-red-50 text-red-700' }
  : (authStore.user?.status || authStore.restrictionStatus) === 'silenced'
    ? { label: '已禁言', className: 'border-amber-300 bg-amber-50 text-amber-800' }
    : null)
const leaderboardPreview = ref<TurtleSoup[]>([])
const isLeaderboardPreviewLoading = ref(true)
const leaderboardPreviewError = ref<string | null>(null)
const heroRef = ref<HTMLElement | null>(null)
const scenePosition = ref({ x: 0, y: 0 })
const hitokotoText = ref('每一条线索都算数')
type ScenePeriod = 'sunrise' | 'morning' | 'noon' | 'evening' | 'sunset' | 'night'
const scenePeriod = ref<ScenePeriod>('noon')
const titleCharacters = Array.from('汤吧社区')
const featureCards = [
  { to: '/soups', eyebrow: 'Find a clue', title: '发现海龟汤', description: '从热门、标签和排行榜找到下一道值得追的谜题。', icon: PuzzlePieceIcon },
  { to: '/posts', eyebrow: 'Share a thought', title: '一起讨论', description: '把你的推理过程写下来，让每一个“为什么”都有回应。', icon: ChatBubbleLeftRightIcon },
  { to: '/competitions', eyebrow: 'Make a mark', title: '参加比赛', description: '用作品、评分和排行榜，记录每一次灵感发光。', icon: TrophyIcon },
]
let pointerFrame = 0
let hitokotoController: AbortController | null = null
let hitokotoTimeout = 0
let sceneClock = 0

const sceneStyle = computed<CSSProperties>(() => ({
  '--far-x': `${scenePosition.value.x * 0.18}px`,
  '--far-y': `${scenePosition.value.y * 0.18}px`,
  '--mid-x': `${scenePosition.value.x * 0.38}px`,
  '--mid-y': `${scenePosition.value.y * 0.38}px`,
  '--lake-x': `${scenePosition.value.x * 0.62}px`,
  '--lake-y': `${scenePosition.value.y * 0.62}px`,
  '--front-x': `${scenePosition.value.x}px`,
  '--front-y': `${scenePosition.value.y}px`,
}))

function handlePointerMove(event: PointerEvent) {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || event.pointerType === 'touch') return
  const element = event.currentTarget as HTMLElement
  const bounds = element.getBoundingClientRect()
  const x = Math.max(-14, Math.min(14, ((event.clientX - bounds.left) / bounds.width - 0.5) * 28))
  const y = Math.max(-10, Math.min(10, ((event.clientY - bounds.top) / bounds.height - 0.5) * 20))
  cancelAnimationFrame(pointerFrame)
  pointerFrame = requestAnimationFrame(() => {
    scenePosition.value = { x, y }
  })
}

function resetPointer() {
  cancelAnimationFrame(pointerFrame)
  scenePosition.value = { x: 0, y: 0 }
}

function rankClass(index: number) {
  if (index === 0) return 'rank-gold'
  if (index === 1) return 'rank-silver'
  if (index === 2) return 'rank-bronze'
  return 'rank-blue'
}

function chinaMinutes(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    timeZone: 'Asia/Shanghai',
  }).formatToParts(date)
  const hour = Number(parts.find((part) => part.type === 'hour')?.value || 0)
  const minute = Number(parts.find((part) => part.type === 'minute')?.value || 0)
  return hour * 60 + minute
}

function updateScenePeriod() {
  const minutes = chinaMinutes()
  if (minutes >= 390 && minutes < 420) scenePeriod.value = 'sunrise'
  else if (minutes >= 420 && minutes < 540) scenePeriod.value = 'morning'
  else if (minutes >= 540 && minutes < 1020) scenePeriod.value = 'noon'
  else if (minutes >= 1020 && minutes < 1140) scenePeriod.value = 'evening'
  else if (minutes >= 1140 && minutes < 1200) scenePeriod.value = 'sunset'
  else scenePeriod.value = 'night'
}

async function loadLeaderboardPreview() {
  isLeaderboardPreviewLoading.value = true
  leaderboardPreviewError.value = null
  try {
    leaderboardPreview.value = await soupStore.fetchLeaderboardPreview(10)
  } catch {
    leaderboardPreviewError.value = '获取排行榜失败'
  } finally {
    isLeaderboardPreviewLoading.value = false
  }
}

async function loadHitokoto() {
  hitokotoController?.abort()
  const controller = new AbortController()
  hitokotoController = controller
  hitokotoTimeout = window.setTimeout(() => controller.abort(), 6000)

  try {
    const response = await fetch('https://v1.hitokoto.cn/?encode=json', {
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    })
    if (!response.ok) return

    const payload: unknown = await response.json()
    if (!payload || typeof payload !== 'object') return
    const value = (payload as { hitokoto?: unknown }).hitokoto
    if (typeof value === 'string' && value.trim()) hitokotoText.value = value.trim()
  } catch {
    // Keep the local fallback when the third-party service is unavailable.
  } finally {
    window.clearTimeout(hitokotoTimeout)
    if (hitokotoController === controller) hitokotoController = null
  }
}

onMounted(() => {
  updateScenePeriod()
  sceneClock = window.setInterval(updateScenePeriod, 60_000)
  void loadLeaderboardPreview()
  void loadHitokoto()
})

onBeforeUnmount(() => {
  cancelAnimationFrame(pointerFrame)
  window.clearInterval(sceneClock)
  window.clearTimeout(hitokotoTimeout)
  hitokotoController?.abort()
  hitokotoController = null
  heroRef.value = null
})
</script>

<style scoped>
.hero-scene {
  --sky-top: #a7e2ff;
  --sky-middle: #d9f4ff;
  --sky-bottom: #fff4d6;
  --scene-copy: #12354a;
  --scene-copy-muted: rgba(18, 53, 74, .78);
  --scene-link: #0f526d;
  --scene-title-one: #12354a;
  --scene-title-two: #075985;
  --scene-title-three: #166534;
  --scene-title-four: #9a3412;
  --far-x: 0px;
  --far-y: 0px;
  --mid-x: 0px;
  --mid-y: 0px;
  --lake-x: 0px;
  --lake-y: 0px;
  --front-x: 0px;
  --front-y: 0px;
}

.sky-stop-top { stop-color: var(--sky-top); }
.sky-stop-middle { stop-color: var(--sky-middle); }
.sky-stop-bottom { stop-color: var(--sky-bottom); }

.hero-sky {
  background: linear-gradient(130deg, rgba(255, 255, 255, 0.42), transparent 42%), linear-gradient(180deg, rgba(91, 192, 235, 0.25), rgba(255, 226, 146, 0.22));
}

.hero-sun {
  z-index: 4;
  right: 14%;
  top: 12%;
  width: 9rem;
  height: 9rem;
  border-radius: 50%;
  background: #ffe38b;
  box-shadow: 0 0 0 1.5rem rgba(255, 227, 139, 0.14), 0 0 5rem 2rem rgba(255, 230, 153, 0.35);
  animation: sun-breathe 6s ease-in-out infinite;
}

.hero-glint {
  z-index: 4;
  width: 15rem;
  height: 4rem;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.34);
  filter: blur(1rem);
  transform: rotate(-22deg);
  animation: glint-drift 9s ease-in-out infinite;
}

.hero-glint-one { left: 8%; top: 18%; }
.hero-glint-two { right: 8%; top: 36%; animation-delay: -4s; opacity: 0.55; }
.hero-mist { z-index: 3; pointer-events: none; opacity: 0; transition: opacity 1.5s ease, background 1.5s ease; }

.hero-scene,
.hero-sky,
.hero-sun,
.landscape {
  transition: background-color 1.5s ease, background 1.5s ease, filter 1.5s ease, opacity 1.5s ease, box-shadow 1.5s ease;
}

.scene-sunrise { --sky-top: #7485ba; --sky-middle: #ffad82; --sky-bottom: #ffe5ac; --scene-copy: #182b49; --scene-copy-muted: rgba(24, 43, 73, .84); --scene-link: #173f68; --scene-title-one: #182b49; --scene-title-two: #124e78; --scene-title-three: #245b43; --scene-title-four: #8c3f1f; background: #ffd8ad; }
.scene-sunrise .hero-sky { background: linear-gradient(180deg, rgba(93, 117, 177, .32), rgba(255, 153, 94, .42) 58%, rgba(255, 233, 180, .55)); }
.scene-sunrise .hero-sun { right: 17%; top: 53%; background: #ffb24f; box-shadow: 0 0 0 1.3rem rgba(255, 178, 79, .14), 0 0 5rem 2rem rgba(255, 123, 66, .3); }
.scene-sunrise .landscape { filter: sepia(.12) saturate(1.1) brightness(.88); }

.scene-morning { --sky-top: #c1e2e9; --sky-middle: #e8f2ed; --sky-bottom: #f6f6df; --scene-copy: #164e63; --scene-copy-muted: rgba(22, 78, 99, .78); --scene-link: #155e75; --scene-title-one: #164e63; --scene-title-two: #075985; --scene-title-three: #166534; --scene-title-four: #9a3412; background: #dff4f3; }
.scene-morning .hero-sky { background: linear-gradient(180deg, rgba(182, 225, 236, .4), rgba(238, 248, 242, .45)); }
.scene-morning .hero-sun { right: 16%; top: 25%; background: #ffe6a2; box-shadow: 0 0 4rem 1.5rem rgba(255, 230, 162, .25); }
.scene-morning .hero-mist { opacity: .7; background: linear-gradient(180deg, transparent 35%, rgba(241, 250, 248, .76) 62%, rgba(231, 244, 242, .36) 82%, transparent); filter: blur(.4rem); animation: mist-drift 18s ease-in-out infinite; }
.scene-morning .landscape { filter: saturate(.78) brightness(1.04); }

.scene-evening { --sky-top: #7199af; --sky-middle: #dcb886; --sky-bottom: #f6dca7; --scene-copy: #17324d; --scene-copy-muted: rgba(23, 50, 77, .84); --scene-link: #174e6d; --scene-title-one: #17324d; --scene-title-two: #124e78; --scene-title-three: #22543d; --scene-title-four: #8c3f1f; background: #b9d8df; }
.scene-evening .hero-sky { background: linear-gradient(180deg, rgba(91, 139, 167, .36), rgba(231, 186, 128, .42) 68%, rgba(252, 221, 166, .35)); }
.scene-evening .hero-sun { right: 12%; top: 34%; background: #f6c76b; box-shadow: 0 0 4rem 1.4rem rgba(246, 199, 107, .25); }
.scene-evening .landscape { filter: saturate(.88) brightness(.82); }

.scene-sunset { --sky-top: #343b6d; --sky-middle: #bd6269; --sky-bottom: #ff9f60; --scene-copy: #fff7ed; --scene-copy-muted: rgba(255, 247, 237, .86); --scene-link: #ffedd5; --scene-title-one: #fff7ed; --scene-title-two: #dbeafe; --scene-title-three: #dcfce7; --scene-title-four: #fed7aa; background: #8e7584; }
.scene-sunset .hero-sky { background: linear-gradient(180deg, rgba(51, 58, 106, .5), rgba(192, 85, 89, .42) 56%, rgba(255, 161, 85, .52)); }
.scene-sunset .hero-sun { right: 15%; top: 57%; background: #ff875d; box-shadow: 0 0 0 1.2rem rgba(255, 135, 93, .12), 0 0 5rem 2rem rgba(236, 79, 84, .32); }
.scene-sunset .landscape { filter: sepia(.18) hue-rotate(-8deg) saturate(1.05) brightness(.57); }

.scene-night { --sky-top: #050d1b; --sky-middle: #102a40; --sky-bottom: #17374b; --scene-copy: #d9f6ff; --scene-copy-muted: rgba(217, 246, 255, .84); --scene-link: #e0f2fe; --scene-title-one: #e7fbff; --scene-title-two: #67d8f0; --scene-title-three: #7ce0b2; --scene-title-four: #ffc16f; background: #061321; }
.scene-night .hero-sky { background: radial-gradient(circle at 20% 18%, rgba(149, 199, 223, .12) 0 1px, transparent 2px), radial-gradient(circle at 67% 13%, rgba(255, 255, 255, .2) 0 1px, transparent 2px), linear-gradient(180deg, #06101f, #102a40 70%, #17374b); background-size: 9rem 8rem, 13rem 11rem, auto; }
.scene-night .hero-sun { right: 14%; top: 13%; background: #e8eff1; box-shadow: inset -1.8rem -.6rem 0 #becdd4, 0 0 3rem 1rem rgba(211, 235, 242, .18); }
.scene-night .hero-glint { opacity: .12; }
.scene-night .landscape { filter: hue-rotate(8deg) saturate(.58) brightness(.32); }

.landscape {
  z-index: 2;
  pointer-events: none;
}

.landscape-layer { transform-box: fill-box; transform-origin: center; transition: transform 700ms cubic-bezier(.2,.75,.25,1); }
.layer-far { transform: translate3d(var(--far-x), var(--far-y), 0); }
.layer-mid { transform: translate3d(var(--mid-x), var(--mid-y), 0); }
.layer-lake { transform: translate3d(var(--lake-x), var(--lake-y), 0); }
.layer-foreground, .layer-grass { transform: translate3d(var(--front-x), var(--front-y), 0); }
.layer-cloud-back { transform: translate3d(var(--far-x), var(--far-y), 0); }
.layer-cloud-front { transform: translate3d(var(--mid-x), var(--mid-y), 0); }

.cloud-drift-slow { animation: cloud-drift 32s linear infinite; }
.cloud-drift-fast { animation: cloud-drift 22s linear infinite reverse; }
.lake-shimmer { animation: lake-shimmer 8s ease-in-out infinite; }

.hero-container { animation: hero-settle 700ms cubic-bezier(.18,.8,.25,1) both; }
.hero-copy { animation: copy-enter 650ms cubic-bezier(.16,.8,.25,1) 100ms both; }
.hero-kicker, .hero-lede, .hero-actions, .hero-quick-links { animation: rise-in 650ms cubic-bezier(.18,.8,.25,1) both; }
.hero-kicker { animation-delay: 120ms; }
.hero-lede { animation-delay: 420ms; }
.hero-actions { animation-delay: 500ms; }
.hero-quick-links { animation-delay: 620ms; }

.hero-title { perspective: 900px; text-wrap: balance; }
.hero-title-character { display: inline-block; transform: translate3d(0, 1.8rem, 0) rotateX(-65deg) rotateZ(-4deg); transform-origin: 50% 100%; opacity: 0; color: var(--scene-title-one) !important; text-shadow: none !important; animation: title-pop 800ms cubic-bezier(.18,1.35,.3,1) forwards; }
.hero-title-character:nth-child(2) { color: var(--scene-title-two) !important; }
.hero-title-character:nth-child(3) { color: var(--scene-title-three) !important; }
.hero-title-character:nth-child(4) { color: var(--scene-title-four) !important; }

.hero-kicker { color: var(--scene-copy) !important; }
.hero-lede { color: var(--scene-copy-muted) !important; }
.hero-quick-links, .hero-quick-links a, .hero-scroll-cue { color: var(--scene-link) !important; }
.hero-quick-links a:hover, .hero-scroll-cue:hover { color: var(--scene-copy) !important; }
.hero-secondary-button { color: var(--scene-copy) !important; }

.hero-puzzle-stage { animation: puzzle-stage-enter 800ms cubic-bezier(.18,.8,.25,1) 420ms both; perspective: 900px; }
.puzzle-note { backface-visibility: hidden; transform-origin: center bottom; animation: note-enter 800ms cubic-bezier(.18,1.2,.3,1) both, note-float 6s ease-in-out 1.2s infinite; }
.puzzle-note-back { --note-rotate: -9deg; animation-delay: 650ms, -1.4s; }
.puzzle-note-middle { --note-rotate: 8deg; animation-delay: 760ms, -3.6s; }
.puzzle-note-front { --note-rotate: -3deg; animation-delay: 870ms, -2.3s; }
.puzzle-sticker { animation: sticker-pop 700ms cubic-bezier(.2,1.45,.3,1) 1.2s both, sticker-wiggle 7s ease-in-out 2s infinite; }

.hero-scroll-cue { animation: scroll-cue 2s ease-in-out infinite; }
.feature-card, .soup-card { animation: card-rise 650ms cubic-bezier(.18,.8,.25,1) both; }
.feature-card:hover, .soup-card:hover { transform-origin: center bottom; }
.feature-index { line-height: 1; }

.rank-gold { background: linear-gradient(145deg, #f6c453, #d88b17); box-shadow: 0 4px 0 #b16b10; }
.rank-silver { background: linear-gradient(145deg, #b9c9d4, #71899b); box-shadow: 0 4px 0 #536b7e; }
.rank-bronze { background: linear-gradient(145deg, #e99a62, #b85b31); box-shadow: 0 4px 0 #934226; }
.rank-blue { background: linear-gradient(145deg, #38a7c6, #2873a7); box-shadow: 0 4px 0 #1f597e; }

.soup-loader { position: relative; display: block; width: 3.6rem; height: 2rem; border: 4px solid #42a8bf; border-top: 0; border-radius: 0 0 3rem 3rem; animation: bowl-bob 1.4s ease-in-out infinite; }
.soup-loader::before { content: ''; position: absolute; left: 50%; top: -0.35rem; width: 4.5rem; height: .45rem; transform: translateX(-50%); border-radius: 50%; background: #42a8bf; }
.soup-loader span { position: absolute; left: .6rem; top: -.85rem; width: .35rem; height: 1rem; border-radius: 50%; background: #f3b55f; animation: steam-rise 1.3s ease-in-out infinite; }
.soup-loader span::after { content: ''; position: absolute; left: .8rem; top: .2rem; width: .3rem; height: .7rem; border-radius: 50%; background: #f3b55f; animation: steam-rise 1.3s ease-in-out .3s infinite; }

@keyframes hero-settle { from { opacity: 0; transform: translateY(1.2rem); } to { opacity: 1; transform: translateY(0); } }
@keyframes copy-enter { from { opacity: 0; transform: translateX(-1.2rem); } to { opacity: 1; transform: translateX(0); } }
@keyframes rise-in { from { opacity: 0; transform: translateY(1rem); } to { opacity: 1; transform: translateY(0); } }
@keyframes title-pop { 0% { opacity: 0; transform: translate3d(0, 1.8rem, 0) rotateX(-65deg) rotateZ(-4deg); } 68% { opacity: 1; transform: translate3d(0, -.35rem, 0) rotateX(8deg) rotateZ(1deg); } 100% { opacity: 1; transform: translate3d(0, 0, 0) rotateX(0) rotateZ(0); } }
@keyframes puzzle-stage-enter { from { opacity: 0; transform: translate3d(1.2rem, 1rem, 0) rotateY(-9deg); } to { opacity: 1; transform: translate3d(0, 0, 0) rotateY(0); } }
@keyframes note-enter { from { opacity: 0; transform: translate3d(0, 2rem, 0) rotate(var(--note-rotate, 0deg)) scale(.86); } to { opacity: 1; transform: translate3d(0, 0, 0) rotate(var(--note-rotate, 0deg)) scale(1); } }
@keyframes note-float { 0%, 100% { margin-top: 0; } 50% { margin-top: -.55rem; } }
@keyframes sticker-pop { from { opacity: 0; transform: scale(.2) rotate(-30deg); } to { opacity: 1; transform: scale(1) rotate(12deg); } }
@keyframes sticker-wiggle { 0%, 100% { rotate: 12deg; } 50% { rotate: 7deg; } }
@keyframes sun-breathe { 0%, 100% { transform: scale(1); opacity: .86; } 50% { transform: scale(1.06); opacity: 1; } }
@keyframes glint-drift { 0%, 100% { translate: 0 0; } 50% { translate: 2rem 1rem; } }
@keyframes cloud-drift { from { translate: -3rem 0; } to { translate: 3rem 0; } }
@keyframes lake-shimmer { 0%, 100% { opacity: .4; transform: translateX(-1.5rem); } 50% { opacity: .8; transform: translateX(1.5rem); } }
@keyframes scroll-cue { 0%, 100% { transform: translate(-50%, 0); } 50% { transform: translate(-50%, .35rem); } }
@keyframes card-rise { from { opacity: 0; transform: translateY(1.5rem) rotate(1deg); } to { opacity: 1; transform: translateY(0) rotate(0); } }
@keyframes bowl-bob { 0%, 100% { transform: translateY(0) rotate(-2deg); } 50% { transform: translateY(-.3rem) rotate(2deg); } }
@keyframes steam-rise { 0%, 100% { opacity: .35; transform: translateY(.3rem) scale(.85); } 50% { opacity: 1; transform: translateY(-.35rem) scale(1); } }
@keyframes mist-drift { 0%, 100% { transform: translateX(-2%); } 50% { transform: translateX(2%); } }

@media (max-width: 639px) {
  .hero-sun { right: -2rem; top: 8%; width: 7rem; height: 7rem; }
  .hero-glint-two, .cloud-drift-fast { display: none; }
  .puzzle-note { padding: 1rem; }
  .puzzle-note p { font-size: 1rem; line-height: 1.5rem; }
  .puzzle-note-back { left: 0; width: 76%; }
  .puzzle-note-middle { right: 0; width: 73%; }
  .puzzle-note-front { left: 10%; width: 78%; }
  .puzzle-sticker { right: 0; height: 4rem; width: 4rem; border-width: 3px; font-size: .65rem; }
}

:global(.dark) .hero-scene { border-color: #193247; }
:global(.dark) .hero-scene:not(.scene-night) .hero-sky { opacity: .88; }
:global(.dark) .hero-scene:not(.scene-night) .hero-sun { filter: brightness(.92) saturate(.9); }
:global(.dark) .hero-scene:not(.scene-night) .landscape { opacity: .92; }

@media (prefers-reduced-motion: reduce) {
  .hero-sun, .hero-glint, .cloud-drift-slow, .cloud-drift-fast, .lake-shimmer, .hero-container, .hero-copy, .hero-kicker, .hero-lede, .hero-actions, .hero-quick-links, .hero-title-character, .hero-puzzle-stage, .puzzle-note, .puzzle-sticker, .hero-scroll-cue, .feature-card, .soup-card, .soup-loader, .soup-loader span, .soup-loader span::after { animation: none !important; transition: opacity 120ms ease !important; }
  .landscape-layer { transition: none; transform: none !important; }
}
</style>
