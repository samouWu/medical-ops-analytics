<script setup>
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import FilterBar from '../components/FilterBar.vue'
import MetricCard from '../components/MetricCard.vue'
import ImportDialog from '../components/ImportDialog.vue'
import LineChart from '../components/charts/LineChart.vue'
import BarChart from '../components/charts/BarChart.vue'
import StateBlock from '../components/StateBlock.vue'
import AppIcon from '../components/AppIcon.vue'
import { downloadFile, request } from '../api/client'
import { appState, filterParams, filters, loadMeta } from '../stores/app'
import { errorMessage } from '../utils/format'
import { downloadBlob } from '../utils/helpers'

const loading = ref(false)
const error = ref('')
const notice = ref('')
const importOpen = ref(false)
const exporting = ref(false)
const data = ref({ cards: [], trends: [], top_departments: [] })
const drillDepartment = computed(() => appState.meta.departments.find((item) => item.dept_code === filters.dept_code))
// 收入趋势与科室排行统一折算为万元，与指标卡口径保持一致。
const revenueTrend = computed(() => data.value.trends.map((item) => Number(((item.revenue || 0)/10000).toFixed(2))))
const departmentRevenue = computed(() => data.value.top_departments.map((item) => Number(((item.revenue || 0)/10000).toFixed(2))))
let requestId = 0

async function fetchDashboard() {
  const currentRequest = ++requestId
  loading.value = true
  error.value = ''
  try {
    const result = await request('/dashboards/management', { query: filterParams() })
    if (currentRequest !== requestId) return
    data.value = {
      cards: Array.isArray(result?.cards) ? result.cards : [],
      trends: Array.isArray(result?.trends) ? result.trends : [],
      top_departments: Array.isArray(result?.top_departments) ? result.top_departments : [],
    }
  } catch (err) {
    if (currentRequest === requestId) error.value = errorMessage(err)
  } finally {
    if (currentRequest === requestId) loading.value = false
  }
}

async function exportDashboard() {
  exporting.value = true
  notice.value = ''
  try {
    const { blob, filename } = await downloadFile('/export/management', filterParams(), '管理驾驶舱.xlsx')
    downloadBlob(blob, filename)
    notice.value = '管理驾驶舱 Excel 导出成功'
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    exporting.value = false
  }
}

async function onImported(result) {
  // 弹窗保持打开展示导入结果，看板在后台刷新。
  notice.value = `已导入 ${result?.row_count ?? 0} 行数据（${result?.source_table || '目标表'}），数仓已同步重建`
  await loadMeta()
  await fetchDashboard()
}

async function drillIntoDepartment(params) {
  if (filters.dept_code) return
  const department = appState.meta.departments.find((item) => item.dept_name === params.name)
  if (!department) return
  filters.dept_code = department.dept_code
  await fetchDashboard()
}

async function resetDrill() {
  filters.dept_code = ''
  await fetchDashboard()
}

onMounted(async () => {
  await loadMeta()
  fetchDashboard()
})
</script>

<template>
  <div class="page dashboard-page">
    <PageHeader title="管理驾驶舱" description="聚合核心运营指标，纵览全院医疗服务与经营态势">
      <template #actions>
        <button v-if="filters.dept_code" class="btn" :disabled="loading" @click="resetDrill">
          <AppIcon name="chevronRight" :size="15" class="back-icon" />返回全院
        </button>
        <button class="btn" @click="importOpen = true">
          <AppIcon name="upload" :size="15" />导入数据
        </button>
        <button class="btn" :disabled="exporting" @click="exportDashboard">
          <span v-if="exporting" class="spinner" /><AppIcon v-else name="download" :size="15" />{{ exporting ? '导出中' : '导出 Excel' }}
        </button>
        <button class="btn" :disabled="loading" @click="fetchDashboard">
          <AppIcon name="refresh" :size="15" />刷新数据
        </button>
      </template>
    </PageHeader>

    <FilterBar :loading="loading" @apply="fetchDashboard" />

    <div v-if="notice" class="dashboard-notice"><AppIcon name="check" :size="16" />{{ notice }}</div>

    <div v-if="drillDepartment" class="drill-banner">
      <span>当前已下钻至 <strong>{{ drillDepartment.dept_name }}</strong>，可继续点击“返回全院”恢复</span>
      <button class="btn btn-sm" @click="resetDrill">返回全院</button>
    </div>

    <div v-if="error" class="dashboard-error">
      <AppIcon name="alert" :size="17" /><span>{{ error }}</span>
      <button class="btn btn-sm" @click="fetchDashboard">重试</button>
    </div>

    <div v-if="data.cards.length || loading" class="metrics-grid dashboard-metrics">
      <template v-if="loading && !data.cards.length">
        <div v-for="index in 4" :key="index" class="card metric-skeleton">
          <div class="skeleton" style="width: 40%; height: 13px" />
          <div class="skeleton" style="width: 62%; height: 30px; margin-top: 20px" />
          <div class="skeleton" style="width: 35%; height: 10px; margin-top: 17px" />
        </div>
      </template>
      <MetricCard v-for="(card, index) in data.cards" v-else :key="card.key" :card="card" :index="index" />
    </div>

    <StateBlock v-if="!loading && !data.cards.length && !data.trends.length && !data.top_departments.length" />

    <div v-else class="dashboard-grid">
      <section class="card">
        <div class="card-header">
          <div><h2 class="card-heading">运营趋势</h2><p class="card-subheading">门诊服务量与医疗收入变化</p></div>
          <span class="status-badge info">按日统计</span>
        </div>
        <div class="card-body chart-body">
          <StateBlock v-if="!loading && !data.trends.length" compact />
          <div v-else class="chart chart-lg">
            <LineChart
              :dates="data.trends.map((item) => item.date)"
              :series="[
                { name: '门诊人次', data: data.trends.map((item) => item.outpatient_visits), area: true },
                { name: '医疗收入（万元）', data: revenueTrend, yAxisIndex: 1, area: false },
              ]"
              :loading="loading"
            />
          </div>
        </div>
      </section>

      <section class="card">
        <div class="card-header">
          <div><h2 class="card-heading">科室收入排行</h2><p class="card-subheading">{{ filters.dept_code ? '当前科室运营表现' : '点击科室柱形可下钻' }}</p></div>
          <AppIcon name="building" :size="18" class="header-icon" />
        </div>
        <div class="card-body chart-body">
          <StateBlock v-if="!loading && !data.top_departments.length" compact />
          <div v-else class="chart chart-lg">
            <BarChart
              :categories="data.top_departments.map((item) => item.dept_name)"
              :values="departmentRevenue"
              name="医疗收入（万元）"
              horizontal
              color="#2f7cf6"
              :loading="loading"
              @chart-click="drillIntoDepartment"
            />
          </div>
        </div>
      </section>
    </div>
    <ImportDialog :open="importOpen" @close="importOpen = false" @success="onImported" />
  </div>
</template>

<style scoped>
.dashboard-page {
  position: relative;
}

.dashboard-notice {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 14px;
  padding: 9px 13px;
  color: #14805f;
  font-size: 12px;
  background: var(--success-soft);
  border: 1px solid #ccece0;
  border-radius: 7px;
}

.dashboard-error {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 16px;
  padding: 11px 14px;
  color: #b84848;
  font-size: 12px;
  background: var(--danger-soft);
  border: 1px solid #f6dede;
  border-radius: 8px;
}

.dashboard-error span {
  flex: 1;
}

.dashboard-metrics {
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.dashboard-metrics :deep(.metric-card) {
  min-width: 0;
  padding: 17px 16px 15px;
}

.dashboard-metrics :deep(.metric-content) {
  min-width: 0;
  white-space: nowrap;
}

.dashboard-metrics :deep(.metric-value) {
  min-width: 0;
  font-size: clamp(18px, 1.35vw, 22px);
  letter-spacing: -0.8px;
}

.dashboard-metrics :deep(.metric-icon) {
  width: 32px;
  height: 32px;
}

.dashboard-metrics :deep(.metric-label) {
  font-size: 12px;
}

.metric-skeleton {
  min-height: 147px;
  padding: 22px 20px;
}

@media (max-width: 1280px) {
  .dashboard-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .dashboard-metrics > :last-child { grid-column: 1 / -1; }
  .dashboard-metrics :deep(.metric-value) { font-size: 28px; }
}

@media (max-width: 820px) {
  .dashboard-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 560px) {
  .dashboard-metrics { grid-template-columns: 1fr; }
  .dashboard-metrics > :last-child { grid-column: auto; }
  .dashboard-metrics :deep(.metric-value) { font-size: 24px; }
}

.chart-body {
  padding-top: 10px;
  padding-bottom: 10px;
}

.header-icon {
  color: #8ca2ba;
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
</style>
