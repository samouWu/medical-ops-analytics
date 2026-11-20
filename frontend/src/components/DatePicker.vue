<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  mode: { type: String, default: 'date' },
  min: { type: String, default: '' },
  max: { type: String, default: '' },
  placeholder: { type: String, default: '请选择日期' },
})
const emit = defineEmits(['update:modelValue', 'change'])

const root = ref(null)
const open = ref(false)
const viewDate = ref(new Date())
const weekLabels = ['一', '二', '三', '四', '五', '六', '日']

function parseValue(value) {
  if (!value) return null
  const parts = value.split('-').map(Number)
  if (parts.length < 2 || !parts[0] || !parts[1]) return null
  return new Date(parts[0], parts[1]-1, parts[2] || 1)
}

function isoDate(year, month, day) {
  return `${year}-${String(month+1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

function syncView() {
  viewDate.value = parseValue(props.modelValue) || parseValue(props.max) || new Date()
}

watch(() => props.modelValue, syncView, { immediate: true })

const display = computed(() => {
  if (!props.modelValue) return props.placeholder
  const value = props.modelValue
  if (props.mode === 'month') {
    const parts = value.split('-')
    return parts.length >= 2 ? `${parts[0]}年${Number(parts[1])}月` : value
  }
  return value
})

const header = computed(() => `${viewDate.value.getFullYear()}年${viewDate.value.getMonth()+1}月`)
const monthHeader = computed(() => `${viewDate.value.getFullYear()}年`)
const weekdays = computed(() => weekLabels)

const days = computed(() => {
  const year = viewDate.value.getFullYear()
  const month = viewDate.value.getMonth()
  const firstWeekday = (new Date(year, month, 1).getDay()+6) % 7
  const total = new Date(year, month+1, 0).getDate()
  const cells = []
  for (let index = 0; index < firstWeekday; index += 1) cells.push({ key: `empty-${index}`, empty: true })
  for (let day = 1; day <= total; day += 1) {
    const value = isoDate(year, month, day)
    cells.push({
      key: value,
      value,
      label: day,
      disabled: (props.min && value < props.min) || (props.max && value > props.max),
    })
  }
  return cells
})

const months = computed(() => {
  const year = viewDate.value.getFullYear()
  return Array.from({ length: 12 }, (_, index) => {
    const value = `${year}-${String(index+1).padStart(2, '0')}`
    return { key: value, value, label: `${index+1}月`, disabled: (props.min && value < props.min.slice(0, 7)) || (props.max && value > props.max.slice(0, 7)) }
  })
})

function toggle() {
  if (!open.value) syncView()
  open.value = !open.value
}

function shift(step) {
  const next = new Date(viewDate.value)
  if (props.mode === 'month') next.setFullYear(next.getFullYear()+step)
  else next.setMonth(next.getMonth()+step)
  viewDate.value = next
}

function select(value) {
  emit('update:modelValue', value)
  emit('change', value)
  open.value = false
}

function selectMonth(value) {
  if (props.mode === 'month') select(value)
  else {
    viewDate.value = new Date(Number(value.slice(0, 4)), Number(value.slice(5, 7))-1, 1)
  }
}

function selectToday() {
  const today = new Date()
  select(props.mode === 'month' ? `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2, '0')}` : isoDate(today.getFullYear(), today.getMonth(), today.getDate()))
}

function clear() {
  emit('update:modelValue', '')
  emit('change', '')
  open.value = false
}

function onDocumentPointer(event) {
  if (open.value && root.value && !root.value.contains(event.target)) open.value = false
}
function onKeydown(event) {
  if (event.key === 'Escape') open.value = false
}

onMounted(() => {
  document.addEventListener('pointerdown', onDocumentPointer)
  document.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocumentPointer)
  document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div ref="root" class="date-picker" :class="{ open }">
    <button type="button" class="form-control date-trigger" :aria-expanded="open" @click="toggle">
      <AppIcon name="calendar" :size="15" />
      <span :class="{ placeholder: !modelValue }">{{ display }}</span>
      <AppIcon name="chevronDown" :size="13" class="date-chevron" />
    </button>
    <div v-if="open" class="date-popover" @click.stop>
      <div class="date-popover-header">
        <button type="button" class="date-nav" aria-label="上一段" @click="shift(-1)"><AppIcon name="chevronRight" :size="14" class="nav-prev" /></button>
        <strong>{{ mode === 'month' ? monthHeader : header }}</strong>
        <button type="button" class="date-nav" aria-label="下一段" @click="shift(1)"><AppIcon name="chevronRight" :size="14" /></button>
      </div>
      <template v-if="mode === 'date'">
        <div class="date-weekdays"><span v-for="label in weekdays" :key="label">{{ label }}</span></div>
        <div class="date-grid">
          <button
            v-for="cell in days"
            :key="cell.key"
            type="button"
            class="date-cell"
            :class="{ empty: cell.empty, selected: cell.value === modelValue }"
            :disabled="cell.empty || cell.disabled"
            @click="!cell.empty && select(cell.value)"
          >
            {{ cell.empty ? '' : cell.label }}
          </button>
        </div>
      </template>
      <div v-else class="month-grid">
        <button
          v-for="month in months"
          :key="month.key"
          type="button"
          class="month-cell"
          :class="{ selected: month.value === modelValue }"
          :disabled="month.disabled"
          @click="selectMonth(month.value)"
        >
          {{ month.label }}
        </button>
      </div>
      <div class="date-popover-footer">
        <button type="button" @click="clear">清除</button>
        <button type="button" class="today-link" @click="selectToday">今天</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.date-picker { position: relative; width: 100%; color-scheme: light; }
.date-trigger {
  display: flex;
  align-items: center;
  gap: 7px;
  text-align: left;
  cursor: pointer;
}
.date-trigger > span { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.date-trigger .placeholder { color: #a2afbf; }
.date-chevron { color: #8b9aaf; transition: transform 150ms ease; }
.date-picker.open .date-chevron { transform: rotate(180deg); }
.date-popover {
  position: absolute;
  z-index: 120;
  top: calc(100% + 6px);
  left: 0;
  width: 278px;
  padding: 12px;
  color: #1a2230;
  background: #fff;
  border: 1px solid #dfe6ee;
  border-radius: 9px;
  box-shadow: 0 14px 34px rgba(15, 38, 66, 0.16);
}
.date-popover-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.date-popover-header strong { color: #2d465f; font-size: 12px; }
.date-nav { display: grid; width: 25px; height: 25px; place-items: center; padding: 0; color: #6b7f94; background: transparent; border-radius: 5px; }
.date-nav:hover { background: #f2f6fb; color: var(--primary); }
.nav-prev { transform: rotate(180deg); }
.date-weekdays, .date-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
.date-weekdays { margin-bottom: 3px; color: #9aa8b8; font-size: 10px; text-align: center; }
.date-cell, .month-cell { height: 29px; padding: 0; color: #40566f; font-size: 11px; background: transparent; border: 0; border-radius: 5px; cursor: pointer; }
.date-cell:hover:not(:disabled), .month-cell:hover:not(:disabled) { color: var(--primary); background: #eef4fe; }
.date-cell.selected, .month-cell.selected { color: #fff; font-weight: 600; background: var(--primary); }
.date-cell.empty { cursor: default; }
.date-cell:disabled, .month-cell:disabled { color: #c8d1dc; cursor: not-allowed; }
.month-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; padding: 4px 0; }
.month-cell { height: 34px; }
.date-popover-footer { display: flex; justify-content: space-between; margin-top: 8px; padding-top: 7px; border-top: 1px solid #edf1f5; }
.date-popover-footer button { padding: 2px 3px; color: #7e8fa2; font-size: 10px; background: transparent; cursor: pointer; }
.date-popover-footer .today-link { color: var(--primary); }
</style>
