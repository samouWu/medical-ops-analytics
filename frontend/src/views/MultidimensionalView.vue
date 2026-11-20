<script setup>
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import FilterBar from '../components/FilterBar.vue'
import DataTable from '../components/DataTable.vue'
import StateBlock from '../components/StateBlock.vue'
import AppIcon from '../components/AppIcon.vue'
import { downloadFile, request } from '../api/client'
import { filterParams, loadMeta } from '../stores/app'
import { downloadBlob } from '../utils/helpers'
import { errorMessage } from '../utils/format'

const metrics = ref([])
const selectedMetrics = ref([])
const selectedDimensions = ref(['dept_code'])
const comparisons = ref(['yoy', 'mom'])
const grain = ref('day')
const search = ref('')
const loadingMetrics = ref(false)
const querying = ref(false)
const exporting = ref(false)
const error = ref('')
const notice = ref('')
const result = ref(null)
const hasQueried = ref(false)

const filteredMetrics = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  return metrics.value.filter((metric) => !keyword || `${metric.name}${metric.code}${metric.topic}`.toLowerCase().includes(keyword))
})
const columns = computed(() => result.value?.columns || [])
const rows = computed(() => result.value?.rows || [])

async function fetchMetrics() {
  loadingMetrics.value = true
  error.value = ''
  try {
    const data = await request('/metrics')
    metrics.value = Array.isArray(data) ? data : []
    const first = metrics.value.find((metric) => metric.supported !== false)
    if (first) selectedMetrics.value = [first.code]
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loadingMetrics.value = false
  }
}

function toggleMetric(code) {
  selectedMetrics.value = selectedMetrics.value.includes(code)
    ? selectedMetrics.value.filter((item) => item !== code)
    : [...selectedMetrics.value, code]
}

function toggleDimension(code) {
  selectedDimensions.value = selectedDimensions.value.includes(code)
    ? selectedDimensions.value.filter((item) => item !== code)
    : [...selectedDimensions.value, code]
}

function toggleComparison(code) {
  comparisons.value = comparisons.value.includes(code)
    ? comparisons.value.filter((item) => item !== code)
    : [...comparisons.value, code]
}

function queryPayload() {
  return {
    metrics: selectedMetrics.value,
    dimensions: selectedDimensions.value,
    filters: filterParams(),
    grain: grain.value,
    comparisons: comparisons.value,
  }
}

async function exportReport() {
  exporting.value = true
  error.value = ''
  notice.value = ''
  try {
    const { blob, filename } = await downloadFile('/reports/query/export', {}, '多维报表.xlsx', {
      method: 'POST',
      body: queryPayload(),
    })
    downloadBlob(blob, filename)
    notice.value = '多维报表 Excel 导出成功'
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    exporting.value = false
  }
}

async function runQuery() {
  error.value = ''
  notice.value = ''
  if (!selectedMetrics.value.length) {
    error.value = '请至少选择一个查询指标'
    return
  }
  if (!selectedDimensions.value.length) {
    error.value = '请至少选择一个分析维度'
    return
  }
  querying.value = true
  hasQueried.value = true
  try {
    result.value = await request('/reports/query', {
      method: 'POST',
      body: queryPayload(),
    })
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    querying.value = false
  }
}

onMounted(async () => {
  await loadMeta()
  await fetchMetrics()
  if (selectedMetrics.value.length) runQuery()
})
</script>

<template>
  <div class="page">
    <PageHeader title="多维报表" description="自由组合指标与维度，快速生成个性化运营报表">
      <template #actions>
        <button class="btn btn-primary" :disabled="!hasQueried || exporting || querying" @click="exportReport">
          <span v-if="exporting" class="spinner" /><AppIcon v-else name="download" :size="15" />
          {{ exporting ? '正在导出' : '导出 Excel' }}
        </button>
      </template>
    </PageHeader>
    <FilterBar :loading="querying" @apply="runQuery" />

    <section class="card builder-card">
      <div class="card-header">
        <div><h2 class="card-heading">报表配置</h2><p class="card-subheading">选择需要分析的指标、维度与时间粒度</p></div>
        <span class="status-badge info">已选 {{ selectedMetrics.length }} 个指标</span>
      </div>
      <div class="card-body builder-body">
        <div class="builder-section">
          <div class="builder-label"><span>1</span><strong>选择指标</strong><small>支持多选</small></div>
          <div class="metric-search"><AppIcon name="search" :size="15" /><input v-model="search" placeholder="搜索指标名称、编码或主题"></div>
          <div v-if="loadingMetrics" class="metric-options"><div v-for="i in 3" :key="i" class="skeleton option-skeleton" /></div>
          <div v-else class="metric-options">
            <label v-for="metric in filteredMetrics" :key="metric.code" class="metric-option" :class="{ selected: selectedMetrics.includes(metric.code), disabled: metric.supported === false }">
              <input type="checkbox" :checked="selectedMetrics.includes(metric.code)" :disabled="metric.supported === false" @change="toggleMetric(metric.code)">
              <span class="custom-check"><AppIcon name="check" :size="12" /></span>
              <span><strong>{{ metric.name }}</strong><small>{{ metric.code }} · {{ metric.topic }}</small></span>
              <em v-if="metric.unit">{{ metric.unit }}</em>
            </label>
            <p v-if="!filteredMetrics.length" class="no-metrics">未找到匹配指标</p>
          </div>
        </div>

        <div class="builder-bottom">
          <div class="dimension-section">
            <div class="builder-label"><span>2</span><strong>分析维度</strong></div>
            <div class="dimension-options">
              <label :class="{ selected: selectedDimensions.includes('dept_code') }"><input type="checkbox" :checked="selectedDimensions.includes('dept_code')" @change="toggleDimension('dept_code')"><AppIcon name="building" :size="16" />科室维度</label>
              <label :class="{ selected: selectedDimensions.includes('date') }"><input type="checkbox" :checked="selectedDimensions.includes('date')" @change="toggleDimension('date')"><AppIcon name="calendar" :size="16" />日期维度</label>
            </div>
          </div>
          <div class="grain-section">
            <div class="builder-label"><span>3</span><strong>时间粒度</strong></div>
            <div class="segmented"><button :class="{ active: grain === 'day' }" @click="grain = 'day'">按日</button><button :class="{ active: grain === 'week' }" @click="grain = 'week'">按周</button><button :class="{ active: grain === 'month' }" @click="grain = 'month'">按月</button></div>
          </div>
          <div class="compare-section">
            <div class="builder-label"><span>4</span><strong>对比分析</strong></div>
            <div class="dimension-options">
              <label :class="{ selected: comparisons.includes('yoy') }"><input type="checkbox" :checked="comparisons.includes('yoy')" @change="toggleComparison('yoy')">同比</label>
              <label :class="{ selected: comparisons.includes('mom') }"><input type="checkbox" :checked="comparisons.includes('mom')" @change="toggleComparison('mom')">环比</label>
            </div>
          </div>
          <button class="btn btn-primary generate-button" :disabled="querying" @click="runQuery">
            <span v-if="querying" class="spinner" /><AppIcon v-else name="multidimensional" :size="16" />{{ querying ? '正在生成' : '生成报表' }}
          </button>
        </div>
      </div>
    </section>

    <div v-if="error" class="query-error"><AppIcon name="alert" :size="16" />{{ error }}<button class="btn btn-sm" @click="runQuery">重试</button></div>
    <div v-if="notice" class="query-notice"><AppIcon name="check" :size="16" />{{ notice }}</div>

    <section class="card result-card">
      <div class="card-header">
        <div><h2 class="card-heading">报表结果</h2><p class="card-subheading">查询结果按所选指标与维度展示</p></div>
        <span v-if="result" class="status-badge">{{ rows.length }} 条记录</span>
      </div>
      <p v-if="result?.note" class="result-note"><AppIcon name="alert" :size="14" />{{ result.note }}</p>
      <StateBlock v-if="!hasQueried && !querying" title="开始构建您的报表" description="选择指标和维度后，点击生成报表查看结果" />
      <DataTable v-else :columns="columns" :rows="rows" :loading="querying" :page-size="12" />
    </section>
  </div>
</template>

<style scoped>
.builder-card,
.result-card {
  overflow: hidden;
}

.builder-card {
  margin-bottom: 18px;
}

.builder-body {
  padding: 0;
}

.builder-section {
  padding: 20px;
}

.builder-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 13px;
}

.builder-label > span {
  display: grid;
  width: 21px;
  height: 21px;
  place-items: center;
  color: var(--primary);
  font-size: 11px;
  font-weight: 600;
  background: var(--primary-soft);
  border-radius: 50%;
}

.builder-label strong {
  color: #3d546e;
  font-size: 12px;
  font-weight: 600;
}

.builder-label small {
  color: var(--text-muted);
  font-size: 11px;
}

.metric-search {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 280px;
  height: 34px;
  margin-bottom: 12px;
  padding: 0 10px;
  color: var(--text-muted);
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: 6px;
}

.metric-search input {
  width: 100%;
  color: var(--text);
  font-size: 11px;
  background: transparent;
  border: 0;
  outline: 0;
}

.metric-options {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  max-height: 180px;
  overflow: auto;
}

.metric-option {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
  padding: 10px;
  background: #fafbfd;
  border: 1px solid var(--border);
  border-radius: 7px;
  cursor: pointer;
}

.metric-option.selected {
  background: #f2f7ff;
  border-color: #a7c8f7;
}

.metric-option.disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.metric-option input,
.dimension-options input {
  position: absolute;
  opacity: 0;
}

.custom-check {
  display: grid;
  flex: 0 0 16px;
  width: 16px;
  height: 16px;
  place-items: center;
  color: transparent;
  background: #fff;
  border: 1px solid #cbd6e2;
  border-radius: 4px;
}

.metric-option.selected .custom-check {
  color: #fff;
  background: var(--primary);
  border-color: var(--primary);
}

.metric-option > span:nth-of-type(2) {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.metric-option strong {
  overflow: hidden;
  color: #40566f;
  font-size: 11px;
  font-weight: 550;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric-option small {
  margin-top: 4px;
  overflow: hidden;
  color: var(--text-muted);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric-option em {
  color: var(--text-muted);
  font-size: 10px;
  font-style: normal;
}

.option-skeleton {
  height: 57px;
}

.no-metrics {
  grid-column: 1 / -1;
  padding: 20px;
  color: var(--text-muted);
  font-size: 12px;
  text-align: center;
}

.builder-bottom {
  display: flex;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 20px 26px;
  padding: 17px 20px;
  background: #fafbfd;
  border-top: 1px solid var(--border);
}

.dimension-options {
  display: flex;
  gap: 8px;
}

.dimension-options label {
  display: flex;
  align-items: center;
  gap: 7px;
  min-height: 35px;
  padding: 7px 12px;
  color: var(--text-secondary);
  font-size: 11px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 6px;
  cursor: pointer;
}

.dimension-options label.selected {
  color: var(--primary);
  background: var(--primary-soft);
  border-color: #a7c8f7;
}

.generate-button {
  margin-left: auto;
}

.query-error {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 16px;
  padding: 10px 13px;
  color: var(--danger);
  font-size: 12px;
  background: var(--danger-soft);
  border-radius: 7px;
}

.query-error .btn {
  margin-left: auto;
}

.result-note {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 20px 12px;
  padding: 8px 11px;
  color: #8a6218;
  font-size: 12px;
  background: var(--warning-soft);
  border: 1px solid #f6e3bf;
  border-radius: 7px;
}

.query-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding: 10px 13px;
  color: #138061;
  font-size: 12px;
  background: var(--success-soft);
  border-radius: 7px;
}

@media (max-width: 1050px) {
  .metric-options {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .metric-options {
    grid-template-columns: 1fr;
  }

  .metric-search {
    width: 100%;
  }

  .builder-bottom {
    align-items: stretch;
    flex-direction: column;
    gap: 17px;
  }

  .generate-button {
    align-self: flex-end;
    margin-left: 0;
  }
}
</style>
