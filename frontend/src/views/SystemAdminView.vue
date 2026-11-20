<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import DataTable from '../components/DataTable.vue'
import StateBlock from '../components/StateBlock.vue'
import BaseModal from '../components/BaseModal.vue'
import AppIcon from '../components/AppIcon.vue'
import { request } from '../api/client'
import { errorMessage } from '../utils/format'

const tabs = [
  { key: 'users', label: '用户管理', icon: 'user' },
  { key: 'roles', label: '角色权限', icon: 'lock' },
  { key: 'sources', label: '数据源管理', icon: 'integration' },
  { key: 'jobs', label: 'ETL任务管理', icon: 'clock' },
]
const activeTab = ref('users')
const users = ref([])
const roles = ref([])
const sources = ref([])
const jobs = ref([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')
const modalOpen = ref(false)
const modalMode = ref('create')
const form = reactive({})

const userColumns = [
  { key: 'username', label: '用户名' },
  { key: 'display_name', label: '显示名称' },
  { key: 'role', label: '角色' },
  { key: 'dept_codes', label: '科室范围' },
  { key: 'enabled', label: '状态' },
  { key: 'actions', label: '操作', width: '170px' },
]
const sourceColumns = [
  { key: 'name', label: '名称' },
  { key: 'kind', label: '类型' },
  { key: 'path', label: '路径' },
  { key: 'enabled', label: '状态' },
  { key: 'actions', label: '操作', width: '210px' },
]
const jobColumns = [
  { key: 'name', label: '任务名称' },
  { key: 'source_table', label: '源表' },
  { key: 'schedule', label: '调度表达式' },
  { key: 'retry_limit', label: '重试上限' },
  { key: 'enabled', label: '状态' },
  { key: 'actions', label: '操作', width: '210px' },
]
const sourceOptions = [
  ['his_outpatient', 'HIS门诊'], ['his_inpatient', 'HIS住院'], ['his_charge', 'HIS收费'],
  ['emr_record', 'EMR'], ['lis_report', 'LIS'], ['finance_excel', '财务'],
]
const currentRows = computed(() => activeTab.value === 'users' ? users.value : activeTab.value === 'sources' ? sources.value : activeTab.value === 'jobs' ? jobs.value : [])

async function fetchAll() {
  loading.value = true
  error.value = ''
  try {
    const [userData, roleData, sourceData, jobData] = await Promise.all([
      request('/users'), request('/roles'), request('/data-sources'), request('/etl/jobs'),
    ])
    users.value = userData || []
    roles.value = roleData || []
    sources.value = (sourceData || []).map((item) => ({ ...item, path: item.config?.path || '' }))
    jobs.value = jobData || []
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  modalMode.value = 'create'
  Object.keys(form).forEach((key) => delete form[key])
  if (activeTab.value === 'users') Object.assign(form, { username: '', display_name: '', password: '', role: 'analyst', dept_codes: '', enabled: true })
  if (activeTab.value === 'sources') Object.assign(form, { name: '', kind: 'csv', path: '', enabled: true })
  if (activeTab.value === 'jobs') Object.assign(form, { name: '', source_table: 'his_outpatient', schedule: '0 2 * * *', retry_limit: 3, enabled: true })
  modalOpen.value = true
}

function openEdit(row) {
  modalMode.value = 'edit'
  Object.keys(form).forEach((key) => delete form[key])
  if (activeTab.value === 'users') Object.assign(form, { username: row.username, display_name: row.display_name, password: '', role: row.role, dept_codes: (row.dept_codes || []).join(','), enabled: row.enabled })
  if (activeTab.value === 'sources') Object.assign(form, { id: row.id, name: row.name, kind: row.kind, path: row.path, enabled: row.enabled })
  if (activeTab.value === 'jobs') Object.assign(form, { id: row.id, name: row.name, source_table: row.source_table, schedule: row.schedule, retry_limit: row.retry_limit, enabled: row.enabled })
  modalOpen.value = true
}

async function submitForm() {
  saving.value = true
  error.value = ''
  try {
    if (activeTab.value === 'users') {
      if (modalMode.value === 'create') {
        await request('/users', { method: 'POST', body: { username: form.username, display_name: form.display_name, password: form.password, role: form.role, dept_codes: form.dept_codes.split(',').map((item) => item.trim()).filter(Boolean) } })
      } else {
        const body = { display_name: form.display_name, role: form.role, dept_codes: form.dept_codes.split(',').map((item) => item.trim()).filter(Boolean), enabled: form.enabled }
        if (form.password) body.password = form.password
        await request(`/users/${encodeURIComponent(form.username)}`, { method: 'PUT', body })
      }
    } else if (activeTab.value === 'sources') {
      const body = { name: form.name, kind: form.kind, path: form.path, enabled: form.enabled }
      if (modalMode.value === 'create') await request('/data-sources', { method: 'POST', body })
      else await request(`/data-sources/${form.id}`, { method: 'PUT', body })
    } else if (activeTab.value === 'jobs') {
      if (modalMode.value === 'create') {
        await request('/etl/jobs', { method: 'POST', body: { name: form.name, source_table: form.source_table, schedule: form.schedule, enabled: form.enabled, retry_limit: Number(form.retry_limit) } })
      } else {
        await request(`/etl/jobs/${form.id}`, { method: 'PUT', body: { name: form.name, schedule: form.schedule, enabled: form.enabled, retry_limit: Number(form.retry_limit) } })
      }
    }
    modalOpen.value = false
    notice.value = modalMode.value === 'create' ? '创建成功' : '更新成功'
    await fetchAll()
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    saving.value = false
  }
}

async function removeRow(row) {
  const name = row.display_name || row.name || row.username || row.id
  if (!window.confirm(`确认删除“${name}”吗？`)) return
  try {
    if (activeTab.value === 'users') await request(`/users/${encodeURIComponent(row.username)}`, { method: 'DELETE' })
    if (activeTab.value === 'sources') await request(`/data-sources/${row.id}`, { method: 'DELETE' })
    if (activeTab.value === 'jobs') await request(`/etl/jobs/${row.id}`, { method: 'DELETE' })
    notice.value = '删除成功'
    await fetchAll()
  } catch (err) {
    error.value = errorMessage(err)
  }
}

async function testSource(row) {
  try {
    const result = await request(`/data-sources/${row.id}/test`, { method: 'POST' })
    notice.value = result.connected ? `连接成功：${result.message}` : `连接失败：${result.message}`
  } catch (err) {
    error.value = errorMessage(err)
  }
}

async function runJob(row) {
  try {
    const result = await request(`/etl/jobs/${row.id}/run`, { method: 'POST' })
    notice.value = `${row.name}执行完成，处理 ${result.row_count} 行`
    await fetchAll()
  } catch (err) {
    error.value = errorMessage(err)
  }
}

onMounted(fetchAll)
</script>

<template>
  <div class="page">
    <PageHeader title="系统管理" description="维护用户、角色、数据源与ETL任务">
      <template #actions>
        <button class="btn" :disabled="loading" @click="fetchAll"><AppIcon name="refresh" :size="15" />刷新</button>
        <button v-if="activeTab !== 'roles'" class="btn btn-primary" @click="openCreate"><AppIcon name="plus" :size="15" />新增</button>
      </template>
    </PageHeader>

    <div class="admin-tabs card">
      <button v-for="tab in tabs" :key="tab.key" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">
        <AppIcon :name="tab.icon" :size="16" />{{ tab.label }}
      </button>
    </div>

    <div v-if="error" class="admin-message error"><AppIcon name="alert" :size="16" /><span>{{ error }}</span></div>
    <div v-if="notice" class="admin-message success"><AppIcon name="check" :size="16" /><span>{{ notice }}</span></div>

    <section v-if="activeTab === 'roles'" class="role-grid">
      <article v-for="role in roles" :key="role.code" class="card role-card">
        <div class="role-icon"><AppIcon name="lock" :size="19" /></div>
        <h3>{{ role.name }}</h3>
        <code>{{ role.code }}</code>
        <p>{{ role.description }}</p>
        <span class="status-badge" :class="role.department_scoped ? 'warning' : 'info'">{{ role.department_scoped ? '科室隔离' : '全院范围' }}</span>
      </article>
    </section>

    <section v-else class="card admin-table">
      <StateBlock v-if="loading && !currentRows.length" type="loading" compact title="正在加载系统配置" />
      <DataTable v-else :columns="activeTab === 'users' ? userColumns : activeTab === 'sources' ? sourceColumns : jobColumns" :rows="currentRows" :loading="loading" :page-size="10">
        <template #cell-role="{ value }">{{ roles.find((item) => item.code === value)?.name || value }}</template>
        <template #cell-dept_codes="{ value }">{{ value?.length ? value.join('、') : '全院' }}</template>
        <template #cell-enabled="{ value }"><span class="status-badge" :class="value ? 'success' : 'warning'"><span class="status-dot" />{{ value ? '启用' : '停用' }}</span></template>
        <template #cell-actions="{ row }">
          <div class="row-actions">
            <button v-if="activeTab === 'sources'" class="btn btn-sm" @click="testSource(row)">测试</button>
            <button v-if="activeTab === 'jobs'" class="btn btn-sm" @click="runJob(row)">执行</button>
            <button class="btn btn-sm" @click="openEdit(row)">编辑</button>
            <button class="btn btn-sm danger-text" @click="removeRow(row)">删除</button>
          </div>
        </template>
      </DataTable>
    </section>

    <BaseModal :open="modalOpen" :title="modalMode === 'create' ? '新增配置' : '编辑配置'" @close="modalOpen = false">
      <div class="admin-form">
        <template v-if="activeTab === 'users'">
          <label>用户名<input v-model="form.username" class="form-control" :disabled="modalMode === 'edit'"></label>
          <label>显示名称<input v-model="form.display_name" class="form-control"></label>
          <label>密码<input v-model="form.password" type="password" class="form-control" :placeholder="modalMode === 'edit' ? '留空表示不修改' : '至少8位'"></label>
          <label>角色<select v-model="form.role" class="form-control"><option v-for="role in roles" :key="role.code" :value="role.code">{{ role.name }}</option></select></label>
          <label>科室编码<input v-model="form.dept_codes" class="form-control" placeholder="HN,HX；留空为全院"></label>
          <label v-if="modalMode === 'edit'" class="check-row"><input v-model="form.enabled" type="checkbox">启用该用户</label>
        </template>
        <template v-else-if="activeTab === 'sources'">
          <label>名称<input v-model="form.name" class="form-control"></label>
          <label>类型<select v-model="form.kind" class="form-control"><option value="csv">CSV</option><option value="excel">Excel</option><option value="mysql">MySQL</option><option value="oracle">Oracle</option><option value="sqlserver">SQL Server</option><option value="api">API</option></select></label>
          <label>路径<input v-model="form.path" class="form-control" placeholder="mock_his/his_outpatient.csv"></label>
          <label class="check-row"><input v-model="form.enabled" type="checkbox">启用该数据源</label>
        </template>
        <template v-else>
          <label>任务名称<input v-model="form.name" class="form-control"></label>
          <label>源数据表<select v-model="form.source_table" class="form-control" :disabled="modalMode === 'edit'"><option v-for="item in sourceOptions" :key="item[0]" :value="item[0]">{{ item[1] }}（{{ item[0] }}）</option></select></label>
          <label>调度表达式<input v-model="form.schedule" class="form-control" placeholder="0 2 * * *"></label>
          <label>重试上限<input v-model.number="form.retry_limit" type="number" min="0" max="10" class="form-control"></label>
          <label class="check-row"><input v-model="form.enabled" type="checkbox">启用该任务</label>
        </template>
      </div>
      <template #footer>
        <button class="btn" @click="modalOpen = false">取消</button>
        <button class="btn btn-primary" :disabled="saving" @click="submitForm"><span v-if="saving" class="spinner" />保存</button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.admin-tabs { display: flex; gap: 4px; margin-bottom: 16px; padding: 7px; }
.admin-tabs button { display: flex; align-items: center; gap: 7px; padding: 9px 14px; color: var(--text-secondary); font-size: 12px; background: transparent; border-radius: 7px; }
.admin-tabs button.active { color: var(--primary); background: var(--primary-soft); font-weight: 600; }
.admin-message { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; padding: 10px 13px; font-size: 12px; border-radius: 7px; }
.admin-message.error { color: var(--danger); background: var(--danger-soft); }
.admin-message.success { color: var(--success); background: var(--success-soft); }
.admin-table { overflow: hidden; }
.row-actions { display: flex; gap: 5px; }
.danger-text { color: var(--danger); }
.role-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.role-card { padding: 20px; }
.role-icon { display: grid; width: 38px; height: 38px; place-items: center; color: var(--primary); background: var(--primary-soft); border-radius: 9px; }
.role-card h3 { margin-top: 14px; color: var(--text); font-size: 16px; }
.role-card code { display: inline-block; margin-top: 5px; color: var(--text-muted); font-size: 11px; }
.role-card p { min-height: 58px; margin: 12px 0; color: var(--text-secondary); font-size: 12px; line-height: 1.6; }
.admin-form { display: flex; flex-direction: column; gap: 14px; padding: 4px 0; }
.admin-form label { display: flex; flex-direction: column; gap: 7px; color: var(--text-secondary); font-size: 12px; }
.admin-form .check-row { flex-direction: row; align-items: center; }
@media (max-width: 900px) { .role-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 640px) { .role-grid { grid-template-columns: 1fr; } .admin-tabs { overflow-x: auto; } }
</style>
