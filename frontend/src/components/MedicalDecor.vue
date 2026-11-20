<script setup>
defineProps({
  variant: { type: String, default: 'sidebar' },
})
</script>

<template>
  <!-- 轻量医疗主题装饰：胶囊、十字与心电图，仅作点缀，不承载信息 -->
  <svg
    v-if="variant === 'sidebar'"
    class="decor decor-sidebar"
    viewBox="0 0 200 96"
    aria-hidden="true"
    focusable="false"
  >
    <path d="M6 78h34l7-16 8 26 7-34 8 24h28" fill="none" stroke="#3d6388" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
    <g transform="translate(112 16) rotate(-22)">
      <rect width="62" height="24" rx="12" fill="#1c3c58" stroke="#3a6086" />
      <path d="M31 0v24" stroke="#3a6086" />
      <path d="M12 1h19v22H12a11 11 0 0 1 0-22z" fill="#2a5478" />
    </g>
    <g transform="translate(150 44) rotate(14)">
      <rect width="26" height="38" rx="13" fill="#1c3c58" stroke="#3a6086" />
      <path d="M0 19h26" stroke="#3a6086" />
      <circle cx="9" cy="11" r="1.7" fill="#7fa6c8" />
      <circle cx="17" cy="11" r="1.7" fill="#7fa6c8" />
      <path d="M9.5 15.5q3.5 2.6 7 0" fill="none" stroke="#7fa6c8" stroke-width="1.5" stroke-linecap="round" />
    </g>
    <g transform="translate(96 56)" fill="none" stroke="#3a6086" stroke-width="2" stroke-linecap="round">
      <path d="M9 0v18M0 9h18" />
    </g>
  </svg>

  <svg
    v-else-if="variant === 'header'"
    class="decor decor-header"
    viewBox="0 0 150 44"
    aria-hidden="true"
    focusable="false"
  >
    <path d="M0 33h26l6-13 7 24 6-31 7 20h22" fill="none" stroke="#c9dcf2" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
    <g transform="translate(86 8) rotate(-20)">
      <rect width="44" height="17" rx="8.5" fill="#e8f2ff" stroke="#c9dcf2" />
      <path d="M22 0v17" stroke="#c9dcf2" />
      <path d="M9 1h13v15H9a7.5 7.5 0 0 1 0-15z" fill="#d6e8fd" />
    </g>
    <g transform="translate(124 18) rotate(10)">
      <rect width="18" height="26" rx="9" fill="#eef6ff" stroke="#c9dcf2" />
      <path d="M0 13h18" stroke="#c9dcf2" />
      <circle cx="6" cy="8" r="1.3" fill="#9dbbdd" />
      <circle cx="12" cy="8" r="1.3" fill="#9dbbdd" />
      <path d="M6.5 11q2.5 2 5 0" fill="none" stroke="#9dbbdd" stroke-width="1.2" stroke-linecap="round" />
    </g>
    <g transform="translate(60 16)" fill="none" stroke="#cfe0f6" stroke-width="2.2" stroke-linecap="round">
      <path d="M7 0v14M0 7h14" />
    </g>
  </svg>

  <svg
    v-else
    class="decor decor-brand"
    viewBox="0 0 320 220"
    aria-hidden="true"
    focusable="false"
  >
    <path d="M0 168h58l12-28 13 46 12-58 13 40h48" fill="none" stroke="rgba(255,255,255,.28)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />
    <g transform="translate(196 24) rotate(-24)">
      <rect width="102" height="40" rx="20" fill="rgba(255,255,255,.10)" stroke="rgba(255,255,255,.34)" />
      <path d="M51 0v40" stroke="rgba(255,255,255,.34)" />
      <path d="M20 1h31v38H20a19 19 0 0 1 0-38z" fill="rgba(255,255,255,.18)" />
    </g>
    <g transform="translate(236 96) rotate(12)">
      <rect width="46" height="66" rx="23" fill="rgba(255,255,255,.10)" stroke="rgba(255,255,255,.34)" />
      <path d="M0 33h46" stroke="rgba(255,255,255,.34)" />
      <circle cx="16" cy="20" r="2.6" fill="rgba(255,255,255,.6)" />
      <circle cx="30" cy="20" r="2.6" fill="rgba(255,255,255,.6)" />
      <path d="M17 27q6 4.5 12 0" fill="none" stroke="rgba(255,255,255,.6)" stroke-width="2" stroke-linecap="round" />
    </g>
    <g transform="translate(150 150)" fill="none" stroke="rgba(255,255,255,.26)" stroke-width="3" stroke-linecap="round">
      <path d="M12 0v24M0 12h24" />
    </g>
  </svg>
</template>

<style scoped>
.decor {
  display: block;
  pointer-events: none;
}

.decor-sidebar {
  width: 100%;
  max-width: 190px;
  height: auto;
  opacity: 0.58;
}

.decor-header {
  width: 150px;
  height: auto;
  opacity: 0.9;
}

.decor-brand {
  position: absolute;
  top: 66px;
  right: -6px;
  width: 246px;
  height: auto;
  opacity: 0.82;
}
</style>
