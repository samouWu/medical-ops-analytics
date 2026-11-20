<script setup>
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import FilterBar from '../components/FilterBar.vue'
import MetricCard from '../components/MetricCard.vue'
import BarChart from '../components/charts/BarChart.vue'
import DataTable from '../components/DataTable.vue'
import StateBlock from '../components/StateBlock.vue'
import AppIcon from '../components/AppIcon.vue'
import { downloadFile, request } from '../api/client'
import { filterParams, loadMeta } from '../stores/app'
import { downloadBlob } from '../utils/helpers'
import { errorMessage, formatMetric } from '../utils/format'

const loading = ref(false)
const exporting = ref(false)
const error = ref('')
const notice = ref('')
const data = ref({ cards: [], table: { columns: [], rows: [] } })
let requestId = 0

const rows = computed(() => data.value.table?.rows || [])
const usageCategories = computed(() => rows.value.map((item) => item.name))
const usageValues = computed(() => rows.value.map((item) => Number(item.usage) || 0))
const turnoverValues = computed(() => rows.value.map((item) => Number(item.turnover) || 0))
const columns = [
  { key: 'name', label: '科室', width: '24%' },
  { key: 'beds', label: '编制床位' },
  { key: 'usage', label: '床位使用率', format: 'percent' },
  { key: 'turnover', label: '床位周转次数' },
  { key: 'staff', label: '配置人力' },
  { key: 'revenue', label: '医疗收入（元）', format: 'money' },
]

async function fetchData() {
  const current = ++requestId
  loading.value = true
  error.value = ''
  notice.value = ''
  try {
    const result = await request('/analytics/resources', { query: filterParams() })
    if (current !== requestId) return
    data.value = {
      cards: Array.isArray(result?.cards) ? result.cards : [],
      table: result?.table || { columns: [], rows: [] },
    }
  } catch (err) {
    if (current === requestId) error.value = errorMessage(err)
  } finally {
    if (current === requestId) loading.value = false
  }
}

async function exportData() {
  exporting.value = true
  error.value = ''
  try {
    const { blob, filename } = await downloadFile('/export/resources', filterParams(), '资源效率分析.xlsx')
    downloadBlob(blob, filename)
    notice.value = '资源效率报表导出成功'
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  await loadMeta()
  await fetchData()
})
</script>

<template>
  <div class="page">
    <PageHeader title="资源效率" description="评估科室床位配置、利用效率与服务承载能力">
      <template #actions>
        <button class="btn" :disabled="loading" @click="fetchData"><AppIcon name="refresh" :size="15" />刷新</button>
        <button class="btn btn-primary" :disabled="exporting || loading" @click="exportData">
          <span v-if="exporting" class="spinner" /><AppIcon v-else name="download" :size="15" />
          {{ exporting ? '正在导出' : '导出 Excel' }}
        </button>
      </template>
    </PageHeader>

    <FilterBar :loading="loading" @apply="fetchData" />

    <div v-if="error" class="resource-message error"><AppIcon name="alert" :size="16" /><span>{{ error }}</span><button class="btn btn-sm" @click="fetchData">重试</button></div>
    <div v-if="notice" class="resource-message success"><AppIcon name="check" :size="16" />{{ notice }}</div>

    <div v-if="data.cards.length" class="metrics-grid resource-metrics" :style="{ '--cols': data.cards.length }">
      <MetricCard v-for="(card, index) in data.cards" :key="card.key" :card="card" :index="index" />
    </div>

    <div class="resource-charts">
      <section class="card">
        <div class="card-header"><div><h2 class="card-heading">各科室床位使用率</h2><p class="card-subheading">实际占用床日占开放床日的比例</p></div><span class="status-badge info">使用率</span></div>
        <div class="card-body chart-body">
          <StateBlock v-if="!loading && !rows.length" compact />
          <div v-else class="chart chart-md"><BarChart :categories="usageCategories" :values="usageValues" name="床位使用率（%）" color="#2f7cf6" :loading="loading" /></div>
        </div>
      </section>
      <section class="card">
        <div class="card-header"><div><h2 class="card-heading">各科室床位周转次数</h2><p class="card-subheading">出院人次与平均开放床位的比值</p></div><span class="status-badge success">周转次数</span></div>
        <div class="card-body chart-body">
          <StateBlock v-if="!loading && !rows.length" compact />
          <div v-else class="chart chart-md"><BarChart :categories="usageCategories" :values="turnoverValues" name="床位周转次数" color="#20a995" :loading="loading" /></div>
        </div>
      </section>
    </div>

    <section class="card resource-table">
      <div class="card-header"><div><h2 class="card-heading">科室资源明细</h2><p class="card-subheading">床位、人力、使用效率和收入对照</p></div><span v-if="rows.length" class="status-badge">{{ rows.length }} 个科室</span></div>
      <DataTable :columns="columns" :rows="rows" :loading="loading" :page-size="10">
        <template #cell-usage="{ value }"><strong class="usage-value">{{ value === null ? '—' : `${value.toFixed(2)}%` }}</strong></template>
        <template #cell-turnover="{ value }"><strong class="turnover-value">{{ value === null ? '—' : Number(value).toFixed(2) }}</strong></template>
        <template #cell-revenue="{ value }">{{ formatMetric(value, '元') }}</template>
      </DataTable>
    </section>
  </div>
</template>

<style scoped>
.resource-message { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; padding: 10px 13px; font-size: 12px; border-radius: 7px; }
.resource-message.error { color: var(--danger); background: var(--danger-soft); }
.resource-message.success { color: var(--success); background: var(--success-soft); }
.resource-message span { flex: 1; }
.resource-metrics { margin-bottom: 18px; }
.resource-charts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; margin-bottom: 18px; }
.chart-body { padding-top: 10px; padding-bottom: 10px; }
.resource-table { overflow: hidden; }
.usage-value { color: #246fcf; font-weight: 600; }
.turnover-value { color: #168e7d; font-weight: 600; }
@media (max-width: 1050px) { .resource-charts { grid-template-columns: 1fr; } }
@media (max-width: 900px) { .resource-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 640px) { .resource-metrics { grid-template-columns: 1fr; } }
</style>
