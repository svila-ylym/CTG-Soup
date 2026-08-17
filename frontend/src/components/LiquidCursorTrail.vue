<template>
  <div ref="trailRoot" class="liquid-cursor-trail" aria-hidden="true">
    <span v-for="index in TRAIL_LENGTH" :key="index" class="liquid-cursor-dot"></span>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

const TRAIL_LENGTH = 12
const IDLE_TIMEOUT = 800
const trailRoot = ref<HTMLElement | null>(null)
const positions = Array.from({ length: TRAIL_LENGTH }, () => ({ x: 0, y: 0 }))
const target = { x: 0, y: 0 }
let dots: HTMLElement[] = []
let animationFrame = 0
let lastPointerMove = 0
let sleeping = true
let enabled = false

function resetPositions(x: number, y: number) {
  for (const position of positions) {
    position.x = x
    position.y = y
  }
}

function renderTrail(timestamp: number) {
  const velocity = Math.hypot(target.x - positions[0].x, target.y - positions[0].y)
  positions.forEach((position, index) => {
    const leader = index === 0 ? target : positions[index - 1]
    const easing = Math.max(0.08, 0.25 - index * 0.016)
    position.x += (leader.x - position.x) * easing
    position.y += (leader.y - position.y) * easing
    const leadPulse = index === 0 ? Math.min(0.1, velocity / 240) : 0
    const scale = 1 - index * 0.055 + leadPulse
    const dot = dots[index]
    if (dot) {
      dot.style.transform = `translate3d(${position.x}px, ${position.y}px, 0) translate(-50%, -50%) scale(${scale})`
    }
  })

  if (timestamp - lastPointerMove > IDLE_TIMEOUT) {
    trailRoot.value?.classList.remove('is-visible')
    sleeping = true
    animationFrame = 0
    return
  }
  animationFrame = requestAnimationFrame(renderTrail)
}

function handlePointerMove(event: PointerEvent) {
  if (!enabled || (event.pointerType && event.pointerType !== 'mouse')) return
  target.x = event.clientX
  target.y = event.clientY
  lastPointerMove = performance.now()
  if (sleeping) {
    resetPositions(target.x, target.y)
    sleeping = false
  }
  trailRoot.value?.classList.add('is-visible')
  if (!animationFrame) animationFrame = requestAnimationFrame(renderTrail)
}

function handlePointerLeave() {
  trailRoot.value?.classList.remove('is-visible')
  sleeping = true
  if (animationFrame) cancelAnimationFrame(animationFrame)
  animationFrame = 0
}

function handleVisibilityChange() {
  if (document.visibilityState === 'hidden') handlePointerLeave()
}

function setEnabled(value: boolean) {
  if (enabled === value) return
  enabled = value
  if (enabled) {
    window.addEventListener('pointermove', handlePointerMove, { passive: true })
    document.documentElement.addEventListener('mouseleave', handlePointerLeave)
    document.addEventListener('visibilitychange', handleVisibilityChange)
  } else {
    window.removeEventListener('pointermove', handlePointerMove)
    document.documentElement.removeEventListener('mouseleave', handlePointerLeave)
    document.removeEventListener('visibilitychange', handleVisibilityChange)
    handlePointerLeave()
  }
}

let pointerQuery: MediaQueryList | null = null
let motionQuery: MediaQueryList | null = null
function syncAvailability() {
  setEnabled(Boolean(pointerQuery?.matches && !motionQuery?.matches))
}

onMounted(() => {
  dots = Array.from(trailRoot.value?.querySelectorAll<HTMLElement>('.liquid-cursor-dot') ?? [])
  pointerQuery = window.matchMedia('(hover: hover) and (pointer: fine)')
  motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  pointerQuery.addEventListener('change', syncAvailability)
  motionQuery.addEventListener('change', syncAvailability)
  syncAvailability()
})

onBeforeUnmount(() => {
  setEnabled(false)
  pointerQuery?.removeEventListener('change', syncAvailability)
  motionQuery?.removeEventListener('change', syncAvailability)
})
</script>
