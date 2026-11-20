<script setup>
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import FilterBar from '../components/FilterBar.vue'
import LineChart from '../components/charts/LineChart.vue'
import DataTable from '../components/DataTable.vue'
import StateBlock from '../components/StateBlock.vue'
import AppIcon from '../components/AppIcon.vue'
import { request } from '../api/client'
import { filterParams, loadMeta } from '../stores/app'
import { errorMessage, formatMetric, formatNumber, isMoneyUnit } from '../utils/format'

const metrics = ref([])
const selectedCode = ref('')
const search = ref('')
const topicFilter = ref('')
const grain = ref('day')
const loadingMetrics = ref(false)
const loadingValues = ref(false)
const error = ref('')
const values = ref(null)

const topics = computed(() => [...new Set(metrics.value.map((item) => item.topic).filter(Boolean))])
const filteredMetrics = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  return metrics.value.filter((metric) => {
    const matchesKeyword = !keyword || `${metric.name}${metric.code}${metric.description || ''}`.toLowerCase().includes(keyword)
    return matchesKeyword && (!topicFilter.value || metric.topic === topicFilter.value)
  })
})
const selectedMetric = computed(() => metrics.value.find((item) => item.code === selectedCode.value))
const points = computed(() => values.value?.points || [])
const wanUnit = computed(() => isMoneyUnit(values.value?.metric?.unit))
const chartUnit = computed(() => (wanUnit.value ? '万元' : values.value?.metric?.unit || selectedMetric.value?.unit || ''))
const chartSeries = computed(() => [{
  name: `${values.value?.metric?.name || selectedMetric.value?.name || '指标值'}${wanUnit.value ? '（万元）' : ''}`,
  data: points.value.map((item) => {
    if (item.value === null || item.value === undefined) return null
    return wanUnit.value ? Number((Number(item.value)/10000).toFixed(2)) : item.value
  }),
}])
const summaryItems = computed(() => {
  const summary = values.value?.summary
  if (summary === null || summary === undefined) return []
  if (typeof summary !== 'object') return [{ label: '汇总值', value: summary }]
  const labels = { sum: '合计', avg: '平均值', average: '平均值', max: '最大值', min: '最小值', count: '记录数', latest: '最新值', value: '指标值' }
  return Object.entries(summary).map(([key, value]) => ({ label: labels[key] || key, value }))
})
const pointColumns = computed(() => [
  { key: 'date', label: '日期', width: '45%' },
  { key: 'value', label: `指标值${wanUnit.value ? '（万元）' : ''}` },
])

// 明细表整列统一单位，避免同一列出现元与万元混排。
function formatPointValue(value) {
  if (value === null || value === undefined) return '—'
  if (wanUnit.value) return `${formatNumber(Number(value)/10000, 'currency')}万元`
  return formatMetric(value, values.value?.metric?.unit)
}

async function fetchMetrics() {
  loadingMetrics.value = true
  error.value = ''
  try {
    const data = await request('/metrics')
    metrics.value = Array.isArray(data) ? data : []
    const first = metrics.value.find((item) => item.supported !== false)
    if (first) selectedCode.value = first.code
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loadingMetrics.value = false
  }
}

async function fetchValues() {
  if (!selectedCode.value) return
  loadingValues.value = true
  error.value = ''
  try {
    values.value = await request(`/metrics/${encodeURIComponent(selectedCode.value)}/values`, {
      query: { ...filterParams(), grain: grain.value },
    })
  } catch (err) {
    error.value = errorMessage(err)
    values.value = null
  } finally {
    loadingValues.value = false
  }
}

function selectMetric(metric) {
  if (metric.supported === false) return
  selectedCode.value = metric.code
  values.value = null
  fetchValues()
}

onMounted(async () => {
  await loadMeta()
  await fetchMetrics()
  fetchValues()
})
</script>

<template>
  <div class="page">
    <PageHeader title="指标查询" description="检索指标口径，查询不同时间粒度的指标结果" />
    <FilterBar :loading="loadingValues" @apply="fetchValues" />

    <div class="metrics-layout">
      <aside class="card metric-catalog">
        <div class="card-header"><div><h2 class="card-heading">指标目录</h2><p class="card-subheading">共 {{ metrics.length }} 项可查指标</p></div><AppIcon name="metrics" :size="18" /></div>
        <div class="catalog-filters">
          <div class="catalog-search"><AppIcon name="search" :size="15" /><input v-model="search" placeholder="搜索指标"></div>
          <select v-model="topicFilter" class="form-control" aria-label="指标主题"><option value="">全部主题</option><option v-for="topic in topics" :key="topic" :value="topic">{{ topic }}</option></select>
        </div>
        <div class="catalog-list">
          <StateBlock v-if="loadingMetrics" type="loading" compact />
          <button v-for="metric in filteredMetrics" v-else :key="metric.code" :class="{ active: selectedCode === metric.code }" :disabled="metric.supported === false" :title="metric.formula || metric.description" @click="selectMetric(metric)">
            <span class="catalog-item-top"><strong>{{ metric.name }}</strong><em v-if="metric.unit">{{ metric.unit }}</em></span>
            <span class="catalog-code">{{ metric.code }}</span>
            <span class="catalog-topic">{{ metric.topic }}<i v-if="metric.supported === false">暂不支持</i></span>
          </button>
          <p v-if="!loadingMetrics && !filteredMetrics.length" class="catalog-empty">未找到匹配指标</p>
        </div>
      </aside>

      <div class="metric-detail">
        <section class="card definition-card">
          <div v-if="selectedMetric" class="definition-content">
            <div class="definition-icon"><AppIcon name="multidimensional" :size="24" /></div>
            <div class="definition-main">
              <div class="definition-title"><h2>{{ selectedMetric.name }}</h2><span class="status-badge info">{{ selectedMetric.code }}</span><span v-if="selectedMetric.unit" class="status-badge">单位：{{ selectedMetric.unit }}</span></div>
              <p>{{ selectedMetric.description || '该指标暂无补充口径说明' }}</p>
              <div v-if="selectedMetric.formula" class="definition-formula">
                <span class="formula-label">计算公式</span>
                <code>{{ selectedMetric.formula }}</code>
              </div>
            </div>
            <div class="definition-query">
              <div class="segmented"><button :class="{ active: grain === 'day' }" @click="grain = 'day'">按日</button><button :class="{ active: grain === 'week' }" @click="grain = 'week'">按周</button><button :class="{ active: grain === 'month' }" @click="grain = 'month'">按月</button></div>
              <button class="btn btn-primary" :disabled="loadingValues" @click="fetchValues"><AppIcon name="search" :size="15" />查询</button>
            </div>
          </div>
          <StateBlock v-else compact title="请选择指标" />
        </section>

        <div v-if="summaryItems.length" class="summary-grid">
          <div v-for="item in summaryItems" :key="item.label" class="card summary-item"><span>{{ item.label }}</span><strong>{{ formatMetric(item.value, values?.metric?.unit) }}</strong></div>
        </div>

        <div v-if="error" class="metric-error"><AppIcon name="alert" :size="16" />{{ error }}<button class="btn btn-sm" @click="fetchValues">重试</button></div>

        <section class="card trend-card">
          <div class="card-header"><div><h2 class="card-heading">指标趋势</h2><p class="card-subheading">{{ grain === 'day' ? '按日' : grain === 'week' ? '按周' : '按月' }}展示指标变化</p></div><span v-if="points.length" class="status-badge">{{ points.length }} 个数据点</span></div>
          <div class="card-body">
            <StateBlock v-if="!loadingValues && !points.length" compact :title="error ? '指标查询未完成' : '暂无指标数据'" />
            <div v-else class="chart chart-sm">
              <LineChart
                :dates="points.map((item) => item.date)"
                :series="chartSeries"
                :y-axis-name="chartUnit"
                :loading="loadingValues"
              />
            </div>
            <p v-if="points.length" class="chart-note">数据截止日按源数据结算，期末在院患者为 0，床位使用率、出院人次等指标在最后一天会出现边界波动，属数据边界而非计算错误。</p>
          </div>
        </section>

        <section class="card points-card">
          <div class="card-header"><h2 class="card-heading">指标明细</h2></div>
          <DataTable :columns="pointColumns" :rows="points" :loading="loadingValues" :page-size="8">
            <template #cell-value="{ value }"><strong class="point-value">{{ formatPointValue(value) }}</strong></template>
          </DataTable>
          <p class="points-note">“—”表示该时点无分母可算（如当日无出院人次），不是数据缺失；指标值由 ADS 与统一指标服务同口径计算。</p>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.metrics-layout {
  display: grid;
  grid-template-columns: 290px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.metric-catalog {
  overflow: hidden;
}

.catalog-filters {
  display: grid;
  grid-template-columns: 1fr 105px;
  gap: 8px;
  padding: 13px;
  border-bottom: 1px solid var(--border);
}

.catalog-search {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 38px;
  padding: 0 9px;
  color: var(--text-muted);
  border: 1px solid #dfe6ee;
  border-radius: 7px;
}

.catalog-search input {
  min-width: 0;
  width: 100%;
  font-size: 11px;
  border: 0;
  outline: 0;
}

.catalog-filters .form-control {
  padding: 7px;
  font-size: 11px;
}

.catalog-list {
  max-height: 680px;
  padding: 7px;
  overflow-y: auto;
}

.catalog-list > button {
  display: flex;
  flex-direction: column;
  width: 100%;
  margin-bottom: 3px;
  padding: 12px;
  color: var(--text-secondary);
  text-align: left;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 7px;
}

.catalog-list > button:hover:not(:disabled) {
  background: #f6f9fc;
}

.catalog-list > button.active {
  background: var(--primary-soft);
  border-color: #ccddf6;
}

.catalog-item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.catalog-item-top strong {
  color: #354d67;
  font-size: 12px;
  font-weight: 550;
}

.catalog-item-top em {
  color: var(--text-muted);
  font-size: 11px;
  font-style: normal;
}

.catalog-code {
  margin-top: 5px;
  color: var(--text-muted);
  font-family: monospace;
  font-size: 11px;
}

.catalog-topic {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  color: #8194a9;
  font-size: 11px;
}

.catalog-topic i {
  color: var(--warning);
  font-style: normal;
}

.catalog-empty {
  padding: 30px 10px;
  color: var(--text-muted);
  font-size: 12px;
  text-align: center;
}

.metric-detail {
  min-width: 0;
}

.definition-card {
  margin-bottom: 16px;
}

.definition-content {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
}

.definition-icon {
  display: grid;
  flex: 0 0 48px;
  height: 48px;
  place-items: center;
  color: var(--primary);
  background: var(--primary-soft);
  border-radius: 11px;
}

.definition-main {
  flex: 1;
  min-width: 0;
}

.definition-title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.definition-title h2 {
  color: var(--text);
  font-size: 17px;
  font-weight: 600;
}

.definition-main > p {
  margin-top: 7px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.definition-formula {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  margin-top: 8px;
  padding: 8px 11px;
  background: #f6f9fe;
  border: 1px solid #e6eefb;
  border-radius: 7px;
}

.formula-label {
  color: #5b7392;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.2px;
}

.definition-formula code {
  color: #24507f;
  font-family: "Cascadia Mono", "JetBrains Mono", Consolas, "Microsoft YaHei", monospace;
  font-size: 12px;
  line-height: 1.6;
  word-break: break-word;
}

.chart-note {
  margin: 2px 2px 0;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.6;
}

.points-note {
  margin: 10px 2px 0;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.6;
}

.definition-query {
  display: flex;
  align-items: center;
  gap: 10px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px;
}

.summary-item span {
  color: var(--text-muted);
  font-size: 11px;
}

.summary-item strong {
  color: var(--primary);
  font-size: 20px;
  font-weight: 600;
}

.metric-error {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding: 10px 13px;
  color: var(--danger);
  font-size: 12px;
  background: var(--danger-soft);
  border-radius: 7px;
}

.metric-error .btn {
  margin-left: auto;
}

.trend-card,
.points-card {
  margin-bottom: 16px;
  overflow: hidden;
}

.point-value {
  color: var(--primary);
  font-weight: 600;
}

@media (max-width: 1180px) {
  .definition-content {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .definition-query {
    width: 100%;
    justify-content: flex-end;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .metrics-layout {
    grid-template-columns: 1fr;
  }

  .catalog-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    max-height: 300px;
  }
}

@media (max-width: 640px) {
  .catalog-list {
    grid-template-columns: 1fr;
  }

  .definition-icon {
    display: none;
  }

  .definition-query {
    justify-content: space-between;
  }
}
</style>
