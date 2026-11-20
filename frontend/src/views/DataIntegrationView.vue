<script setup>
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import DataTable from '../components/DataTable.vue'
import StateBlock from '../components/StateBlock.vue'
import ImportDialog from '../components/ImportDialog.vue'
import AppIcon from '../components/AppIcon.vue'
import { request } from '../api/client'
import { errorMessage, formatDateTime, formatNumber } from '../utils/format'

const jobs = ref([])
const loading = ref(false)
const error = ref('')
const notice = ref('')
const importOpen = ref(false)
const refreshingAds = ref(false)
const runningIds = ref(new Set())

const enabledCount = computed(() => jobs.value.filter((job) => job.enabled).length)
const successCount = computed(() => jobs.value.filter((job) => isSuccess(job.last_status)).length)
const sourceCount = computed(() => new Set(jobs.value.map((job) => job.source_table).filter(Boolean)).size)
const columns = [
  { key: 'name', label: '任务名称', width: '20%' },
  { key: 'source_table', label: '源数据表' },
  { key: 'schedule', label: '调度周期' },
  { key: 'enabled', label: '任务状态' },
  { key: 'last_status', label: '最近执行' },
  { key: 'last_run', label: '最近执行时间', width: '20%' },
  { key: 'actions', label: '操作' },
]

function isSuccess(status) {
  return ['success', 'succeeded', 'completed', '成功', '完成'].includes(String(status).toLowerCase())
}

function statusClass(status) {
  if (isSuccess(status)) return 'success'
  if (['failed', 'error', '失败'].includes(String(status).toLowerCase())) return 'danger'
  return 'warning'
}

async function fetchJobs() {
  loading.value = true
  error.value = ''
  try {
    const data = await request('/etl/jobs')
    jobs.value = Array.isArray(data) ? data : []
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

function setRunning(id, value) {
  const next = new Set(runningIds.value)
  if (value) next.add(id)
  else next.delete(id)
  runningIds.value = next
}

async function runJob(job) {
  if (runningIds.value.has(job.id)) return
  setRunning(job.id, true)
  error.value = ''
  notice.value = ''
  try {
    const result = await request(`/etl/jobs/${encodeURIComponent(job.id)}/run`, { method: 'POST' })
    notice.value = `${job.name}执行完成，处理 ${formatNumber(result?.row_count ?? 0)} 行数据`
    await fetchJobs()
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    setRunning(job.id, false)
  }
}

async function refreshAds() {
  refreshingAds.value = true
  error.value = ''
  notice.value = ''
  try {
    const result = await request('/etl/ads/refresh', {
      method: 'POST',
      body: { grains: ['day', 'week', 'month'] },
    })
    const rows = Object.values(result || {}).reduce((sum, item) => sum + (item?.rows || 0), 0)
    notice.value = `ADS 日/周/月结果回刷完成，共重算 ${formatNumber(rows)} 行`
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    refreshingAds.value = false
  }
}

function onImported(result) {
  notice.value = `数据文件已接入 ${result?.source_table || '目标数据表'}，共处理 ${formatNumber(result?.row_count ?? 0)} 行`
  fetchJobs()
}

onMounted(fetchJobs)
</script>

<template>
  <div class="page">
    <PageHeader title="数据接入与任务" description="接入业务数据文件，管理数据同步任务">
      <template #actions><button class="btn" :disabled="refreshingAds" @click="refreshAds"><span v-if="refreshingAds" class="spinner" /><AppIcon v-else name="refresh" :size="15" />{{ refreshingAds ? '回刷中' : '回刷ADS' }}</button><button class="btn" :disabled="loading" @click="fetchJobs"><AppIcon name="refresh" :size="15" />刷新任务</button><button class="btn btn-primary" @click="importOpen = true"><AppIcon name="upload" :size="15" />导入数据文件</button></template>
    </PageHeader>

    <div v-if="error" class="integration-message error"><AppIcon name="alert" :size="16" /><span>{{ error }}</span><button class="btn btn-sm" @click="fetchJobs">重试</button></div>
    <div v-if="notice" class="integration-message success"><AppIcon name="check" :size="16" />{{ notice }}<button class="message-close" aria-label="关闭提示" @click="notice = ''"><AppIcon name="close" :size="14" /></button></div>

    <section class="card import-banner">
      <div class="banner-icon"><AppIcon name="integration" :size="26" /></div>
      <div class="banner-copy"><h2>业务数据快速接入</h2><p>上传 CSV 或 Excel 文件，自动识别目标数据表并完成格式校验与数据导入。</p></div>
      <div class="file-types"><span>CSV</span><span>XLSX</span><span>XLSM</span></div>
      <button class="btn" @click="importOpen = true">选择文件<AppIcon name="arrowRight" :size="15" /></button>
    </section>

    <div class="integration-stats">
      <article class="card"><span class="stat-icon"><AppIcon name="integration" :size="20" /></span><div><p>同步任务</p><strong>{{ jobs.length }}<small>个</small></strong></div></article>
      <article class="card"><span class="stat-icon teal"><AppIcon name="check" :size="20" /></span><div><p>已启用任务</p><strong>{{ enabledCount }}<small>个</small></strong></div></article>
      <article class="card"><span class="stat-icon orange"><AppIcon name="clock" :size="20" /></span><div><p>最近执行成功</p><strong>{{ successCount }}<small>个</small></strong></div></article>
      <article class="card"><span class="stat-icon purple"><AppIcon name="table" :size="20" /></span><div><p>接入源表</p><strong>{{ sourceCount }}<small>张</small></strong></div></article>
    </div>

    <section class="card jobs-card">
      <div class="card-header">
        <div><h2 class="card-heading">数据同步任务</h2><p class="card-subheading">查看调度配置与执行状态，或手动运行指定任务</p></div>
        <span class="status-badge info">{{ jobs.length }} 个任务</span>
      </div>
      <StateBlock v-if="error && !jobs.length" type="error" :description="error" @retry="fetchJobs" />
      <DataTable v-else :columns="columns" :rows="jobs" :loading="loading" :page-size="8" empty-text="暂无数据同步任务">
        <template #cell-name="{ row }"><div class="job-name"><span><AppIcon name="refresh" :size="15" /></span><div><strong>{{ row.name }}</strong><small>任务 ID：{{ row.id }}</small></div></div></template>
        <template #cell-source_table="{ value }"><span class="mono table-name">{{ value || '—' }}</span></template>
        <template #cell-schedule="{ value }"><span class="schedule-cell"><AppIcon name="clock" :size="13" />{{ value || '—' }}</span></template>
        <template #cell-enabled="{ value }"><span class="status-badge" :class="value ? 'success' : ''"><span class="status-dot" />{{ value ? '已启用' : '已停用' }}</span></template>
        <template #cell-last_status="{ value }"><span class="status-badge" :class="statusClass(value)">{{ value || '未执行' }}</span></template>
        <template #cell-last_run="{ value }">{{ formatDateTime(value) }}</template>
        <template #cell-actions="{ row }"><button class="btn btn-sm" :disabled="runningIds.has(row.id) || !row.enabled" @click="runJob(row)"><span v-if="runningIds.has(row.id)" class="spinner" /><AppIcon v-else name="play" :size="13" />{{ runningIds.has(row.id) ? '执行中' : '立即执行' }}</button></template>
      </DataTable>
    </section>

    <ImportDialog :open="importOpen" @close="importOpen = false" @success="onImported" />
  </div>
</template>

<style scoped>
.integration-message {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding: 10px 13px;
  font-size: 12px;
  border-radius: 7px;
}

.integration-message span { flex: 1; }
.integration-message.error { color: var(--danger); background: var(--danger-soft); }
.integration-message.success { color: var(--success); background: var(--success-soft); }
.message-close { padding: 4px; color: inherit; background: transparent; }

.import-banner {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 16px;
  padding: 19px 21px;
  background: #f8fbff;
  border-color: #dce9f8;
}

.banner-icon {
  display: grid;
  flex: 0 0 48px;
  height: 48px;
  place-items: center;
  color: var(--primary);
  background: #e7f0fd;
  border-radius: 11px;
}

.banner-copy { flex: 1; }
.banner-copy h2 { color: #2c4968; font-size: 14px; font-weight: 600; }
.banner-copy p { margin-top: 6px; color: #748ba5; font-size: 11px; line-height: 1.6; }
.file-types { display: flex; gap: 5px; }
.file-types span { padding: 5px 7px; color: #6d88a6; font-size: 10px; background: #fff; border: 1px solid #dce6f1; border-radius: 5px; }

.integration-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.integration-stats article {
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 16px 18px;
}

.stat-icon {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  color: var(--primary);
  background: var(--primary-soft);
  border-radius: 9px;
}

.stat-icon.teal { color: #168e7d; background: var(--success-soft); }
.stat-icon.orange { color: var(--warning); background: var(--warning-soft); }
.stat-icon.purple { color: #7864cc; background: #f2effc; }
.integration-stats p { color: var(--text-secondary); font-size: 11px; }
.integration-stats strong { display: block; margin-top: 5px; color: #246fcf; font-size: 23px; font-weight: 600; }
.integration-stats small { margin-left: 5px; color: var(--text-muted); font-size: 11px; font-weight: 400; }

.jobs-card { overflow: hidden; }
.job-name { display: flex; align-items: center; gap: 9px; }
.job-name > span { display: grid; width: 30px; height: 30px; place-items: center; color: var(--primary); background: var(--primary-soft); border-radius: 7px; }
.job-name > div { display: flex; flex-direction: column; gap: 4px; }
.job-name strong { color: #3a526d; font-size: 12px; font-weight: 550; }
.job-name small { color: var(--text-muted); font-size: 10px; }
.table-name { padding: 4px 7px; color: #56728f; font-size: 11px; background: #f3f6f9; border-radius: 4px; }
.schedule-cell { display: flex; align-items: center; gap: 5px; color: #667e96; }
.integration-message .spinner,
.jobs-card .spinner { width: 13px; height: 13px; }

@media (max-width: 1050px) {
  .integration-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .file-types { display: none; }
}

@media (max-width: 640px) {
  .import-banner { align-items: flex-start; flex-wrap: wrap; }
  .banner-copy { min-width: calc(100% - 70px); }
  .import-banner > .btn { margin-left: auto; }
  .integration-stats { grid-template-columns: 1fr; }
}
</style>
