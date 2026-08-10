<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  level?: number
  band?: string
  compact?: boolean
}>(), {
  level: 0,
  band: '',
  compact: false,
})

const normalizedLevel = computed(() => Math.max(0, Math.floor(Number(props.level) || 0)))
const resolvedBand = computed(() => {
  if (props.band) return props.band
  const bands = ['black', 'yellow', 'purple', 'green', 'bronze', 'silver', 'cyan', 'blue', 'gold', 'red']
  return bands[Math.min(Math.floor(normalizedLevel.value / 10), bands.length - 1)]
})
</script>

<template>
  <span class="level-badge" :class="[`level-${resolvedBand}`, compact ? 'level-compact' : '']" :title="`等级 ${normalizedLevel}`">
    Lv.{{ normalizedLevel }}
  </span>
</template>

<style scoped>
.level-badge {
  display: inline-flex;
  min-height: 1.55rem;
  flex: none;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: .55rem;
  padding: .18rem .52rem;
  font-size: .72rem;
  font-weight: 800;
  line-height: 1;
  letter-spacing: .01em !important;
  box-shadow: 0 2px 0 rgba(15, 23, 42, .12), 0 4px 9px rgba(15, 23, 42, .08);
}

.level-compact { min-height: 1.3rem; padding: .14rem .4rem; font-size: .65rem; }
.level-black { border-color: #475569; background: #1e293b; color: #f8fafc; }
.level-yellow { border-color: #d6b64f; background: #fff1b8; color: #735515; }
.level-purple { border-color: #aa8bd5; background: #eadcff; color: #5d3a86; }
.level-green { border-color: #78b997; background: #d8f3e3; color: #256245; }
.level-bronze { border-color: #b98565; background: #ecd2c0; color: #71432d; }
.level-silver { border-color: #aab6c3; background: #e6ebf0; color: #455568; }
.level-cyan { border-color: #68bdc5; background: #d6f2f3; color: #24666d; }
.level-blue { border-color: #83aee0; background: #dceaff; color: #285b98; }
.level-gold { border-color: #c99b39; background: #f8e3a5; color: #725314; }
.level-red { border-color: #d88989; background: #f8dada; color: #8e3232; }
</style>
