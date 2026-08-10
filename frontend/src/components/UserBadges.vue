<script setup lang="ts">
import { computed } from 'vue'
import LevelBadge from '@/components/LevelBadge.vue'

const props = withDefaults(defineProps<{
  level?: number
  band?: string
  permissionGroups?: string[]
  role?: 'user' | 'admin' | 'root'
  compact?: boolean
}>(), {
  level: 0,
  band: '',
  permissionGroups: () => [],
  role: 'user',
  compact: false,
})

const groupLabel = computed(() => props.permissionGroups.filter(Boolean).join(' / '))
const roleLabel = computed(() => {
  if (props.role === 'root') return '最高管理员'
  if (props.role === 'admin') return '管理员'
  return ''
})
</script>

<template>
  <span class="user-badges" :class="compact ? 'user-badges-compact' : ''">
    <LevelBadge :level="level" :band="band" :compact="compact" />
    <span v-if="groupLabel" class="user-group-badge" :title="`用户组：${groupLabel}`">{{ groupLabel }}</span>
    <span v-if="roleLabel" class="user-role-badge" :class="role === 'root' ? 'user-role-root' : 'user-role-admin'">{{ roleLabel }}</span>
  </span>
</template>

<style scoped>
.user-badges {
  display: inline-flex;
  min-width: 0;
  align-items: center;
  flex-wrap: wrap;
  gap: .35rem;
}

.user-group-badge,
.user-role-badge {
  display: inline-flex;
  min-height: 1.55rem;
  max-width: 14rem;
  align-items: center;
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: .55rem;
  padding: .18rem .52rem;
  box-shadow: 0 2px 0 rgba(15, 23, 42, .12), 0 4px 9px rgba(15, 23, 42, .08);
  font-size: .72rem;
  font-weight: 800;
  line-height: 1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-badges-compact .user-group-badge,
.user-badges-compact .user-role-badge {
  min-height: 1.3rem;
  max-width: 11rem;
  padding: .14rem .4rem;
  font-size: .65rem;
}

.user-group-badge { border-color: #8ab9aa; background: #e3f3ed; color: #25624f; }
.user-role-admin { border-color: #8ca9cf; background: #e5efff; color: #29558a; }
.user-role-root { border-color: #d3a45c; background: #fff0c7; color: #805817; }

:global(.dark) .user-group-badge { border-color: #3e7565; background: #17382f; color: #b9efdc; }
:global(.dark) .user-role-admin { border-color: #496c9e; background: #1c3150; color: #c8dcff; }
:global(.dark) .user-role-root { border-color: #8c6730; background: #4b3618; color: #ffe4a8; }
</style>
