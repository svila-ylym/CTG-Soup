<template>
  <main
    class="home-page min-h-screen overflow-hidden text-slate-900 dark:bg-black dark:text-white"
    :class="seasonClass"
  >
    <section
      class="home-banner relative isolate overflow-hidden border-b border-sky-100 dark:border-slate-800"
      :class="[`scene-${effectivePeriod}`, `banner-season-${effectiveSeason}`]"
      data-testid="home-banner"
      :style="{ height: bannerHeightPx + 'px' }"
    >
      <!-- Background image layer -->
      <div class="banner-bg-image absolute inset-0"></div>
      
      <!-- Gradient overlay for better text readability -->
      <div class="banner-gradient-overlay absolute inset-0"></div>
      
      <!-- SVG overlay for details and animations -->
      <svg class="banner-svg-overlay absolute inset-0 h-full w-full" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <defs>
          <!-- Gradients for various elements -->
          <radialGradient id="sun-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="#fff9e6" stop-opacity="0.9" />
            <stop offset="50%" stop-color="#ffe066" stop-opacity="0.6" />
            <stop offset="100%" stop-color="#ffd700" stop-opacity="0" />
          </radialGradient>
          
          <radialGradient id="moon-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="#f0f0f0" stop-opacity="0.95" />
            <stop offset="70%" stop-color="#d0d0d0" stop-opacity="0.7" />
            <stop offset="100%" stop-color="#b0b0b0" stop-opacity="0" />
          </radialGradient>
          
          <linearGradient id="mountain-gradient-far" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#6B8E9F" />
            <stop offset="100%" stop-color="#4A6B7C" />
          </linearGradient>
          
          <linearGradient id="mountain-gradient-mid" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#4A7C59" />
            <stop offset="100%" stop-color="#2F5D42" />
          </linearGradient>
          
          <linearGradient id="water-gradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#5DA9C7" stop-opacity="0.6" />
            <stop offset="100%" stop-color="#3A7C99" stop-opacity="0.8" />
          </linearGradient>
          
          <linearGradient id="hill-gradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#3D6B3D" />
            <stop offset="100%" stop-color="#2A4A2A" />
          </linearGradient>
          
          <filter id="cloud-blur">
            <feGaussianBlur in="SourceGraphic" stdDeviation="2" />
          </filter>
          
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        
        <!-- Stars (night only) - drawn first so everything else is on top -->
        <g class="stars-group">
          <circle v-for="star in stars" :key="star.id" 
                  :cx="star.x" :cy="star.y" :r="star.size" 
                  fill="white" :opacity="star.opacity"
                  class="star-twinkle" 
                  :style="{ animationDelay: star.delay + 's' }" />
        </g>
        
        <!-- Sun (visible during day) -->
        <g class="sun-group">
          <circle cx="1400" cy="150" r="140" fill="url(#sun-glow)" opacity="0.3" />
          <circle cx="1400" cy="150" r="60" fill="#FFD700" />
          <circle cx="1400" cy="150" r="80" fill="none" stroke="#FFE55C" stroke-width="2" opacity="0.4" />
        </g>
        
        <!-- Moon (visible at night) -->
        <g class="moon-group">
          <circle cx="300" cy="150" r="100" fill="url(#moon-glow)" opacity="0.2" />
          <circle cx="300" cy="150" r="40" fill="#E8E8E8" />
          <ellipse cx="315" cy="145" rx="35" ry="38" fill="#D0D0D0" opacity="0.3" />
          <circle cx="295" cy="140" r="6" fill="#C0C0C0" opacity="0.4" />
          <circle cx="310" cy="155" r="4" fill="#C0C0C0" opacity="0.3" />
        </g>
        
        <!-- Distant mountains -->
        <g class="mountains-distant" opacity="0.35">
          <path d="M0,500 L200,380 L300,420 L450,340 L600,400 L750,360 L900,390 L1100,350 L1250,400 L1400,370 L1600,410 L1600,900 L0,900 Z" 
                fill="url(#mountain-gradient-far)" />
        </g>
        
        <!-- Mid mountains with more detail -->
        <g class="mountains-mid" opacity="0.55">
          <path d="M0,580 L150,480 L250,520 L350,460 L500,510 L650,470 L800,500 L950,460 L1100,490 L1250,470 L1400,510 L1600,530 L1600,900 L0,900 Z" 
                fill="url(#mountain-gradient-mid)" />
          <!-- Mountain shadows for depth -->
          <path d="M200,480 L250,520 L250,900 L200,900 Z" fill="#000" opacity="0.15" />
          <path d="M650,470 L700,490 L700,900 L650,900 Z" fill="#000" opacity="0.15" />
          <path d="M1100,490 L1150,510 L1150,900 L1100,900 Z" fill="#000" opacity="0.15" />
        </g>
        
        <!-- Summer snow caps on mountains -->
        <g class="summer-snow-caps">
          <ellipse cx="450" cy="340" rx="40" ry="15" fill="white" opacity="0.9" />
          <ellipse cx="750" cy="360" rx="35" ry="12" fill="white" opacity="0.9" />
          <ellipse cx="1100" cy="350" rx="45" ry="14" fill="white" opacity="0.9" />
        </g>
        
        <!-- Lake/Water -->
        <g class="water-layer" opacity="0.4">
          <path d="M0,680 Q400,670 800,685 Q1200,695 1600,680 L1600,900 L0,900 Z"
                fill="url(#water-gradient)" />
          <!-- Water shimmer effect -->
          <g opacity="0.5">
            <ellipse cx="300" cy="700" rx="80" ry="5" fill="white" opacity="0.3" class="water-shimmer" />
            <ellipse cx="700" cy="710" rx="90" ry="5" fill="white" opacity="0.3" class="water-shimmer" style="animation-delay: 1.2s" />
            <ellipse cx="1100" cy="705" rx="70" ry="5" fill="white" opacity="0.3" class="water-shimmer" style="animation-delay: 2.4s" />
            <ellipse cx="1400" cy="695" rx="75" ry="5" fill="white" opacity="0.3" class="water-shimmer" style="animation-delay: 1.8s" />
          </g>
          <!-- Ripples -->
          <g opacity="0.3">
            <circle cx="500" cy="720" r="20" fill="none" stroke="white" stroke-width="1" class="water-ripple" />
            <circle cx="1200" cy="715" r="25" fill="none" stroke="white" stroke-width="1" class="water-ripple" style="animation-delay: 1s" />
          </g>
        </g>
        
        <!-- Foreground hills -->
        <g class="foreground-hills" opacity="0.75">
          <path d="M0,730 Q150,710 300,725 Q450,740 600,730 Q750,720 900,735 Q1050,745 1200,740 Q1350,730 1500,745 L1600,900 L0,900 Z"
                fill="url(#hill-gradient)" />
          <!-- Hill highlights -->
          <path d="M150,710 Q200,705 250,710 L250,900 L150,900 Z" fill="white" opacity="0.05" />
          <path d="M750,720 Q800,715 850,720 L850,900 L750,900 Z" fill="white" opacity="0.05" />
        </g>
        
        <!-- Trees on hills (Spring/Summer) -->
        <g class="season-trees spring-summer-trees">
          <g transform="translate(100, 755)">
            <ellipse cx="0" cy="0" rx="18" ry="25" fill="#2D5016" opacity="0.7" />
            <rect x="-3" y="0" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(250, 760)">
            <ellipse cx="0" cy="0" rx="20" ry="28" fill="#2D5016" opacity="0.7" />
            <rect x="-3" y="0" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(400, 758)">
            <ellipse cx="0" cy="0" rx="16" ry="22" fill="#2D5016" opacity="0.7" />
            <rect x="-3" y="0" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(600, 762)">
            <ellipse cx="0" cy="0" rx="19" ry="26" fill="#2D5016" opacity="0.7" />
            <rect x="-3" y="0" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(750, 757)">
            <ellipse cx="0" cy="0" rx="17" ry="24" fill="#2D5016" opacity="0.7" />
            <rect x="-3" y="0" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(900, 763)">
            <ellipse cx="0" cy="0" rx="21" ry="29" fill="#2D5016" opacity="0.7" />
            <rect x="-3" y="0" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(1100, 759)">
            <ellipse cx="0" cy="0" rx="18" ry="25" fill="#2D5016" opacity="0.7" />
            <rect x="-3" y="0" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(1300, 761)">
            <ellipse cx="0" cy="0" rx="16" ry="23" fill="#2D5016" opacity="0.7" />
            <rect x="-3" y="0" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(1500, 756)">
            <ellipse cx="0" cy="0" rx="20" ry="27" fill="#2D5016" opacity="0.7" />
            <rect x="-3" y="0" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
        </g>
        
        <!-- Pine trees (Winter) -->
        <g class="season-trees winter-trees">
          <g transform="translate(120, 765)">
            <polygon points="0,-35 -15,-10 15,-10" fill="#1B4332" opacity="0.8" />
            <polygon points="0,-25 -12,0 12,0" fill="#1B4332" opacity="0.8" />
            <rect x="-2" y="0" width="4" height="20" fill="#3E2723" opacity="0.8" />
            <ellipse cx="0" cy="-35" rx="8" ry="3" fill="white" opacity="0.9" />
          </g>
          <g transform="translate(300, 768)">
            <polygon points="0,-40 -16,-12 16,-12" fill="#1B4332" opacity="0.8" />
            <polygon points="0,-28 -13,0 13,0" fill="#1B4332" opacity="0.8" />
            <rect x="-2" y="0" width="4" height="20" fill="#3E2723" opacity="0.8" />
            <ellipse cx="0" cy="-40" rx="8" ry="3" fill="white" opacity="0.9" />
          </g>
          <g transform="translate(500, 763)">
            <polygon points="0,-38 -14,-11 14,-11" fill="#1B4332" opacity="0.8" />
            <polygon points="0,-26 -11,0 11,0" fill="#1B4332" opacity="0.8" />
            <rect x="-2" y="0" width="4" height="20" fill="#3E2723" opacity="0.8" />
            <ellipse cx="0" cy="-38" rx="8" ry="3" fill="white" opacity="0.9" />
          </g>
          <g transform="translate(700, 770)">
            <polygon points="0,-42 -17,-13 17,-13" fill="#1B4332" opacity="0.8" />
            <polygon points="0,-30 -14,0 14,0" fill="#1B4332" opacity="0.8" />
            <rect x="-2" y="0" width="4" height="20" fill="#3E2723" opacity="0.8" />
            <ellipse cx="0" cy="-42" rx="8" ry="3" fill="white" opacity="0.9" />
          </g>
          <g transform="translate(900, 766)">
            <polygon points="0,-36 -15,-10 15,-10" fill="#1B4332" opacity="0.8" />
            <polygon points="0,-24 -12,0 12,0" fill="#1B4332" opacity="0.8" />
            <rect x="-2" y="0" width="4" height="20" fill="#3E2723" opacity="0.8" />
            <ellipse cx="0" cy="-36" rx="8" ry="3" fill="white" opacity="0.9" />
          </g>
          <g transform="translate(1100, 764)">
            <polygon points="0,-39 -16,-12 16,-12" fill="#1B4332" opacity="0.8" />
            <polygon points="0,-27 -13,0 13,0" fill="#1B4332" opacity="0.8" />
            <rect x="-2" y="0" width="4" height="20" fill="#3E2723" opacity="0.8" />
            <ellipse cx="0" cy="-39" rx="8" ry="3" fill="white" opacity="0.9" />
          </g>
          <g transform="translate(1350, 769)">
            <polygon points="0,-37 -14,-11 14,-11" fill="#1B4332" opacity="0.8" />
            <polygon points="0,-25 -11,0 11,0" fill="#1B4332" opacity="0.8" />
            <rect x="-2" y="0" width="4" height="20" fill="#3E2723" opacity="0.8" />
            <ellipse cx="0" cy="-37" rx="8" ry="3" fill="white" opacity="0.9" />
          </g>
          <g transform="translate(1520, 762)">
            <polygon points="0,-41 -17,-13 17,-13" fill="#1B4332" opacity="0.8" />
            <polygon points="0,-29 -14,0 14,0" fill="#1B4332" opacity="0.8" />
            <rect x="-2" y="0" width="4" height="20" fill="#3E2723" opacity="0.8" />
            <ellipse cx="0" cy="-41" rx="8" ry="3" fill="white" opacity="0.9" />
          </g>
        </g>
        
        <!-- Autumn trees with colorful foliage -->
        <g class="season-trees autumn-trees">
          <g transform="translate(80, 758)">
            <circle cx="0" cy="-15" r="22" fill="#DC2626" opacity="0.7" />
            <circle cx="8" cy="-18" r="15" fill="#F97316" opacity="0.65" />
            <rect x="-3" y="-5" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(190, 763)">
            <circle cx="0" cy="-15" r="20" fill="#F97316" opacity="0.7" />
            <circle cx="-8" cy="-18" r="14" fill="#EAB308" opacity="0.65" />
            <rect x="-3" y="-5" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(300, 760)">
            <circle cx="0" cy="-15" r="24" fill="#EAB308" opacity="0.7" />
            <circle cx="10" cy="-18" r="16" fill="#DC2626" opacity="0.65" />
            <rect x="-3" y="-5" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(420, 765)">
            <circle cx="0" cy="-15" r="21" fill="#B91C1C" opacity="0.7" />
            <circle cx="-9" cy="-18" r="13" fill="#F97316" opacity="0.65" />
            <rect x="-3" y="-5" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(540, 762)">
            <circle cx="0" cy="-15" r="23" fill="#F97316" opacity="0.7" />
            <circle cx="8" cy="-18" r="15" fill="#EAB308" opacity="0.65" />
            <rect x="-3" y="-5" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(680, 767)">
            <circle cx="0" cy="-15" r="22" fill="#DC2626" opacity="0.7" />
            <circle cx="-7" cy="-18" r="14" fill="#B45309" opacity="0.65" />
            <rect x="-3" y="-5" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(800, 764)">
            <circle cx="0" cy="-15" r="20" fill="#EAB308" opacity="0.7" />
            <circle cx="9" cy="-18" r="13" fill="#F97316" opacity="0.65" />
            <rect x="-3" y="-5" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(930, 766)">
            <circle cx="0" cy="-15" r="24" fill="#DC2626" opacity="0.7" />
            <circle cx="-8" cy="-18" r="16" fill="#EAB308" opacity="0.65" />
            <rect x="-3" y="-5" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(1060, 761)">
            <circle cx="0" cy="-15" r="21" fill="#F97316" opacity="0.7" />
            <circle cx="7" cy="-18" r="14" fill="#DC2626" opacity="0.65" />
            <rect x="-3" y="-5" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(1200, 768)">
            <circle cx="0" cy="-15" r="23" fill="#B91C1C" opacity="0.7" />
            <circle cx="-9" cy="-18" r="15" fill="#F97316" opacity="0.65" />
            <rect x="-3" y="-5" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(1340, 763)">
            <circle cx="0" cy="-15" r="20" fill="#EAB308" opacity="0.7" />
            <circle cx="8" cy="-18" r="13" fill="#B45309" opacity="0.65" />
            <rect x="-3" y="-5" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
          <g transform="translate(1470, 765)">
            <circle cx="0" cy="-15" r="22" fill="#DC2626" opacity="0.7" />
            <circle cx="-7" cy="-18" r="14" fill="#EAB308" opacity="0.65" />
            <rect x="-3" y="-5" width="6" height="25" fill="#4A3520" opacity="0.8" />
          </g>
        </g>
        
        <!-- Spring flowers on ground -->
        <g class="spring-ground-flowers">
          <g transform="translate(100, 810)">
            <circle cx="0" cy="0" r="4" fill="#FF69B4" opacity="0.8" />
            <line x1="0" y1="0" x2="0" y2="15" stroke="#3D8B3D" stroke-width="1.5" opacity="0.6" />
          </g>
          <g transform="translate(200, 805)">
            <circle cx="0" cy="0" r="4" fill="#FFB6C1" opacity="0.8" />
            <line x1="0" y1="0" x2="0" y2="15" stroke="#3D8B3D" stroke-width="1.5" opacity="0.6" />
          </g>
          <g transform="translate(300, 815)">
            <circle cx="0" cy="0" r="4" fill="#FFA07A" opacity="0.8" />
            <line x1="0" y1="0" x2="0" y2="15" stroke="#3D8B3D" stroke-width="1.5" opacity="0.6" />
          </g>
          <g transform="translate(450, 808)">
            <circle cx="0" cy="0" r="4" fill="#FFD700" opacity="0.8" />
            <line x1="0" y1="0" x2="0" y2="15" stroke="#3D8B3D" stroke-width="1.5" opacity="0.6" />
          </g>
          <g transform="translate(600, 812)">
            <circle cx="0" cy="0" r="4" fill="#FF69B4" opacity="0.8" />
            <line x1="0" y1="0" x2="0" y2="15" stroke="#3D8B3D" stroke-width="1.5" opacity="0.6" />
          </g>
          <g transform="translate(750, 807)">
            <circle cx="0" cy="0" r="4" fill="#FFB6C1" opacity="0.8" />
            <line x1="0" y1="0" x2="0" y2="15" stroke="#3D8B3D" stroke-width="1.5" opacity="0.6" />
          </g>
          <g transform="translate(900, 813)">
            <circle cx="0" cy="0" r="4" fill="#FFA07A" opacity="0.8" />
            <line x1="0" y1="0" x2="0" y2="15" stroke="#3D8B3D" stroke-width="1.5" opacity="0.6" />
          </g>
          <g transform="translate(1050, 809)">
            <circle cx="0" cy="0" r="4" fill="#FFD700" opacity="0.8" />
            <line x1="0" y1="0" x2="0" y2="15" stroke="#3D8B3D" stroke-width="1.5" opacity="0.6" />
          </g>
          <g transform="translate(1200, 814)">
            <circle cx="0" cy="0" r="4" fill="#FF69B4" opacity="0.8" />
            <line x1="0" y1="0" x2="0" y2="15" stroke="#3D8B3D" stroke-width="1.5" opacity="0.6" />
          </g>
          <g transform="translate(1350, 806)">
            <circle cx="0" cy="0" r="4" fill="#FFB6C1" opacity="0.8" />
            <line x1="0" y1="0" x2="0" y2="15" stroke="#3D8B3D" stroke-width="1.5" opacity="0.6" />
          </g>
          <g transform="translate(1500, 811)">
            <circle cx="0" cy="0" r="4" fill="#FFA07A" opacity="0.8" />
            <line x1="0" y1="0" x2="0" y2="15" stroke="#3D8B3D" stroke-width="1.5" opacity="0.6" />
          </g>
        </g>
        
        <!-- Village/houses (optional detail) -->
        <g class="village-houses" opacity="0.5">
          <g transform="translate(300, 720)">
            <rect x="0" y="0" width="30" height="25" fill="#8B6F47" />
            <polygon points="15,0 0,0 -5,-15 35,-15 30,0" fill="#6B4423" />
            <rect x="8" y="10" width="8" height="10" fill="#3E2723" />
            <rect x="18" y="8" width="6" height="6" fill="#FFD700" opacity="0.6" />
          </g>
          <g transform="translate(900, 730)">
            <rect x="0" y="0" width="25" height="20" fill="#8B6F47" />
            <polygon points="12.5,0 0,0 -4,-12 29,-12 25,0" fill="#6B4423" />
            <rect x="10" y="8" width="5" height="5" fill="#FFD700" opacity="0.6" />
          </g>
        </g>
        
        <!-- Clouds -->
        <g class="clouds-layer">
          <g class="cloud cloud-1" filter="url(#cloud-blur)">
            <ellipse cx="200" cy="150" rx="80" ry="30" fill="white" opacity="0.7" />
            <ellipse cx="180" cy="140" rx="50" ry="25" fill="white" opacity="0.7" />
            <ellipse cx="220" cy="145" rx="60" ry="28" fill="white" opacity="0.7" />
          </g>
          <g class="cloud cloud-2" filter="url(#cloud-blur)">
            <ellipse cx="800" cy="180" rx="90" ry="35" fill="white" opacity="0.7" />
            <ellipse cx="770" cy="170" rx="60" ry="30" fill="white" opacity="0.7" />
            <ellipse cx="830" cy="175" rx="70" ry="32" fill="white" opacity="0.7" />
          </g>
          <g class="cloud cloud-3" filter="url(#cloud-blur)">
            <ellipse cx="1300" cy="200" rx="100" ry="40" fill="white" opacity="0.6" />
            <ellipse cx="1270" cy="190" rx="70" ry="35" fill="white" opacity="0.6" />
            <ellipse cx="1330" cy="195" rx="80" ry="38" fill="white" opacity="0.6" />
          </g>
        </g>
        
        <!-- Birds -->
        <g class="birds-layer" stroke="currentColor" stroke-width="2" fill="none" opacity="0.4">
          <path class="bird bird-1" d="M0,0 Q10,-5 20,0" />
          <path class="bird bird-2" d="M0,0 Q8,-4 16,0" />
          <path class="bird bird-3" d="M0,0 Q12,-6 24,0" />
        </g>
      </svg>
      
      <!-- Particle effects overlay -->
      <div class="particles-overlay absolute inset-0 pointer-events-none">
        <!-- Spring petals -->
        <div class="spring-petals season-spring">
          <div v-for="i in 15" :key="`petal-${i}`" class="petal" :style="getParticleStyle(i, 'petal')"></div>
        </div>
        
        <!-- Summer fireflies -->
        <div class="summer-fireflies season-summer">
          <div v-for="i in 12" :key="`firefly-${i}`" class="firefly" :style="getParticleStyle(i, 'firefly')"></div>
        </div>
        
        <!-- Autumn leaves -->
        <div class="autumn-falling-leaves season-autumn">
          <div v-for="i in 20" :key="`leaf-${i}`" class="falling-leaf" :style="getParticleStyle(i, 'leaf')"></div>
        </div>
        
        <!-- Winter snowflakes -->
        <div class="winter-snowflakes season-winter">
          <div v-for="i in 25" :key="`snow-${i}`" class="snowflake" :style="getParticleStyle(i, 'snow')"></div>
        </div>
      </div>
      
      <!-- Atmospheric lighting effects -->
      <div class="atmospheric-effects absolute inset-0 pointer-events-none mix-blend-overlay"></div>
      
      <!-- Content overlay -->
      <div class="relative z-10 mx-auto flex h-full max-w-7xl items-center px-5 sm:px-8 lg:px-10">
        <div class="banner-copy max-w-2xl">
          <p v-if="accountStatus" class="mb-3 w-fit rounded-full border px-3 py-1 text-xs font-bold" :class="accountStatus.className">{{ accountStatus.label }}</p>
          <p class="banner-kicker mb-2 inline-flex items-center gap-2 text-xs font-black uppercase tracking-[.15em] text-white/90 drop-shadow-lg">
            <SparklesIcon class="h-4 w-4" aria-hidden="true" />
            {{ seasonTermLabel }}
          </p>
          <h1 class="banner-title text-4xl font-black leading-none text-white drop-shadow-lg sm:text-5xl lg:text-6xl">汤吧社区</h1>
          <Transition name="copy-swap" mode="out-in">
            <p :key="hitokotoText" class="banner-line mt-3 line-clamp-2 max-w-xl text-sm font-semibold leading-6 text-white/95 drop-shadow-md sm:text-base">{{ hitokotoText }}</p>
          </Transition>
          <div class="mt-5 flex flex-wrap gap-3">
            <router-link to="/soups" class="liquid-primary inline-flex min-h-10 items-center gap-2 px-4 py-2 text-sm font-bold shadow-lg">
              去解一碗汤
              <ArrowRightIcon class="h-4 w-4" aria-hidden="true" />
            </router-link>
            <router-link to="/soups/create" class="banner-secondary glass-button inline-flex min-h-10 items-center gap-2 px-4 py-2 text-sm font-bold text-white shadow-lg">
              发布谜面
              <PencilSquareIcon class="h-4 w-4" aria-hidden="true" />
            </router-link>
          </div>
          <p class="mt-4 text-xs font-semibold text-white/80 drop-shadow">
            <span class="solar-term-badge">{{ currentTermLabel }}</span>
          </p>
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
          <div class="glass-card h-[27rem] max-h-[27rem] p-5">
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
            class="latest-competition glass-card glass-card-interactive group flex h-[27rem] max-h-[27rem] flex-col overflow-hidden"
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

          <div v-else class="glass-card flex h-[27rem] max-h-[27rem] flex-col items-center justify-center p-8 text-center">
            <FlagIcon class="h-10 w-10 text-slate-300" aria-hidden="true" />
            <h3 class="mt-4 text-xl font-bold">暂时没有比赛</h3>
            <p class="mt-2 text-sm text-slate-500">新比赛发布后会优先出现在这里。</p>
          </div>

          <aside aria-labelledby="random-soups-heading">
            <div class="mb-3 flex items-center justify-between gap-3">
              <h3 id="random-soups-heading" class="text-lg font-black">随机推荐 <span class="text-sm font-semibold text-slate-400">· {{ randomSoups.length }} 碗</span></h3>
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
                <h4 class="mt-3 line-clamp-2 break-words text-base font-black" :class="soup.is_hall_of_fame ? 'hall-title' : 'text-slate-900 dark:text-white'">{{ soup.title }}</h4>
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

    <DevMode
      :forced-season="forcedSeason"
      :forced-period="forcedPeriod"
      :current-term="currentTerm"
      :current-season="effectiveSeason"
      :current-period="effectivePeriod"
      :banner-height="bannerHeight"
      @update:forced-season="forcedSeason = $event"
      @update:forced-period="forcedPeriod = $event"
      @update:banner-height="bannerHeight = $event"
      @reload="loadSolarTerms"
    />
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
import { fetchSolarTerms, seasonFromDate, getTermLabel } from '@/utils/solarTerms'
import type { HomeCompetitionSummary, HomeDiscovery, SoupColor, SoupGenre } from '@/types'
import type { Season, SolarTermInfo } from '@/utils/solarTerms'
import DevMode from '@/components/DevMode.vue'

const authStore = useAuthStore()
const HITOKOTO_FALLBACK = '每一条线索都算数'
const discovery = ref<HomeDiscovery | null>(null)
const loading = ref(true)
const refreshing = ref(false)
const error = ref('')
const hitokotoText = ref(HITOKOTO_FALLBACK)

type ScenePeriod = 'sunrise' | 'morning' | 'noon' | 'evening' | 'sunset' | 'night'
const scenePeriod = ref<ScenePeriod>('noon')
const season = ref<Season>('summer')
const currentTerm = ref('')
const currentTermLabel = ref('')
const solarTerms = ref<SolarTermInfo[]>([])

// DEV mode overrides
const forcedSeason = ref<Season | null>(null)
const forcedPeriod = ref<string | null>(null)
const bannerHeight = ref(400)

let sceneClock = 0
let hitokotoTimeout = 0
let hitokotoController: AbortController | null = null

// Generate stars for night sky
const stars = ref(Array.from({ length: 100 }, (_, i) => ({
  id: i,
  x: Math.random() * 1600,
  y: Math.random() * 400,
  size: 0.5 + Math.random() * 2,
  opacity: 0.3 + Math.random() * 0.7,
  delay: Math.random() * 3
})))

const effectiveSeason = computed(() => forcedSeason.value ?? season.value)

const effectivePeriod = computed<string>(() => {
  const v = forcedPeriod.value
  if (v && ['sunrise', 'morning', 'noon', 'evening', 'sunset', 'night'].includes(v)) return v
  return scenePeriod.value
})

const bannerHeightPx = computed(() => bannerHeight.value)

const seasonClass = computed(() => `banner-season-${effectiveSeason.value}`)

const seasonTermLabel = computed(() => {
  const labels: Record<Season, string> = {
    spring: '🌱 春 · 万物复苏',
    summer: '☀️ 夏 · 荷风送爽',
    autumn: '🍂 秋 · 金风玉露',
    winter: '❄️ 冬 · 瑞雪丰年',
  }
  return labels[effectiveSeason.value] || '情境推理社区'
})

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

function getParticleStyle(index: number, type: string) {
  const seed = index * (type === 'petal' ? 123 : type === 'firefly' ? 234 : type === 'leaf' ? 345 : 456)
  const left = (Math.sin(seed) * 10000) % 100
  const delay = (Math.cos(seed * 2) + 1) * 5
  const duration = (type === 'snow' ? 8 : type === 'firefly' ? 10 : 12) + (Math.sin(seed * 3) + 1) * 4
  
  return {
    left: `${Math.abs(left)}%`,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`
  }
}

async function loadSolarTerms() {
  try {
    const data = await fetchSolarTerms()
    if (data?.data?.solar_term) {
      const st = data.data.solar_term
      currentTerm.value = st.current || st.prev || ''
      currentTermLabel.value = currentTerm.value ? getTermLabel(currentTerm.value) : ''
      solarTerms.value = st.all_terms || []
      if (st.all_terms?.length) {
        season.value = seasonFromDate(st.all_terms)
      }
    }
  } catch {
    const month = new Date().getMonth() + 1
    season.value = month >= 3 && month <= 5 ? 'spring'
      : month >= 6 && month <= 8 ? 'summer'
        : month >= 9 && month <= 11 ? 'autumn' : 'winter'
  }
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

onMounted(() => {
  updateScenePeriod()
  sceneClock = window.setInterval(updateScenePeriod, 60_000)
  void loadSolarTerms()
  void loadHitokoto()
  void loadDiscovery()
})

onBeforeUnmount(() => {
  window.clearInterval(sceneClock)
  window.clearTimeout(hitokotoTimeout)
  hitokotoController?.abort()
})
</script>

<style scoped>
/* ==================== BANNER BASE ==================== */
.home-banner {
  position: relative;
  overflow: hidden;
}

/* ==================== BACKGROUND IMAGES ==================== */
.banner-bg-image {
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  transition: opacity 1s ease, filter 1s ease;
}

/* Spring: Cherry blossoms and flower fields */
.banner-season-spring .banner-bg-image {
  background: 
    radial-gradient(circle at 20% 80%, rgba(255, 182, 193, 0.6) 0%, transparent 25%),
    radial-gradient(circle at 40% 85%, rgba(255, 218, 224, 0.5) 0%, transparent 20%),
    radial-gradient(circle at 60% 90%, rgba(255, 192, 203, 0.6) 0%, transparent 22%),
    radial-gradient(circle at 80% 88%, rgba(255, 220, 230, 0.5) 0%, transparent 18%),
    radial-gradient(ellipse at 50% 70%, rgba(144, 238, 144, 0.3) 0%, transparent 40%),
    linear-gradient(180deg, 
      #87CEEB 0%, 
      #B4E7F5 25%,
      #D4F1F9 50%,
      #E8F6E3 75%,
      #C8E6C9 100%
    );
  filter: saturate(1.2) brightness(1.05);
}

/* Summer: Mountains and lakes */
.banner-season-summer .banner-bg-image {
  background:
    radial-gradient(ellipse at 80% 40%, rgba(255, 255, 255, 0.4) 0%, transparent 30%),
    radial-gradient(ellipse at 30% 35%, rgba(100, 149, 237, 0.2) 0%, transparent 35%),
    linear-gradient(180deg,
      rgba(135, 206, 250, 0.3) 0%,
      transparent 40%
    ),
    linear-gradient(180deg,
      #4A90E2 0%,
      #5DA8E8 15%,
      #87CEEB 35%,
      #A8D8EA 55%,
      #B8E6F0 70%,
      #7EC8E3 85%,
      #5BA3C5 100%
    );
  filter: saturate(1.15) brightness(1.1) contrast(1.05);
}

/* Autumn: Maple forest */
.banner-season-autumn .banner-bg-image {
  background:
    radial-gradient(circle at 15% 80%, rgba(220, 38, 38, 0.4) 0%, transparent 20%),
    radial-gradient(circle at 35% 85%, rgba(249, 115, 22, 0.4) 0%, transparent 18%),
    radial-gradient(circle at 55% 82%, rgba(234, 179, 8, 0.4) 0%, transparent 22%),
    radial-gradient(circle at 75% 88%, rgba(217, 70, 70, 0.4) 0%, transparent 19%),
    radial-gradient(circle at 90% 85%, rgba(251, 146, 60, 0.4) 0%, transparent 17%),
    linear-gradient(180deg,
      #8B6914 0%,
      #A67C38 15%,
      #C68642 30%,
      #D4924A 45%,
      #B87333 60%,
      #8B5A2B 75%,
      #6B4423 90%,
      #4A3518 100%
    );
  filter: saturate(1.3) brightness(1) contrast(1.1);
}

/* Winter: Snowy landscape */
.banner-season-winter .banner-bg-image {
  background:
    radial-gradient(circle at 50% 90%, rgba(255, 255, 255, 0.6) 0%, transparent 40%),
    radial-gradient(circle at 20% 85%, rgba(240, 248, 255, 0.5) 0%, transparent 25%),
    radial-gradient(circle at 80% 88%, rgba(230, 244, 252, 0.5) 0%, transparent 28%),
    radial-gradient(ellipse at 50% 40%, rgba(176, 196, 222, 0.3) 0%, transparent 50%),
    linear-gradient(180deg,
      #B0C4DE 0%,
      #C8D8E8 20%,
      #D4E4F0 40%,
      #E0F0FA 60%,
      #F0F8FF 80%,
      #FFFFFF 100%
    );
  filter: saturate(0.8) brightness(1.15) contrast(1.05);
}

/* ==================== GRADIENT OVERLAY ==================== */
.banner-gradient-overlay {
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.1) 0%,
    rgba(0, 0, 0, 0.3) 100%
  );
  mix-blend-mode: multiply;
  transition: background 0.8s ease;
}

.scene-night .banner-gradient-overlay {
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 20, 0.5) 0%,
    rgba(0, 0, 40, 0.7) 100%
  );
}

/* ==================== SVG OVERLAY ==================== */
.banner-svg-overlay {
  pointer-events: none;
  z-index: 2;
}

/* Season-specific trees visibility */
.season-trees {
  display: none;
}

.banner-season-spring .spring-summer-trees {
  display: block;
}

.banner-season-summer .spring-summer-trees {
  display: block;
}

.banner-season-autumn .autumn-trees {
  display: block;
}

.banner-season-winter .winter-trees {
  display: block;
}

/* Spring ground flowers */
.spring-ground-flowers {
  display: none;
}

.banner-season-spring .spring-ground-flowers {
  display: block;
}

/* Sun visibility */
.sun-group {
  opacity: 1;
  transition: opacity 1s ease;
}

.scene-night .sun-group {
  opacity: 0;
}

/* Moon visibility */
.moon-group {
  opacity: 0;
  transition: opacity 1s ease;
}

.scene-night .moon-group {
  opacity: 1;
}

/* Stars */
.stars-group {
  opacity: 0;
  transition: opacity 1.5s ease;
}

.scene-night .stars-group {
  opacity: 1;
}

.star-twinkle {
  animation: star-twinkle 8s ease-in-out infinite;
}

/* Clouds animation */
.cloud {
  animation: cloud-float 60s linear infinite;
}

.cloud-1 {
  animation-duration: 70s;
}

.cloud-2 {
  animation-duration: 85s;
  animation-delay: -20s;
}

.cloud-3 {
  animation-duration: 90s;
  animation-delay: -40s;
}

/* Birds */
.birds-layer {
  color: rgba(0, 0, 0, 0.3);
}

.bird {
  animation: bird-fly 8s ease-in-out infinite;
}

.bird-1 {
  transform: translate(100px, 200px);
  animation-duration: 10s;
}

.bird-2 {
  transform: translate(300px, 180px);
  animation-duration: 12s;
  animation-delay: -3s;
}

.bird-3 {
  transform: translate(500px, 220px);
  animation-duration: 11s;
  animation-delay: -6s;
}

/* ==================== PARTICLES ==================== */
.particles-overlay {
  z-index: 3;
}

.spring-petals, .summer-fireflies, .autumn-falling-leaves, .winter-snowflakes {
  display: none;
}

.banner-season-spring .spring-petals {
  display: block;
}

.banner-season-summer .summer-fireflies {
  display: block;
}

.banner-season-autumn .autumn-falling-leaves {
  display: block;
}

.banner-season-winter .winter-snowflakes {
  display: block;
}

/* Petals */
.petal {
  position: absolute;
  top: -20px;
  width: 10px;
  height: 10px;
  background: radial-gradient(ellipse, #FFB6C1, #FF69B4);
  border-radius: 50% 0 50% 0;
  opacity: 0;
  animation: petal-fall 15s ease-in-out infinite;
}

/* Fireflies */
.firefly {
  position: absolute;
  width: 5px;
  height: 5px;
  background: #FFFF00;
  border-radius: 50%;
  box-shadow: 0 0 10px #FFFF00, 0 0 20px rgba(255, 255, 0, 0.5);
  opacity: 0;
  animation: firefly-glow 4s ease-in-out infinite;
}

/* Falling leaves */
.falling-leaf {
  position: absolute;
  top: -20px;
  width: 15px;
  height: 15px;
  background: linear-gradient(135deg, #D2691E 0%, #8B4513 100%);
  clip-path: polygon(50% 0%, 0% 100%, 100% 100%);
  opacity: 0;
  animation: leaf-fall 14s ease-in-out infinite;
}

/* Snowflakes */
.snowflake {
  position: absolute;
  top: -20px;
  width: 8px;
  height: 8px;
  background: white;
  border-radius: 50%;
  box-shadow: 0 0 5px rgba(255, 255, 255, 0.8);
  opacity: 0;
  animation: snowflake-fall 12s linear infinite;
}

/* ==================== ATMOSPHERIC EFFECTS ==================== */
.atmospheric-effects {
  z-index: 4;
  background: radial-gradient(
    ellipse at 80% 20%,
    rgba(255, 255, 200, 0.1) 0%,
    transparent 50%
  );
  transition: opacity 1s ease;
}

.scene-night .atmospheric-effects {
  background: radial-gradient(
    ellipse at 20% 20%,
    rgba(180, 180, 220, 0.05) 0%,
    transparent 50%
  );
}

/* ==================== TIME OF DAY VARIATIONS ==================== */
/* Sunrise */
.scene-sunrise .banner-bg-image {
  filter: saturate(1.3) brightness(0.9) hue-rotate(-10deg) !important;
}

.scene-sunrise .banner-gradient-overlay {
  background: linear-gradient(
    to bottom,
    rgba(255, 140, 0, 0.2) 0%,
    rgba(255, 69, 0, 0.3) 100%
  );
}

/* Morning */
.scene-morning .banner-bg-image {
  filter: saturate(1.1) brightness(1.1) !important;
}

/* Noon */
.scene-noon .banner-bg-image {
  filter: saturate(1.2) brightness(1.15) contrast(1.05) !important;
}

/* Evening */
.scene-evening .banner-bg-image {
  filter: saturate(1.1) brightness(0.85) hue-rotate(10deg) !important;
}

.scene-evening .banner-gradient-overlay {
  background: linear-gradient(
    to bottom,
    rgba(255, 140, 0, 0.15) 0%,
    rgba(139, 69, 19, 0.3) 100%
  );
}

/* Sunset */
.scene-sunset .banner-bg-image {
  filter: saturate(1.4) brightness(0.7) contrast(1.1) hue-rotate(15deg) !important;
}

.scene-sunset .banner-gradient-overlay {
  background: linear-gradient(
    to bottom,
    rgba(139, 0, 139, 0.3) 0%,
    rgba(255, 69, 0, 0.4) 100%
  );
}

/* Night */
.scene-night .banner-bg-image {
  filter: saturate(0.5) brightness(0.3) contrast(1.1) hue-rotate(-10deg) !important;
}

/* ==================== TEXT STYLING ==================== */
.solar-term-badge {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(10px);
  font-size: 0.75rem;
  font-weight: 600;
}

.banner-secondary {
  border: 1px solid rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(10px);
}

.banner-secondary:hover {
  background: rgba(255, 255, 255, 0.25);
}

.copy-swap-enter-active,
.copy-swap-leave-active {
  transition: opacity 220ms ease, transform 220ms ease;
}

.copy-swap-enter-from {
  opacity: 0;
  transform: translateY(0.35rem);
}

.copy-swap-leave-to {
  opacity: 0;
  transform: translateY(-0.25rem);
}

/* ==================== ANIMATIONS ==================== */
@keyframes cloud-float {
  from {
    transform: translateX(-200px);
  }
  to {
    transform: translateX(calc(100% + 200px));
  }
}

@keyframes bird-fly {
  0%, 100% {
    transform: translateX(0) translateY(0);
  }
  50% {
    transform: translateX(100px) translateY(-20px);
  }
}

@keyframes star-twinkle {
  0%, 100% {
    opacity: 0.3;
    transform: scale(0.8);
  }
  50% {
    opacity: 1;
    transform: scale(1.2);
  }
}

@keyframes petal-fall {
  0% {
    opacity: 0;
    transform: translateY(-20px) rotate(0deg);
  }
  10% {
    opacity: 0.8;
  }
  90% {
    opacity: 0.3;
  }
  100% {
    opacity: 0;
    transform: translateY(calc(100vh + 50px)) rotate(360deg) translateX(100px);
  }
}

@keyframes firefly-glow {
  0%, 100% {
    opacity: 0.2;
    transform: scale(0.8);
  }
  50% {
    opacity: 1;
    transform: scale(1.2);
  }
}

@keyframes leaf-fall {
  0% {
    opacity: 0;
    transform: translateY(-20px) rotate(0deg);
  }
  10% {
    opacity: 0.9;
  }
  90% {
    opacity: 0.4;
  }
  100% {
    opacity: 0;
    transform: translateY(calc(100vh + 50px)) rotate(720deg) translateX(-100px);
  }
}

@keyframes snowflake-fall {
  0% {
    opacity: 0;
    transform: translateY(-20px) rotate(0deg);
  }
  10% {
    opacity: 0.9;
  }
  90% {
    opacity: 0.5;
  }
  100% {
    opacity: 0;
    transform: translateY(calc(100vh + 50px)) rotate(360deg) translateX(50px);
  }
}

@keyframes water-shimmer {
  0%, 100% {
    opacity: 0.2;
    transform: scaleX(1);
  }
  50% {
    opacity: 0.5;
    transform: scaleX(1.2);
  }
}

@keyframes water-ripple {
  0% {
    r: 10;
    opacity: 0.4;
  }
  100% {
    r: 40;
    opacity: 0;
  }
}

.water-shimmer {
  animation: water-shimmer 4s ease-in-out infinite;
}

.water-ripple {
  animation: water-ripple 3s ease-out infinite;
}

/* Summer snow caps visibility */
.summer-snow-caps {
  display: none;
}

.banner-season-summer .summer-snow-caps {
  display: block;
}

/* ==================== RESPONSIVE ==================== */
@media (max-width: 768px) {
  .particles-overlay {
    display: none;
  }
  
  .birds-layer {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
