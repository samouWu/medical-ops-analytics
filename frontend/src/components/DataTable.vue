<script setup>
import { computed, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'
import StateBlock from './StateBlock.vue'
import { formatNumber } from '../utils/format'

const props = defineProps({
  columns: { type: Array, default: () => [] },
  rows: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  emptyText: { type: String, default: '暂无数据' },
  pageSize: { type: Number, default: 10 },
  rowKey: { type: String, default: 'id' },
  maxHeight: { type: String, default: '' },
})
defineEmits(['retry'])

const currentPage = ref(1)
const pageCount = computed(() => Math.max(1, Math.ceil(props.rows.length / props.pageSize)))
const visibleRows = computed(() => {
  if (!props.pageSize) return props.rows
  const start = (currentPage.value - 1) * props.pageSize
  return props.rows.slice(start, start + props.pageSize)
})
const rangeStart = computed(() => props.rows.length ? (currentPage.value - 1) * props.pageSize + 1 : 0)
const rangeEnd = computed(() => Math.min(currentPage.value * props.pageSize, props.rows.length))

watch(() => props.rows, () => { currentPage.value = 1 })
watch(pageCount, (count) => {
  if (currentPage.value > count) currentPage.value = count
})

function displayValue(value, column = {}) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'number') return column.format === 'percent' ? `${formatNumber(value)}%` : formatNumber(value)
  if (Array.isArray(value)) return value.join('、')
  if (typeof value === 'object') return '—'
  return String(value)
}

function getRowKey(row, index) {
  return row?.[props.rowKey] ?? row?.dept_code ?? row?.code ?? index
}
</script>

<template>
  <div class="data-table-wrap">
    <StateBlock v-if="loading" type="loading" compact title="正在加载表格数据" />
    <StateBlock v-else-if="error" type="error" compact :description="error" @retry="$emit('retry')" />
    <StateBlock v-else-if="!rows.length" compact :title="emptyText" />
    <template v-else>
      <div class="table-scroll" :style="maxHeight ? { maxHeight } : undefined">
        <table class="data-table">
          <thead>
            <tr>
              <th v-for="column in columns" :key="column.key" :style="column.width ? { width: column.width } : undefined">
                {{ column.label }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in visibleRows" :key="getRowKey(row, index)">
              <td v-for="column in columns" :key="column.key">
                <slot :name="`cell-${column.key}`" :row="row" :value="row[column.key]" :index="index">
                  {{ displayValue(row[column.key], column) }}
                </slot>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="pageSize && rows.length > pageSize" class="table-pagination">
        <span>共 {{ rows.length }} 条，当前 {{ rangeStart }}–{{ rangeEnd }} 条</span>
        <div>
          <button class="page-button" :disabled="currentPage <= 1" aria-label="上一页" @click="currentPage--">
            <AppIcon name="chevronRight" :size="14" />
          </button>
          <span class="page-number">{{ currentPage }} / {{ pageCount }}</span>
          <button class="page-button next" :disabled="currentPage >= pageCount" aria-label="下一页" @click="currentPage++">
            <AppIcon name="chevronRight" :size="14" />
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.data-table-wrap {
  min-width: 0;
}

.table-scroll {
  width: 100%;
  overflow: auto;
}

.data-table {
  width: 100%;
  font-size: 12px;
  border-collapse: collapse;
  border-spacing: 0;
}

.data-table th {
  height: 42px;
  padding: 10px 16px;
  color: #71849a;
  font-size: 11px;
  font-weight: 550;
  text-align: left;
  white-space: nowrap;
  background: #f7f9fc;
  border-bottom: 1px solid var(--border);
}

.data-table td {
  height: 47px;
  padding: 11px 16px;
  color: #3f536b;
  white-space: nowrap;
  border-bottom: 1px solid #edf1f5;
}

.data-table tbody tr {
  transition: background-color 120ms ease;
}

.data-table tbody tr:hover {
  background: #f8fbff;
}

.data-table tbody tr:last-child td {
  border-bottom: 0;
}

.table-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  min-height: 52px;
  padding: 10px 16px;
  color: var(--text-muted);
  font-size: 11px;
  border-top: 1px solid var(--border);
}

.table-pagination > div {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-button {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  color: var(--text-secondary);
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 6px;
}

.page-button:first-child svg {
  transform: rotate(180deg);
}

.page-button:hover:not(:disabled) {
  color: var(--primary);
  border-color: #a9c8f7;
}

.page-number {
  min-width: 46px;
  text-align: center;
}

@media (max-width: 640px) {
  .data-table th,
  .data-table td {
    padding-right: 12px;
    padding-left: 12px;
  }

  .table-pagination {
    align-items: flex-start;
    flex-direction: column;
  }

  .table-pagination > div {
    align-self: flex-end;
  }
}
</style>
