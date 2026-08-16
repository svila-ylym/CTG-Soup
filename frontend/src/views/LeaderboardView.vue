<template>
  <main class="leaderboard-page page-shell overflow-hidden">
    <div class="page-container">
      <header class="leaderboard-header glass-panel relative -mx-4 overflow-hidden border-y px-5 py-10 text-slate-950 sm:mx-0 sm:rounded-md sm:border sm:px-8 sm:py-12 dark:text-white">
        <div class="relative z-10 grid gap-8 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
          <div class="max-w-2xl">
            <p class="mb-3 inline-flex items-center gap-2 text-sm font-bold text-amber-700 dark:text-amber-300">
              <SparklesIcon class="h-5 w-5" aria-hidden="true" />
              {{ activeCopy.eyebrow }}
            </p>
            <h1 class="text-3xl font-black text-slate-950 sm:text-5xl dark:text-white">{{ activeCopy.title }}</h1>
            <p class="mt-4 max-w-xl text-sm leading-6 text-slate-600 sm:text-base dark:text-slate-300">{{ activeCopy.description }}</p>
          </div>
          <dl v-if="displayedEntries.length" class="leaderboard-stats grid grid-cols-2 gap-3 sm:flex">
            <div>
              <dt class="text-xs font-semibold text-slate-500 dark:text-slate-400">入榜作品</dt>
              <dd class="mt-1 text-2xl font-black text-slate-950 dark:text-white">{{ displayedEntries.length }}</dd>
            </div>
            <div>
              <dt class="text-xs font-semibold text-slate-500 dark:text-slate-400">累计评分</dt>
              <dd class="mt-1 text-2xl font-black text-amber-700 dark:text-amber-300">{{ totalRatings }}</dd>
            </div>
          </dl>
        </div>
      </header>

      <nav class="mt-6 flex justify-center sm:justify-start" aria-label="社区排行榜分类">
        <div class="leaderboard-tabs relative grid w-full max-w-sm grid-cols-2 p-1" role="tablist">
          <span
            class="leaderboard-tab-indicator"
            :class="{ 'is-bie': activeScope === 'bie' }"
            aria-hidden="true"
          ></span>
          <button
            v-for="option in scopeOptions"
            :key="option.value"
            class="leaderboard-tab relative z-10 min-h-11 px-5 text-sm font-bold"
            :class="activeScope === option.value ? 'is-active' : ''"
            type="button"
            role="tab"
            :aria-selected="activeScope === option.value"
            @click="selectScope(option.value)"
          >
            {{ option.label }}
          </button>
        </div>
      </nav>

      <div ref="leaderboardContentRef" class="leaderboard-scope-stage">
        <section v-if="initialLoading" class="py-10" aria-live="polite" aria-label="正在加载排行榜">
          <div class="grid gap-5 md:grid-cols-3">
            <div v-for="index in 3" :key="index" class="surface-card h-72 animate-pulse bg-slate-100 dark:bg-neutral-900"></div>
          </div>
          <div class="mt-10 space-y-3">
            <div v-for="index in 5" :key="index" class="surface-card h-24 animate-pulse bg-slate-100 dark:bg-neutral-900"></div>
          </div>
        </section>

        <section v-else-if="loadError && !displayedEntries.length" class="py-16 text-center" aria-live="polite">
          <ExclamationCircleIcon class="mx-auto h-12 w-12 text-rose-500" aria-hidden="true" />
          <h2 class="mt-4 text-lg font-bold text-slate-900 dark:text-white">榜单暂时没有加载出来</h2>
          <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">{{ loadError }}</p>
          <button class="btn-primary mt-6" type="button" @click="retryLeaderboard">
            <ArrowPathIcon class="mr-2 h-5 w-5" aria-hidden="true" />
            重新加载
          </button>
        </section>

        <Transition v-else :name="transitionName" appear>
          <div
            :key="displayedScope"
            class="leaderboard-scope-panel"
            :aria-busy="switching"
          >
            <div v-if="loadError" class="leaderboard-inline-error" role="status">
              <span>{{ loadError }}</span>
              <button type="button" @click="retryLeaderboard">重试</button>
            </div>

            <template v-if="displayedEntries.length">
              <section class="pt-12" aria-labelledby="podium-heading">
          <div class="mb-6 flex items-end justify-between gap-4">
            <div>
              <p class="text-xs font-black text-amber-600 dark:text-amber-400">TOP 3</p>
              <h2 id="podium-heading" class="mt-1 text-2xl font-black text-slate-950 dark:text-white">本期前三名</h2>
            </div>
            <TrophyIcon class="h-9 w-9 text-amber-500" aria-hidden="true" />
          </div>

          <div class="podium-grid grid gap-5 md:grid-cols-3 md:items-end">
            <router-link
              v-for="(soup, index) in topThree"
              :key="soup.id"
              :to="`/soups/${soup.id}`"
              class="competition-border-surface podium-card glass-card group relative flex min-w-0 flex-col p-6 text-slate-900 dark:text-white"
              :class="podiumClass(index)"
              :style="competitionBorderStyle(soup.competition_colors)"
            >
              <div class="flex items-start justify-between gap-4">
                <span class="podium-rank flex h-12 w-12 shrink-0 items-center justify-center rounded-md text-xl font-black text-white" :class="rankClass(index)">{{ index + 1 }}</span>
                <span class="inline-flex items-center gap-1 text-lg font-black text-amber-500"><StarIcon class="h-5 w-5" aria-hidden="true" />{{ formatScore(soup.average_score) }}</span>
              </div>

              <div class="mt-6 min-w-0 flex-1">
                <p class="mb-2 text-xs font-bold" :class="placementTextClass(index)">{{ placementLabel(index) }}</p>
                <h3 class="line-clamp-2 break-words text-xl font-black leading-7 transition group-hover:text-blue-700" :class="soup.is_hall_of_fame ? 'hall-title' : 'text-slate-950 dark:text-white dark:group-hover:text-blue-300'">{{ soup.title }}</h3>
                <p class="mt-3 line-clamp-3 break-words text-sm leading-6 text-slate-500 dark:text-slate-400">{{ soup.puzzle }}</p>
              </div>

              <div class="mt-6 flex min-w-0 items-center justify-between gap-3 border-t border-slate-100 pt-4 dark:border-neutral-800">
                <div class="flex min-w-0 items-center gap-2">
                  <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-black text-white">{{ authorInitial(soup.author?.nickname) }}</span>
                  <span class="truncate text-sm font-semibold text-slate-600 dark:text-slate-300">{{ soup.author?.nickname || '未知作者' }}</span>
                </div>
                <span class="shrink-0 text-xs font-medium text-slate-400">{{ soup.rating_count }} 人评分</span>
              </div>
              <span class="podium-accent absolute inset-x-0 bottom-0 h-1" :class="accentClass(index)" aria-hidden="true"></span>
            </router-link>
          </div>
              </section>

              <section v-if="remainingEntries.length" class="pb-4 pt-14" aria-labelledby="ranking-heading">
          <div class="mb-5 flex flex-wrap items-end justify-between gap-3 border-b border-slate-200 pb-4 dark:border-neutral-800">
            <div>
              <p class="text-xs font-black text-blue-600 dark:text-blue-400">RANKING</p>
              <h2 id="ranking-heading" class="mt-1 text-2xl font-black text-slate-950 dark:text-white">完整榜单</h2>
            </div>
            <span class="text-sm text-slate-500 dark:text-slate-400">按作品平均分排序</span>
          </div>

          <div class="space-y-3">
            <router-link
              v-for="(soup, index) in remainingEntries"
              :key="soup.id"
              :to="`/soups/${soup.id}`"
              class="competition-border-surface ranking-row group grid min-w-0 grid-cols-[2.75rem_minmax(0,1fr)] items-center gap-3 rounded-md border border-slate-200 bg-white p-4 transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-lg dark:border-neutral-800 dark:bg-neutral-950 dark:hover:border-blue-800 sm:grid-cols-[3rem_minmax(0,1fr)_auto] sm:gap-5"
              :style="competitionBorderStyle(soup.competition_colors)"
            >
              <span class="flex h-10 w-10 items-center justify-center rounded-md bg-slate-100 text-sm font-black text-slate-600 transition group-hover:bg-blue-600 group-hover:text-white dark:bg-neutral-900 dark:text-slate-300">{{ index + 4 }}</span>

              <div class="min-w-0">
                <h3 class="truncate font-bold transition group-hover:text-blue-700" :class="soup.is_hall_of_fame ? 'hall-title' : 'text-slate-900 dark:text-white dark:group-hover:text-blue-300'">{{ soup.title }}</h3>
                <p class="mt-1 line-clamp-1 text-sm text-slate-500 dark:text-slate-400">{{ soup.puzzle }}</p>
                <div class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400">
                  <span class="truncate">{{ soup.author?.nickname || '未知作者' }}</span>
                  <span class="inline-flex items-center gap-1"><UsersIcon class="h-4 w-4" aria-hidden="true" />{{ soup.rating_count }} 人评分</span>
                  <span class="inline-flex items-center gap-1"><HandThumbUpIcon class="h-4 w-4" aria-hidden="true" />{{ soup.like_count }}</span>
                </div>
              </div>

              <div class="col-span-2 flex items-center justify-end gap-2 border-t border-slate-100 pt-3 text-amber-500 dark:border-neutral-800 sm:col-span-1 sm:border-0 sm:pt-0">
                <StarIcon class="h-5 w-5" aria-hidden="true" />
                <strong class="text-lg">{{ formatScore(soup.average_score) }}</strong>
                <ChevronRightIcon class="ml-1 h-5 w-5 text-slate-300 transition group-hover:translate-x-1 group-hover:text-blue-500 dark:text-neutral-700" aria-hidden="true" />
              </div>
            </router-link>
          </div>
              </section>
            </template>

            <section v-else class="py-20 text-center">
              <ChartBarIcon class="mx-auto h-12 w-12 text-slate-400" aria-hidden="true" />
              <h2 class="mt-4 text-lg font-bold text-slate-900 dark:text-white">暂无上榜作品</h2>
              <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">{{ activeCopy.empty }}</p>
              <router-link to="/soups" class="btn-primary mt-6">去看看海龟汤</router-link>
            </section>
          </div>
        </Transition>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import {
  ArrowPathIcon,
  ChartBarIcon,
  ChevronRightIcon,
  ExclamationCircleIcon,
  HandThumbUpIcon,
  SparklesIcon,
  TrophyIcon,
  UsersIcon,
} from '@heroicons/vue/24/outline'
import { StarIcon } from '@heroicons/vue/20/solid'
import { useSoupStore } from '@/stores/soup'
import type { LeaderboardScope } from '@/api/soup'
import type { TurtleSoup } from '@/types'
import { competitionBorderStyle } from '@/utils/competitionBorder'

const soupStore = useSoupStore()
const activeScope = ref<LeaderboardScope>('regular')
const displayedScope = ref<LeaderboardScope>('regular')
const displayedEntries = ref<TurtleSoup[]>([])
const initialLoading = ref(true)
const switching = ref(false)
const loadError = ref<string | null>(null)
const failedScope = ref<LeaderboardScope | null>(null)
const transitionName = ref('leaderboard-forward')
const leaderboardContentRef = ref<HTMLElement | null>(null)
let leaderboardRequestId = 0
const scopeOptions: Array<{ value: LeaderboardScope; label: string }> = [
  { value: 'regular', label: '海龟汤榜' },
  { value: 'bie', label: '鳖汤榜' },
]
const copyByScope: Record<LeaderboardScope, { eyebrow: string; title: string; description: string; empty: string }> = {
  regular: {
    eyebrow: '社区高分作品',
    title: '海龟汤排行榜',
    description: '评分会实时改变席位。看看哪些谜面经得住最多人的追问。',
    empty: '新的海龟汤评分出现后，榜单会在这里更新。',
  },
  bie: {
    eyebrow: '社区整活作品',
    title: '鳖汤排行榜',
    description: '鳖汤拥有自己的席位，不再与本格、变格作品混排。',
    empty: '新的鳖汤评分出现后，榜单会在这里更新。',
  },
}
const activeCopy = computed(() => copyByScope[displayedScope.value])
const topThree = computed(() => displayedEntries.value.slice(0, 3))
const remainingEntries = computed(() => displayedEntries.value.slice(3))
const totalRatings = computed(() => displayedEntries.value.reduce((total, soup) => total + soup.rating_count, 0))

function errorMessage(error: any) {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  return detail?.message || '获取排行榜失败'
}

async function loadLeaderboard(scope: LeaderboardScope = activeScope.value) {
  const requestId = ++leaderboardRequestId
  switching.value = !initialLoading.value
  loadError.value = null
  failedScope.value = null
  try {
    const entries = await soupStore.fetchLeaderboard(50, scope)
    if (requestId !== leaderboardRequestId) return
    transitionName.value = scope === 'bie' ? 'leaderboard-forward' : 'leaderboard-backward'
    displayedEntries.value = entries
    displayedScope.value = scope
  } catch (error: any) {
    if (requestId !== leaderboardRequestId) return
    loadError.value = errorMessage(error)
    failedScope.value = scope
    activeScope.value = displayedScope.value
  } finally {
    if (requestId === leaderboardRequestId) {
      initialLoading.value = false
      switching.value = false
    }
  }
}

function retryLeaderboard() {
  const scope = failedScope.value || activeScope.value
  activeScope.value = scope
  void loadLeaderboard(scope)
}

async function selectScope(scope: LeaderboardScope) {
  if (scope === activeScope.value) return
  activeScope.value = scope
  await nextTick()
  leaderboardContentRef.value?.scrollIntoView({
    behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
    block: 'start',
  })
  void loadLeaderboard(scope)
}

function formatScore(score: number) {
  return Number.isFinite(score) ? score.toFixed(2) : '0.00'
}

function authorInitial(nickname?: string) {
  return Array.from(nickname || '')[0]?.toUpperCase() || 'U'
}

function placementLabel(index: number) {
  return ['冠军作品', '亚军作品', '季军作品'][index] || '上榜作品'
}

function podiumClass(index: number) {
  return [`podium-place-${index + 1}`, index === 0 ? 'border-amber-300 dark:border-amber-700' : index === 1 ? 'border-slate-300 dark:border-slate-700' : 'border-orange-300 dark:border-orange-800']
}

function rankClass(index: number) {
  return index === 0 ? 'rank-gold' : index === 1 ? 'rank-silver' : 'rank-bronze'
}

function placementTextClass(index: number) {
  return index === 0 ? 'text-amber-600 dark:text-amber-400' : index === 1 ? 'text-slate-500 dark:text-slate-400' : 'text-orange-600 dark:text-orange-400'
}

function accentClass(index: number) {
  return index === 0 ? 'bg-amber-400' : index === 1 ? 'bg-slate-400' : 'bg-orange-500'
}

onMounted(loadLeaderboard)
</script>

<style scoped>
.leaderboard-header {
  border-color: rgba(148, 163, 184, .28);
  background: rgba(255, 255, 255, .66);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .92), 0 1.25rem 3.5rem rgba(15, 23, 42, .09);
}

:global(.dark .leaderboard-header) {
  border-color: rgba(255, 255, 255, .11);
  background: rgba(8, 8, 8, .7);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .08), 0 1.25rem 3.5rem rgba(0, 0, 0, .42);
}

.leaderboard-header::after {
  content: '';
  position: absolute;
  right: -4rem;
  bottom: -5rem;
  width: 15rem;
  height: 13rem;
  background: #f59e0b;
  clip-path: polygon(44% 0, 100% 28%, 72% 100%, 0 72%);
  opacity: .16;
  transform: rotate(-8deg);
  animation: header-mark-float 8s ease-in-out infinite;
}

:global(.dark .leaderboard-header::after) {
  opacity: .11;
}

.leaderboard-stats > div {
  min-width: 7.5rem;
  padding: .85rem 1rem;
  border: 1px solid rgba(148, 163, 184, .24);
  border-radius: .5rem;
  background: rgba(255, 255, 255, .44);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .82);
}

:global(.dark .leaderboard-stats > div) {
  border-color: rgba(255, 255, 255, .1);
  background: rgba(255, 255, 255, .035);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .055);
}

.leaderboard-tabs {
  isolation: isolate;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, .3);
  border-radius: .625rem;
  background: rgba(255, 255, 255, .54);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .9), 0 .75rem 2rem rgba(15, 23, 42, .1);
  -webkit-backdrop-filter: blur(20px) saturate(155%);
  backdrop-filter: blur(20px) saturate(155%);
}

:global(.dark .leaderboard-tabs) {
  border-color: rgba(255, 255, 255, .12);
  background: rgba(10, 10, 10, .62);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .08), 0 .75rem 2rem rgba(0, 0, 0, .34);
}

.leaderboard-tab-indicator {
  position: absolute;
  z-index: 0;
  inset: .25rem 50% .25rem .25rem;
  border: 1px solid rgba(255, 255, 255, .72);
  border-radius: .45rem;
  background: linear-gradient(135deg, rgba(37, 99, 235, .94), rgba(14, 116, 144, .86));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .35), 0 .4rem 1rem rgba(37, 99, 235, .24);
  transform: translateX(0);
  transition: transform 420ms cubic-bezier(.22, 1, .36, 1), box-shadow 320ms ease;
}

.leaderboard-tab-indicator.is-bie {
  transform: translateX(100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .34), 0 .4rem 1rem rgba(14, 116, 144, .25);
}

.leaderboard-tab {
  border-radius: .45rem;
  color: #475569;
  transition: color 260ms ease, text-shadow 260ms ease;
}

.leaderboard-tab:hover {
  color: #0f172a;
}

.leaderboard-tab.is-active {
  color: #fff;
  text-shadow: 0 1px 1px rgba(15, 23, 42, .28);
}

:global(.dark .leaderboard-tab) {
  color: #cbd5e1;
}

:global(.dark .leaderboard-tab:hover) {
  color: #fff;
}

.leaderboard-scope-stage {
  position: relative;
  min-height: 20rem;
  scroll-margin-top: 6.5rem;
}

.leaderboard-scope-panel {
  width: 100%;
}

.leaderboard-inline-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 1rem;
  padding: .75rem 1rem;
  border: 1px solid rgba(244, 63, 94, .25);
  border-radius: .5rem;
  background: rgba(255, 241, 242, .72);
  color: #be123c;
  font-size: .875rem;
  backdrop-filter: blur(14px);
}

.leaderboard-inline-error button {
  flex: none;
  font-weight: 800;
}

:global(.dark .leaderboard-inline-error) {
  border-color: rgba(251, 113, 133, .24);
  background: rgba(76, 5, 25, .42);
  color: #fda4af;
}

.leaderboard-forward-enter-active,
.leaderboard-forward-leave-active,
.leaderboard-backward-enter-active,
.leaderboard-backward-leave-active {
  transition: opacity 320ms ease, transform 400ms cubic-bezier(.22, 1, .36, 1);
  will-change: opacity, transform;
}

.leaderboard-forward-leave-active,
.leaderboard-backward-leave-active {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.leaderboard-forward-enter-from,
.leaderboard-backward-leave-to {
  opacity: 0;
  transform: translate3d(1.5rem, 0, 0);
}

.leaderboard-forward-leave-to,
.leaderboard-backward-enter-from {
  opacity: 0;
  transform: translate3d(-1.5rem, 0, 0);
}

.podium-card,
.ranking-row {
  opacity: 1;
}

.podium-card {
  --competition-card-bg: rgba(255, 255, 255, .78);
  min-height: 19rem;
  border-color: rgba(148, 163, 184, .28);
  background-color: rgba(255, 255, 255, .78);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .9), 6px 8px 0 rgba(15, 23, 42, .07), 0 1rem 2.5rem rgba(15, 23, 42, .08);
  transition: transform 280ms cubic-bezier(.2, .75, .25, 1), box-shadow 280ms ease, border-color 280ms ease;
}

:global(.dark .podium-card) {
  --competition-card-bg: rgba(13, 13, 13, .8);
  border-color: rgba(255, 255, 255, .12);
  background-color: rgba(13, 13, 13, .8);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .07), 6px 8px 0 rgba(0, 0, 0, .3), 0 1rem 2.5rem rgba(0, 0, 0, .28);
}

.podium-card:hover {
  transform: translateY(-.5rem);
  box-shadow: 9px 13px 0 rgba(15, 23, 42, .11), 0 18px 35px rgba(15, 23, 42, .1);
}

:global(.dark .podium-card:hover) {
  box-shadow: 9px 13px 0 rgba(0, 0, 0, .34), 0 18px 35px rgba(0, 0, 0, .28);
}

.rank-gold { background: #d99a16; box-shadow: 0 4px 0 #9f6506; }
.rank-silver { background: #718196; box-shadow: 0 4px 0 #4b586a; }
.rank-bronze { background: #c96535; box-shadow: 0 4px 0 #8d3f20; }

@media (min-width: 768px) {
  .podium-place-1 { order: 2; min-height: 22rem; }
  .podium-place-2 { order: 1; }
  .podium-place-3 { order: 3; }
}

@keyframes header-mark-float {
  0%, 100% { transform: translate(0, 0) rotate(-8deg); }
  50% { transform: translate(-1rem, -.5rem) rotate(-3deg); }
}

@media (prefers-reduced-motion: reduce) {
  .leaderboard-header::after,
  .podium-card,
  .ranking-row {
    animation: none;
    opacity: 1;
  }

  .leaderboard-tab-indicator,
  .leaderboard-tab {
    transition: none !important;
  }

  .leaderboard-forward-enter-active,
  .leaderboard-forward-leave-active,
  .leaderboard-backward-enter-active,
  .leaderboard-backward-leave-active {
    transition: none !important;
  }

  .leaderboard-forward-enter-from,
  .leaderboard-forward-leave-to,
  .leaderboard-backward-enter-from,
  .leaderboard-backward-leave-to {
    opacity: 1 !important;
    transform: none !important;
  }

  .podium-card:hover {
    transform: none;
  }
}
</style>
