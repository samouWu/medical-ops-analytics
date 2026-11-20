<script setup>
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import DataTable from '../components/DataTable.vue'
import AppIcon from '../components/AppIcon.vue'
import { request } from '../api/client'
import { errorMessage, formatDateTime } from '../utils/format'

const logs = ref([])
const loading = ref(false)
const error = ref('')
const keyword = ref('')
const action = ref('')

const actions = computed(() => [...new Set(logs.value.map((log) => log.action).filter(Boolean))])
const filteredLogs = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  return logs.value.filter((log) => {
    const matchesKeyword = !query || `${log.username}${log.resource}${log.trace_id}${detailText(log.detail)}`.toLowerCase().includes(query)
    return matchesKeyword && (!action.value || log.action === action.value)
  })
})
const userCount = computed(() => new Set(filteredLogs.value.map((log) => log.username).filter(Boolean)).size)
const columns = [
  { key: 'created_at', label: '操作时间', width: '19%' },
  { key: 'username', label: '操作用户' },
  { key: 'action', label: '操作类型' },
  { key: 'resource', label: '访问资源', width: '21%' },
  { key: 'detail', label: '操作详情', width: '27%' },
  { key: 'trace_id', label: '追踪编号', width: '20%' },
]

function detailText(detail) {
  if (detail === null || detail === undefined || detail === '') return '—'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map(String).join('；')
  if (typeof detail === 'object') return Object.entries(detail).map(([key, value]) => `${key}：${typeof value === 'object' ? '[复合字段]' : value}`).join('；')
  return String(detail)
}

function actionClass(actionName) {
  const value = String(actionName).toLowerCase()
  if (/delete|remove|fail|删除|失败/.test(value)) return 'danger'
  if (/login|auth|登录/.test(value)) return 'info'
  if (/export|download|导出|下载/.test(value)) return 'warning'
  return 'success'
}

async function fetchLogs() {
  loading.value = true
  error.value = ''
  try {
    const data = await request('/audit/logs')
    logs.value = Array.isArray(data) ? data : []
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

onMounted(fetchLogs)
</script>

<template>
  <div class="page">
    <PageHeader title="系统审计" description="追踪系统操作行为与关键数据访问记录">
      <template #actions><button class="btn" :disabled="loading" @click="fetchLogs"><AppIcon name="refresh" :size="15" />刷新日志</button></template>
    </PageHeader>

    <div class="audit-summary">
      <section class="card audit-intro"><span class="audit-shield"><AppIcon name="audit" :size="26" /></span><div><h2>操作留痕，安全可溯</h2><p>记录平台登录、查询、导入、导出与任务执行等关键操作</p></div></section>
      <article class="card audit-stat"><span>当前日志</span><strong>{{ filteredLogs.length }}<small>条</small></strong></article>
      <article class="card audit-stat"><span>涉及用户</span><strong>{{ userCount }}<small>人</small></strong></article>
    </div>

    <section class="card audit-card">
      <div class="audit-toolbar">
        <div><h2 class="card-heading">审计日志</h2><p class="card-subheading">按用户、资源或追踪编号检索操作记录</p></div>
        <div class="audit-filters">
          <div class="audit-search"><AppIcon name="search" :size="15" /><input v-model="keyword" placeholder="搜索用户、资源或追踪编号"></div>
          <select v-model="action" class="form-control" aria-label="操作类型"><option value="">全部操作</option><option v-for="item in actions" :key="item" :value="item">{{ item }}</option></select>
          <button v-if="keyword || action" class="btn btn-text" @click="keyword = ''; action = ''">清除筛选</button>
        </div>
      </div>
      <DataTable :columns="columns" :rows="filteredLogs" :loading="loading" :error="error" :page-size="12" empty-text="暂无匹配的审计日志" @retry="fetchLogs">
        <template #cell-created_at="{ value }"><span class="time-cell"><AppIcon name="clock" :size="13" />{{ formatDateTime(value) }}</span></template>
        <template #cell-username="{ value }"><span class="user-cell"><span>{{ String(value || '系').slice(0, 1) }}</span>{{ value || '系统' }}</span></template>
        <template #cell-action="{ value }"><span class="status-badge" :class="actionClass(value)">{{ value || '—' }}</span></template>
        <template #cell-resource="{ value }"><span class="mono resource-cell" :title="value">{{ value || '—' }}</span></template>
        <template #cell-detail="{ value }"><span class="detail-cell" :title="detailText(value)">{{ detailText(value) }}</span></template>
        <template #cell-trace_id="{ value }"><span class="mono trace-cell" :title="value">{{ value || '—' }}</span></template>
      </DataTable>
    </section>
  </div>
</template>

<style scoped>
.audit-summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 180px 180px;
  gap: 14px;
  margin-bottom: 18px;
}

.audit-intro {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 17px 20px;
}

.audit-shield {
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  color: var(--primary);
  background: var(--primary-soft);
  border-radius: 10px;
}

.audit-intro h2 { color: #324d68; font-size: 14px; font-weight: 600; }
.audit-intro p { margin-top: 6px; color: var(--text-muted); font-size: 11px; }
.audit-stat { display: flex; align-items: center; justify-content: space-between; padding: 18px; }
.audit-stat > span { color: var(--text-secondary); font-size: 11px; }
.audit-stat strong { color: #246fcf; font-size: 25px; font-weight: 600; }
.audit-stat small { margin-left: 4px; color: var(--text-muted); font-size: 11px; font-weight: 400; }

.audit-card { overflow: hidden; }
.audit-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 16px 20px; border-bottom: 1px solid var(--border); }
.audit-filters { display: flex; align-items: center; gap: 8px; }
.audit-search { display: flex; align-items: center; gap: 7px; width: 245px; height: 36px; padding: 0 10px; color: var(--text-muted); border: 1px solid #dfe6ee; border-radius: 7px; }
.audit-search input { width: 100%; min-width: 0; font-size: 11px; border: 0; outline: 0; }
.audit-filters .form-control { width: 125px; height: 36px; font-size: 11px; }
.time-cell { display: flex; align-items: center; gap: 5px; color: #6c8299; }
.user-cell { display: flex; align-items: center; gap: 7px; }
.user-cell > span { display: grid; width: 25px; height: 25px; place-items: center; color: #3978bd; font-size: 11px; background: #eaf2fb; border-radius: 50%; }
.resource-cell { display: block; max-width: 220px; overflow: hidden; color: #4e6a88; font-size: 11px; text-overflow: ellipsis; }
.detail-cell { display: block; max-width: 310px; overflow: hidden; text-overflow: ellipsis; }
.trace-cell { display: block; max-width: 190px; overflow: hidden; color: #8496aa; font-size: 11px; text-overflow: ellipsis; }

@media (max-width: 1100px) {
  .audit-summary { grid-template-columns: 1fr 150px 150px; }
  .audit-toolbar { align-items: flex-start; flex-direction: column; }
  .audit-filters { width: 100%; }
  .audit-search { flex: 1; }
}

@media (max-width: 640px) {
  .audit-summary { grid-template-columns: 1fr 1fr; }
  .audit-intro { grid-column: 1 / -1; }
  .audit-filters { flex-wrap: wrap; }
  .audit-search { flex-basis: 100%; width: 100%; }
}
</style>
