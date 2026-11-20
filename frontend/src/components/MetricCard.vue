<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
import { formatNumber } from '../utils/format'

const props = defineProps({
  card: { type: Object, required: true },
  index: { type: Number, default: 0 },
})

const iconName = computed(() => {
  const key = `${props.card.key || ''} ${props.card.label || ''}`.toLowerCase()
  if (/revenue|income|收入|费用|金额/.test(key)) return 'revenue'
  if (/drug|药品/.test(key)) return 'drugs'
  if (/consum|耗材/.test(key)) return 'consumables'
  if (/bed|inpatient|住院|床位/.test(key)) return 'inpatient'
  if (/patient|visit|门诊|患者|人次/.test(key)) return 'outpatient'
  if (/satisf|满意|service|服务/.test(key)) return 'service'
  if (/efficien|resource|效率|资源|平均/.test(key)) return 'resources'
  return 'dashboard'
})

const tone = computed(() => ['blue', 'teal', 'orange', 'purple'][props.index % 4])
</script>

<template>
  <article class="metric-card card" :class="`tone-${tone}`">
    <div class="metric-topline">
      <span class="metric-label">{{ card.label }}</span>
      <span class="metric-icon"><AppIcon :name="iconName" :size="20" /></span>
    </div>
    <div class="metric-content">
      <strong class="metric-value">{{ formatNumber(card.value, card.format) }}</strong>
      <span v-if="card.unit" class="metric-unit">{{ card.unit }}</span>
    </div>
    <div class="metric-footnote">
      <span class="metric-indicator" />当前筛选范围统计
    </div>
  </article>
</template>

<style scoped>
.metric-card {
  position: relative;
  min-height: 147px;
  padding: 19px 20px 16px;
  overflow: hidden;
  transition: transform 180ms ease, box-shadow 180ms ease;
}

.metric-card::after {
  position: absolute;
  inset: 0 auto 0 0;
  width: 3px;
  content: '';
  background: transparent;
}

.metric-card:hover {
  box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
}

.metric-topline,
.metric-content {
  display: flex;
  align-items: center;
}

.metric-topline {
  justify-content: space-between;
  gap: 10px;
}

.metric-label {
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric-icon {
  display: grid;
  width: 35px;
  height: 35px;
  place-items: center;
  color: var(--primary);
  background: var(--primary-soft);
  border-radius: 9px;
}

.metric-content {
  align-items: baseline;
  gap: 6px;
  margin-top: 8px;
}

.metric-value {
  color: #226fd9;
  font-size: clamp(24px, 2.1vw, 30px);
  font-weight: 650;
  line-height: 1.25;
  letter-spacing: -0.7px;
}

.metric-unit {
  color: var(--text-secondary);
  font-size: 12px;
}

.metric-footnote {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 12px;
  color: var(--text-muted);
  font-size: 10px;
}

.metric-indicator {
  width: 4px;
  height: 4px;
  background: #a7bad0;
  border-radius: 50%;
}

.tone-teal .metric-icon {
  color: #159780;
  background: #ebf8f5;
}

.tone-orange .metric-icon {
  color: #d48a22;
  background: #fff6e9;
}

.tone-purple .metric-icon {
  color: #7864cc;
  background: #f2effc;
}
</style>
