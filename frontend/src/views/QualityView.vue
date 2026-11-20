<script setup>
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import DataTable from '../components/DataTable.vue'
import GaugeChart from '../components/charts/GaugeChart.vue'
import StateBlock from '../components/StateBlock.vue'
import AppIcon from '../components/AppIcon.vue'
import { request } from '../api/client'
import { errorMessage, formatDateTime, formatNumber } from '../utils/format'

const loading = ref(false)
const running = ref(false)
const error = ref('')
const notice = ref('')
const data = ref(null)

const results = computed(() => data.value?.results || [])
const batches = computed(() => data.value?.batches || [])
const passedCount = computed(() => results.value.filter((item) => ['pass', 'passed', 'success', '通过'].includes(String(item.status).toLowerCase())).length)
const failedCount = computed(() => results.value.length - passedCount.value)
const checkedRows = computed(() => results.value.reduce((total, item) => total + (Number(item.checked_rows) || 0), 0))
const failedRows = computed(() => results.value.reduce((total, item) => total + (Number(item.failed_rows) || 0), 0))
const resultColumns = [
  { key: 'rule_name', label: '质量规则', width: '24%' },
  { key: 'status', label: '状态' },
  { key: 'checked_rows', label: '检查行数' },
  { key: 'failed_rows', label: '异常行数' },
  { key: 'duration_ms', label: '耗时' },
  { key: 'details', label: '规则说明', width: '30%' },
]
const batchColumns = [
  { key: 'batch_id', label: '批次编号', width: '25%' },
  { key: 'source_table', label: '源数据表' },
  { key: 'status', label: '状态' },
  { key: 'row_count', label: '数据行数' },
  { key: 'finished_at', label: '完成时间', width: '24%' },
]

function isSuccess(status) {
  return ['pass', 'passed', 'success', 'completed', '通过', '成功', '完成'].includes(String(status).toLowerCase())
}

function statusText(status) {
  if (isSuccess(status)) return '通过'
  if (['fail', 'failed', 'error', '失败'].includes(String(status).toLowerCase())) return '未通过'
  return status || '未知'
}

function detailText(details) {
  if (details === null || details === undefined || details === '') return '—'
  if (typeof details === 'string') return details
  if (Array.isArray(details)) return details.map((item) => typeof item === 'string' ? item : item.message || item.rule || '').filter(Boolean).join('；') || '—'
  if (typeof details === 'object') return Object.entries(details).map(([key, value]) => `${key}：${value}`).join('；')
  return String(details)
}

async function fetchQuality() {
  loading.value = true
  error.value = ''
  try {
    data.value = await request('/quality/latest')
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

async function runQuality() {
  running.value = true
  error.value = ''
  notice.value = ''
  try {
    data.value = await request('/quality/run', { method: 'POST' })
    notice.value = '数据质量检查已完成'
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    running.value = false
  }
}

onMounted(fetchQuality)
</script>

<template>
  <div class="page">
    <PageHeader title="数据质量" description="监控质量规则执行结果与数据批次状态">
      <template #actions><button class="btn" :disabled="loading || running" @click="fetchQuality"><AppIcon name="refresh" :size="15" />刷新</button><button class="btn btn-primary" :disabled="running || loading" @click="runQuality"><span v-if="running" class="spinner" /><AppIcon v-else name="play" :size="15" />{{ running ? '正在检查' : '运行质量检查' }}</button></template>
    </PageHeader>

    <div v-if="error" class="quality-message error"><AppIcon name="alert" :size="16" /><span>{{ error }}</span><button class="btn btn-sm" @click="fetchQuality">重试</button></div>
    <div v-if="notice" class="quality-message success"><AppIcon name="check" :size="16" />{{ notice }}</div>

    <StateBlock v-if="loading && !data" type="loading" class="card" title="正在获取质量检查结果" />

    <template v-else-if="data">
      <div class="quality-overview">
        <section class="card score-card">
          <div class="score-chart"><GaugeChart :value="Number(data.score) || 0" name="综合质量得分" :loading="running" /></div>
          <div class="score-info"><span class="status-badge" :class="failedCount ? 'warning' : 'success'"><span class="status-dot" />{{ failedCount ? '存在待关注项' : '质量状态良好' }}</span><p>最近检查时间<br><strong>{{ formatDateTime(data.generated_at) }}</strong></p></div>
        </section>
        <div class="quality-stats">
          <article class="card quality-stat"><span class="stat-icon blue"><AppIcon name="quality" :size="20" /></span><div><span>质量规则</span><strong>{{ results.length }}<small>项</small></strong><p>{{ passedCount }} 项通过，{{ failedCount }} 项待关注</p></div></article>
          <article class="card quality-stat"><span class="stat-icon teal"><AppIcon name="table" :size="20" /></span><div><span>累计检查数据</span><strong>{{ formatNumber(checkedRows) }}<small>行</small></strong><p>本次规则检查覆盖数据量</p></div></article>
          <article class="card quality-stat"><span class="stat-icon" :class="failedRows ? 'orange' : 'teal'"><AppIcon name="alert" :size="20" /></span><div><span>异常数据</span><strong :class="{ 'text-danger': failedRows }">{{ formatNumber(failedRows) }}<small>行</small></strong><p>所有规则检出的异常行合计</p></div></article>
          <article class="card quality-stat"><span class="stat-icon purple"><AppIcon name="integration" :size="20" /></span><div><span>最近数据批次</span><strong>{{ batches.length }}<small>批</small></strong><p>当前结果关联的数据批次</p></div></article>
        </div>
      </div>

      <section class="card quality-table-card">
        <div class="card-header"><div><h2 class="card-heading">质量规则检查结果</h2><p class="card-subheading">查看每项规则的覆盖范围、异常数据与执行耗时</p></div><span class="status-badge info">{{ results.length }} 项规则</span></div>
        <DataTable :columns="resultColumns" :rows="results" :page-size="8">
          <template #cell-status="{ value }"><span class="status-badge" :class="isSuccess(value) ? 'success' : 'danger'"><span class="status-dot" />{{ statusText(value) }}</span></template>
          <template #cell-failed_rows="{ value }"><strong :class="value ? 'text-danger' : 'text-success'">{{ formatNumber(value) }}</strong></template>
          <template #cell-duration_ms="{ value }">{{ value ?? '—' }} ms</template>
          <template #cell-details="{ value }"><span class="detail-cell" :title="detailText(value)">{{ detailText(value) }}</span></template>
        </DataTable>
      </section>

      <section class="card quality-table-card">
        <div class="card-header"><div><h2 class="card-heading">数据处理批次</h2><p class="card-subheading">最近完成的数据接入与处理记录</p></div></div>
        <DataTable :columns="batchColumns" :rows="batches" :page-size="6">
          <template #cell-batch_id="{ value }"><span class="mono">{{ value }}</span></template>
          <template #cell-source_table="{ value }"><span class="mono">{{ value }}</span></template>
          <template #cell-status="{ value }"><span class="status-badge" :class="isSuccess(value) ? 'success' : 'warning'"><span class="status-dot" />{{ value || '未知' }}</span></template>
          <template #cell-finished_at="{ value }">{{ formatDateTime(value) }}</template>
        </DataTable>
      </section>
    </template>
    <StateBlock v-else class="card" title="暂无质量检查结果" description="点击运行质量检查，生成最新质量报告"><button class="btn btn-primary" @click="runQuality">立即检查</button></StateBlock>
  </div>
</template>

<style scoped>
.quality-message {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding: 10px 13px;
  font-size: 12px;
  border-radius: 7px;
}

.quality-message span {
  flex: 1;
}

.quality-message.error { color: var(--danger); background: var(--danger-soft); }
.quality-message.success { color: var(--success); background: var(--success-soft); }

.quality-overview {
  display: grid;
  grid-template-columns: minmax(280px, 0.75fr) minmax(480px, 1.5fr);
  gap: 18px;
  margin-bottom: 18px;
}

.score-card {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  padding: 20px;
}

.score-chart {
  flex: 0 0 170px;
  width: 170px;
  height: 170px;
}

.score-info {
  min-width: 0;
}

.score-info p {
  margin-top: 16px;
  color: var(--text-muted);
  font-size: 10px;
  line-height: 2;
}

.score-info strong {
  color: #506880;
  font-size: 11px;
  font-weight: 500;
}

.quality-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.quality-stat {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px;
}

.stat-icon {
  display: grid;
  flex: 0 0 42px;
  height: 42px;
  place-items: center;
  color: var(--primary);
  background: var(--primary-soft);
  border-radius: 10px;
}

.stat-icon.teal { color: #168e7d; background: var(--success-soft); }
.stat-icon.orange { color: var(--warning); background: var(--warning-soft); }
.stat-icon.purple { color: #7864cc; background: #f2effc; }

.quality-stat > div {
  display: flex;
  flex-direction: column;
}

.quality-stat span:not(.stat-icon) {
  color: var(--text-secondary);
  font-size: 11px;
}

.quality-stat strong {
  margin-top: 5px;
  color: #246fcf;
  font-size: 24px;
  font-weight: 600;
}

.quality-stat strong small {
  margin-left: 5px;
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 400;
}

.quality-stat p {
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 9px;
}

.quality-table-card {
  margin-bottom: 18px;
  overflow: hidden;
}

.detail-cell {
  display: block;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 1150px) {
  .quality-overview { grid-template-columns: 1fr; }
  .score-card { padding: 15px; }
}

@media (max-width: 640px) {
  .score-card { flex-direction: column; }
  .score-info { text-align: center; }
  .quality-stats { grid-template-columns: 1fr; }
}
</style>
