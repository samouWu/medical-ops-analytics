<script setup>
import { reactive, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'
import { appState, filters } from '../stores/app'

const props = defineProps({
  loading: { type: Boolean, default: false },
  showDepartment: { type: Boolean, default: true },
})
const emit = defineEmits(['apply', 'reset'])

const draft = reactive({ start: filters.start, end: filters.end, dept_code: filters.dept_code })
const validationError = ref('')

watch(() => appState.meta.date_range, (range) => {
  if (!draft.start) draft.start = range.min || ''
  if (!draft.end) draft.end = range.max || ''
}, { deep: true })

watch(filters, () => {
  Object.assign(draft, filters)
}, { deep: true })

function apply() {
  validationError.value = ''
  if (draft.start && draft.end && draft.start > draft.end) {
    validationError.value = '开始日期不能晚于结束日期'
    return
  }
  Object.assign(filters, draft)
  emit('apply')
}

function reset() {
  draft.start = appState.meta.date_range.min || ''
  draft.end = appState.meta.date_range.max || ''
  draft.dept_code = ''
  Object.assign(filters, draft)
  validationError.value = ''
  emit('reset')
  emit('apply')
}
</script>

<template>
  <section class="filter-bar card" aria-label="数据筛选">
    <div class="filter-title">
      <AppIcon name="filter" :size="17" />
      <span>数据筛选</span>
    </div>
    <div class="filter-fields">
      <label class="filter-field">
        <span>开始日期</span>
        <input
          v-model="draft.start"
          class="form-control"
          type="date"
          :min="appState.meta.date_range.min"
          :max="appState.meta.date_range.max"
        >
      </label>
      <span class="date-separator">至</span>
      <label class="filter-field">
        <span>结束日期</span>
        <input
          v-model="draft.end"
          class="form-control"
          type="date"
          :min="appState.meta.date_range.min"
          :max="appState.meta.date_range.max"
        >
      </label>
      <label v-if="props.showDepartment" class="filter-field department-field">
        <span>科室</span>
        <select v-model="draft.dept_code" class="form-control">
          <option value="">全部科室</option>
          <option v-for="dept in appState.meta.departments" :key="dept.dept_code" :value="dept.dept_code">
            {{ dept.dept_name }}
          </option>
        </select>
      </label>
    </div>
    <div class="filter-actions">
      <span v-if="validationError" class="form-error">{{ validationError }}</span>
      <button class="btn btn-text" :disabled="props.loading" @click="reset">
        <AppIcon name="refresh" :size="15" />重置
      </button>
      <button class="btn btn-primary" :disabled="props.loading" @click="apply">
        <span v-if="props.loading" class="spinner" />
        <AppIcon v-else name="search" :size="15" />查询
      </button>
    </div>
  </section>
</template>

<style scoped>
.filter-bar {
  display: flex;
  align-items: flex-end;
  gap: 18px;
  margin-bottom: 18px;
  padding: 15px 18px;
  box-shadow: none;
}

.filter-title {
  display: flex;
  align-items: center;
  align-self: center;
  gap: 7px;
  padding-right: 18px;
  color: #3b536f;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  border-right: 1px solid var(--border);
}

.filter-title svg {
  color: var(--primary);
}

.filter-fields {
  display: flex;
  flex: 1;
  align-items: flex-end;
  gap: 10px;
  min-width: 0;
}

.filter-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 145px;
}

.filter-field > span {
  color: var(--text-muted);
  font-size: 11px;
}

.filter-field .form-control {
  height: 35px;
  font-size: 12px;
}

.department-field {
  min-width: 160px;
  max-width: 210px;
}

.date-separator {
  align-self: center;
  padding-top: 17px;
  color: var(--text-muted);
  font-size: 11px;
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-left: auto;
}

.filter-actions .btn {
  min-height: 35px;
}

@media (max-width: 1100px) {
  .filter-bar {
    flex-wrap: wrap;
  }

  .filter-title {
    align-self: center;
  }

  .filter-fields {
    order: 3;
    flex-basis: 100%;
  }

  .filter-actions {
    align-self: center;
  }
}

@media (max-width: 640px) {
  .filter-bar {
    align-items: center;
    gap: 12px;
    padding: 13px;
  }

  .filter-title {
    padding-right: 0;
    border: 0;
  }

  .filter-fields {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .filter-field,
  .department-field {
    min-width: 0;
    max-width: none;
  }

  .department-field {
    grid-column: 1 / -1;
  }

  .date-separator {
    display: none;
  }

  .filter-actions .btn-text {
    font-size: 0;
  }

  .filter-actions .btn-text svg {
    width: 17px;
    height: 17px;
  }

  .form-error {
    position: absolute;
    margin-top: 48px;
  }
}
</style>
