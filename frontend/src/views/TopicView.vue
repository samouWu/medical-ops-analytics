<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '../components/PageHeader.vue'
import FilterBar from '../components/FilterBar.vue'
import MetricCard from '../components/MetricCard.vue'
import LineChart from '../components/charts/LineChart.vue'
import BarChart from '../components/charts/BarChart.vue'
import PieChart from '../components/charts/PieChart.vue'
import ScatterChart from '../components/charts/ScatterChart.vue'
import DataTable from '../components/DataTable.vue'
import StateBlock from '../components/StateBlock.vue'
import AppIcon from '../components/AppIcon.vue'
import { downloadFile, request } from '../api/client'
import { appState, filterParams, filters, loadMeta } from '../stores/app'
import { downloadBlob } from '../utils/helpers'
import { errorMessage } from '../utils/format'

const route = useRoute()
const topic = route.meta.topic
const title = route.meta.title
const loading = ref(false)
const exporting = ref(false)
const error = ref('')
const notice = ref('')
const data = ref({ cards: [], trends: [], distribution: [], table: { columns: [], rows: [] } })
let requestId = 0

const trendSeries = computed(() => {
  const trends = data.value.trends || []
  const type = data.value.chart_type === 'bar' ? 'bar' : 'line'
  const maxValue = trends.reduce((acc, item) => Math.max(acc, Math.abs(Number(item.value) || 0)), 0)
  const wan = ['revenue', 'drugs', 'consumables'].includes(topic) && maxValue >= 100000
  const values = wan ? trends.map((item) => Number(((Number(item.value) || 0)/10000).toFixed(2))) : trends.map((item) => item.value)
  return [
    { name: `${trends[0]?.label || '指标值'}${wan ? '（万元）' : ''}`, data: values, type, area: type === 'line' },
    ...(trends.some((item) => item.value2 !== null && item.value2 !== undefined) ? [{
      name: trends[0]?.label2 || '对比指标',
      data: trends.map((item) => item.value2),
      type,
      yAxisIndex: 1,
      area: false,
    }] : []),
  ]
})

const distributionHorizontal = computed(() => data.value.chart_type === 'horizontal_bar' || (data.value.distribution || []).length > 8)
// 收入/药品/耗材主题的结构金额按万元展示，其余主题保留原始计量单位。
const moneyTopic = computed(() => ['revenue', 'drugs', 'consumables'].includes(topic))
const wanScale = computed(() => moneyTopic.value && (data.value.distribution || []).some((item) => Math.abs(Number(item.value) || 0) >= 100000))
const chartDistribution = computed(() => {
  const items = data.value.distribution || []
  if (!wanScale.value) return items
  return items.map((item) => ({ ...item, value: Number((Number(item.value || 0) / 10000).toFixed(2)) }))
})
const scatterPoints = computed(() => (data.value.table?.rows || []).map((item) => [
  Number(item.revenue || 0) / 10000,
  Number(item.usage || 0),
  item.name,
  12,
]))
const hasTrend = computed(() => data.value.trend_available !== false && (data.value.trends || []).length > 0)
// 选择能让末行最满的列数（最多5列），避免出现半行空白。
const cardColumns = computed(() => {
  const total = (data.value.cards || []).length
  if (total <= 1) return total || 1
  let best = Math.min(total, 5)
  let bestGap = total
  for (let cols = Math.min(total, 5); cols >= 2; cols -= 1) {
    const gap = (cols - (total % cols)) % cols
    if (gap < bestGap) { best = cols; bestGap = gap }
  }
  return best
})
const tableColumns = computed(() => data.value.table?.columns || [])
const tableRows = computed(() => data.value.table?.rows || [])
const drillDepartment = computed(() => appState.meta.departments.find((item) => item.dept_code === filters.dept_code))

async function fetchTopic() {
  const currentRequest = ++requestId
  loading.value = true
  error.value = ''
  notice.value = ''
  try {
    const result = await request(`/analytics/${topic}`, { query: filterParams() })
    if (currentRequest !== requestId) return
    data.value = {
      ...result,
      cards: Array.isArray(result?.cards) ? result.cards : [],
      trends: Array.isArray(result?.trends) ? result.trends : [],
      distribution: Array.isArray(result?.distribution) ? result.distribution : [],
      table: result?.table || { columns: [], rows: [] },
    }
  } catch (err) {
    if (currentRequest === requestId) error.value = errorMessage(err)
  } finally {
    if (currentRequest === requestId) loading.value = false
  }
}

async function drillIntoDepartment(params) {
  if (filters.dept_code) return
  const department = appState.meta.departments.find((item) => item.dept_name === params.name)
  if (!department) return
  filters.dept_code = department.dept_code
  await fetchTopic()
  notice.value = `已下钻到 ${department.dept_name}，可点击“返回全院”恢复`
}

async function resetDrill() {
  filters.dept_code = ''
  await fetchTopic()
  notice.value = ''
}

async function exportTopic() {
  exporting.value = true
  notice.value = ''
  error.value = ''
  try {
    const { blob, filename } = await downloadFile(`/export/${topic}`, filterParams(), `${title}.xlsx`)
    downloadBlob(blob, filename)
    notice.value = '报表导出成功'
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  await loadMeta()
  fetchTopic()
})
</script>

<template>
  <div class="page">
    <PageHeader :title="title" :description="route.meta.description">
      <template #actions>
        <button v-if="filters.dept_code" class="btn" :disabled="loading" @click="resetDrill"><AppIcon name="chevronRight" :size="15" class="back-icon" />返回全院</button>
        <button class="btn" :disabled="loading" @click="fetchTopic"><AppIcon name="refresh" :size="15" />刷新</button>
        <button class="btn btn-primary" :disabled="exporting || loading" @click="exportTopic">
          <span v-if="exporting" class="spinner" /><AppIcon v-else name="download" :size="15" />
          {{ exporting ? '正在导出' : '导出报表' }}
        </button>
      </template>
    </PageHeader>

    <FilterBar :loading="loading" @apply="fetchTopic" />

    <div v-if="drillDepartment" class="drill-banner">
      <span>当前已下钻至 <strong>{{ drillDepartment.dept_name }}</strong>，图表与明细均已按科室过滤</span>
      <button class="btn btn-sm" @click="resetDrill">返回全院</button>
    </div>

    <div v-if="error" class="page-message error"><AppIcon name="alert" :size="16" /><span>{{ error }}</span><button class="btn btn-sm" @click="fetchTopic">重试</button></div>
    <div v-if="notice" class="page-message success"><AppIcon name="check" :size="16" />{{ notice }}</div>

    <div v-if="data.cards.length" class="metrics-grid" :style="{ '--cols': cardColumns }">
      <MetricCard v-for="(card, index) in data.cards" :key="card.key" :card="card" :index="index" />
    </div>

    <div class="dashboard-grid" :class="{ single: !hasTrend }">
      <section v-if="hasTrend" class="card">
        <div class="card-header">
          <div><h2 class="card-heading">{{ title }}趋势</h2><p class="card-subheading">核心指标随时间变化情况</p></div>
          <span class="status-badge info">趋势分析</span>
        </div>
        <div class="card-body chart-body">
          <StateBlock v-if="!loading && !data.trends.length" compact />
          <div v-else class="chart"><LineChart :dates="data.trends.map((item) => item.date)" :series="trendSeries" :loading="loading" /></div>
        </div>
      </section>

      <section class="card">
        <div class="card-header">
          <div><h2 class="card-heading">{{ data.bar_title || '结构分布' }}</h2><p class="card-subheading">{{ filters.dept_code ? '当前科室结构' : '点击科室分类可下钻查看' }}</p></div>
          <AppIcon name="multidimensional" :size="18" class="header-icon" />
        </div>
        <div class="card-body chart-body">
          <StateBlock v-if="!loading && !data.distribution.length" compact />
          <div v-else class="chart">
            <ScatterChart
              v-if="topic === 'resources'"
              :points="scatterPoints"
              x-name="医疗收入（万元）"
              y-name="床位使用率（%）"
              name="科室资源效率"
              :loading="loading"
            />
            <BarChart
              v-else-if="distributionHorizontal"
              :categories="chartDistribution.map((item) => item.name)"
              :values="chartDistribution.map((item) => item.value)"
              :name="`${data.bar_title || '数量'}${wanScale ? '（万元）' : ''}`"
              horizontal
              color="#20a995"
              :loading="loading"
              @chart-click="drillIntoDepartment"
            />
            <PieChart
              v-else
              :data="chartDistribution"
              :name="data.bar_title || '构成'"
              :unit="wanScale ? ' 万元' : ''"
              :loading="loading"
              @chart-click="drillIntoDepartment"
            />
          </div>
        </div>
      </section>
    </div>

    <section v-if="tableColumns.length && tableRows.length" class="card table-card">
      <div class="card-header">
        <div><h2 class="card-heading">运营明细</h2><p class="card-subheading">{{ data.source_note || '当前筛选条件下的主题明细数据' }}</p></div>
        <span v-if="tableRows.length" class="status-badge">共 {{ tableRows.length }} 条</span>
      </div>
      <DataTable
        :columns="tableColumns"
        :rows="tableRows"
        :loading="loading"
        :error="error && !data.cards.length ? error : ''"
        :page-size="10"
        @retry="fetchTopic"
      />
    </section>
  </div>
</template>

<style scoped>
.dashboard-grid.single {
  grid-template-columns: minmax(0, 1fr);
}

.page-message {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding: 10px 13px;
  font-size: 12px;
  border-radius: 7px;
}

.page-message span {
  flex: 1;
}

.page-message.error {
  color: #b84848;
  background: var(--danger-soft);
}

.page-message.success {
  color: #138061;
  background: var(--success-soft);
}

.chart-body {
  padding-top: 12px;
  padding-bottom: 10px;
}

.drill-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  padding: 10px 14px;
  color: #245b9e;
  font-size: 12px;
  background: var(--primary-soft);
  border: 1px solid #cbdcf5;
  border-radius: 8px;
}

.back-icon {
  transform: rotate(180deg);
}

.header-icon {
  color: #8ca2ba;
}

.table-card {
  overflow: hidden;
}
</style>
