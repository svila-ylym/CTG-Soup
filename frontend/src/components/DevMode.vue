<template>
  <div class="dev-mode" :class="{ 'is-open': open }">
    <button
      class="dev-toggle"
      type="button"
      :title="open ? '关闭 DEV 模式' : '打开 DEV 模式'"
      :aria-label="open ? '关闭 DEV 模式' : '打开 DEV 模式'"
      @click="open = !open"
    >
      <span class="dev-icon">⚙</span>
    </button>

    <Transition name="dev-panel">
      <div v-if="open" class="dev-panel">
        <header class="dev-header">
          <h2 class="dev-title">DEV 模式</h2>
          <button class="dev-close" type="button" aria-label="关闭 DEV 面板" @click="open = false">✕</button>
        </header>

        <div class="dev-body">
          <!-- Season override -->
          <section class="dev-section">
            <h3 class="dev-section-title">季节覆盖</h3>
            <div class="dev-btn-group">
              <button
                v-for="s in seasons"
                :key="s.value"
                class="dev-btn"
                :class="{ active: forcedSeason === s.value }"
                type="button"
                @click="setSeason(s.value)"
              >{{ s.label }}</button>
              <button
                class="dev-btn"
                :class="{ active: forcedSeason === null }"
                type="button"
                @click="setSeason(null)"
              >自动</button>
            </div>
          </section>

          <!-- Scene period override -->
          <section class="dev-section">
            <h3 class="dev-section-title">时段覆盖</h3>
            <div class="dev-btn-group">
              <button
                v-for="p in periods"
                :key="p.value"
                class="dev-btn"
                :class="{ active: forcedPeriod === p.value }"
                type="button"
                @click="setPeriod(p.value)"
              >{{ p.label }}</button>
              <button
                class="dev-btn"
                :class="{ active: forcedPeriod === null }"
                type="button"
                @click="setPeriod(null)"
              >自动</button>
            </div>
          </section>

          <!-- Current status -->
          <section class="dev-section">
            <h3 class="dev-section-title">当前状态</h3>
            <div class="dev-status">
              <div class="dev-status-row">
                <span class="dev-label">节气</span>
                <span class="dev-value">{{ currentTerm || '—' }}</span>
              </div>
              <div class="dev-status-row">
                <span class="dev-label">季节</span>
                <span class="dev-value" :style="{ color: seasonColor }">{{ currentSeasonLabel }}</span>
              </div>
              <div class="dev-status-row">
                <span class="dev-label">时段</span>
                <span class="dev-value">{{ currentPeriodLabel }}</span>
              </div>
              <div class="dev-status-row">
                <span class="dev-label">Banner 高度</span>
                <span class="dev-value">{{ bannerHeight }}px</span>
              </div>
            </div>
          </section>

          <!-- Banner height slider -->
          <section class="dev-section">
            <h3 class="dev-section-title">Banner 高度</h3>
            <input
              :value="localBannerHeight"
              @input="onBannerHeightInput"
              type="range"
              min="200"
              max="600"
              step="10"
              class="dev-slider"
            >
            <div class="dev-slider-labels">
              <span>200px</span>
              <span>{{ localBannerHeight }}px</span>
              <span>600px</span>
            </div>
          </section>

          <!-- Reload data -->
          <section class="dev-section">
            <button class="dev-btn dev-btn-primary" type="button" @click="$emit('reload')">
              重新加载节气数据
            </button>
          </section>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Season } from '@/utils/solarTerms'
import { SEASON_NAMES, SEASON_COLORS } from '@/utils/solarTerms'

const props = defineProps<{
  forcedSeason: Season | null
  forcedPeriod: string | null
  currentTerm: string
  currentSeason: Season
  currentPeriod: string
  bannerHeight: number
}>()

const emit = defineEmits<{
  (e: 'update:forcedSeason', v: Season | null): void
  (e: 'update:forcedPeriod', v: string | null): void
  (e: 'update:bannerHeight', v: number): void
  (e: 'reload'): void
}>()

const open = ref(false)

const localBannerHeight = computed({
  get: () => props.bannerHeight,
  set: (v: number) => emit('update:bannerHeight', v),
})

function onBannerHeightInput(event: Event) {
  const target = event.target as HTMLInputElement
  emit('update:bannerHeight', Number(target.value))
}

const seasons = [
  { value: 'spring' as Season, label: '🌱 春季' },
  { value: 'summer' as Season, label: '☀️ 夏季' },
  { value: 'autumn' as Season, label: '🍂 秋季' },
  { value: 'winter' as Season, label: '❄️ 冬季' },
]

const periods = [
  { value: 'sunrise', label: '🌅 日出' },
  { value: 'morning', label: '🌤 上午' },
  { value: 'noon', label: '☀️ 正午' },
  { value: 'evening', label: '🌆 傍晚' },
  { value: 'sunset', label: '🌇 日落' },
  { value: 'night', label: '🌙 夜晚' },
]

const currentSeasonLabel = computed(() => SEASON_NAMES[props.currentSeason])
const seasonColor = computed(() => SEASON_COLORS[props.currentSeason]?.accent || '#fff')
const currentPeriodLabel = computed(() => {
  const labels: Record<string, string> = {
    sunrise: '日出',
    morning: '上午',
    noon: '正午',
    evening: '傍晚',
    sunset: '日落',
    night: '夜晚',
  }
  return labels[props.currentPeriod] || props.currentPeriod
})

function setSeason(s: Season | null) {
  emit('update:forcedSeason', s)
}

function setPeriod(p: string | null) {
  emit('update:forcedPeriod', p)
}
</script>

<style scoped>
.dev-mode {
  position: fixed;
  z-index: 9999;
  right: 1rem;
  bottom: 1rem;
  font-family: 'Inter', -apple-system, sans-serif;
}

.dev-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.75rem;
  height: 2.75rem;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
  font-size: 1.25rem;
  cursor: pointer;
  backdrop-filter: blur(12px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  transition: transform 0.2s ease;
}

.dev-toggle:hover {
  transform: scale(1.1);
}

.dev-icon {
  display: block;
  animation: dev-spin 4s linear infinite;
}

.dev-panel {
  position: absolute;
  right: 0;
  bottom: calc(100% + 0.75rem);
  width: 20rem;
  max-height: 70vh;
  overflow-y: auto;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 1rem;
  background: rgba(10, 10, 10, 0.92);
  color: #e5e7eb;
  backdrop-filter: blur(24px) saturate(140%);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.5);
}

.dev-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.dev-title {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.dev-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  color: #9ca3af;
  font-size: 0.8rem;
  cursor: pointer;
  transition: background 0.2s;
}

.dev-close:hover {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.dev-body {
  padding: 0.75rem 1.25rem 1.25rem;
}

.dev-section {
  margin-top: 0.75rem;
}

.dev-section:first-child {
  margin-top: 0;
}

.dev-section-title {
  margin: 0 0 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #6b7280;
}

.dev-btn-group {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.dev-btn {
  padding: 0.3rem 0.65rem;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 0.5rem;
  background: rgba(255, 255, 255, 0.05);
  color: #d1d5db;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.dev-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.25);
}

.dev-btn.active {
  background: rgba(56, 189, 248, 0.2);
  border-color: rgba(56, 189, 248, 0.5);
  color: #38bdf8;
}

.dev-btn-primary {
  width: 100%;
  padding: 0.5rem;
  background: rgba(56, 189, 248, 0.15);
  border-color: rgba(56, 189, 248, 0.3);
  color: #38bdf8;
  font-size: 0.8rem;
}

.dev-btn-primary:hover {
  background: rgba(56, 189, 248, 0.25);
}

.dev-status {
  display: grid;
  gap: 0.375rem;
}

.dev-status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.3rem 0.5rem;
  border-radius: 0.375rem;
  background: rgba(255, 255, 255, 0.03);
  font-size: 0.8rem;
}

.dev-label {
  color: #6b7280;
}

.dev-value {
  color: #e5e7eb;
  font-weight: 600;
}

.dev-slider {
  width: 100%;
  height: 4px;
  -webkit-appearance: none;
  appearance: none;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.15);
  outline: none;
}

.dev-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 1rem;
  height: 1rem;
  border-radius: 50%;
  background: #38bdf8;
  cursor: pointer;
  border: 2px solid rgba(0, 0, 0, 0.3);
}

.dev-slider-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 0.25rem;
  font-size: 0.65rem;
  color: #6b7280;
}

@keyframes dev-spin {
  to { transform: rotate(360deg); }
}

.dev-panel-enter-active,
.dev-panel-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.dev-panel-enter-from,
.dev-panel-leave-to {
  opacity: 0;
  transform: translateY(0.5rem) scale(0.96);
}
</style>