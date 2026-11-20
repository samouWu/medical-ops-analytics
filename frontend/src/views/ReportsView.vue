<script setup>
import { computed, onMounted, ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import AppIcon from '../components/AppIcon.vue'
import StateBlock from '../components/StateBlock.vue'
import DatePicker from '../components/DatePicker.vue'
import { request } from '../api/client'
import { appState, loadMeta } from '../stores/app'
import { errorMessage, formatDateTime } from '../utils/format'

const period = ref('month')
const date = ref('')
const loading = ref(false)
const error = ref('')
const report = ref(null)

const maxDate = computed(() => appState.meta.date_range.max || '')
const minDate = computed(() => appState.meta.date_range.min || '')

function setDefaultDate() {
  if (period.value === 'month') date.value = (maxDate.value || new Date().toISOString().slice(0, 10)).slice(0, 7)
  else date.value = maxDate.value || new Date().toISOString().slice(0, 10)
}

function changePeriod(value) {
  period.value = value
  report.value = null
  error.value = ''
  setDefaultDate()
}

function paragraphs(content) {
  if (Array.isArray(content)) return content.map(String)
  if (content === null || content === undefined) return []
  return String(content).split(/\n+/).map((item) => item.trim()).filter(Boolean)
}

function evidenceText(section) {
  const evidence = section?.evidence
  if (!evidence) return ''
  if (Array.isArray(evidence)) return evidence.map((item) => item.title || item.code).filter(Boolean).join('；')
  const parts = []
  if (evidence.metrics?.length) parts.push('指标：'+evidence.metrics.join('、'))
  if (evidence.period) parts.push('期间：'+evidence.period.join(' 至 '))
  if (evidence.source) parts.push('来源：'+evidence.source)
  if (evidence.thresholds) parts.push('阈值：'+Object.entries(evidence.thresholds).map(([key, value]) => `${key}=${value}`).join('，'))
  return parts.join('；')
}

function printReport() {
  window.print()
}

async function generate() {
  if (!date.value) {
    error.value = '请选择报告周期'
    return
  }
  loading.value = true
  error.value = ''
  try {
    report.value = await request('/reports/generate', {
      method: 'POST',
      body: { period: period.value, date: date.value },
    })
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadMeta()
  setDefaultDate()
  if (date.value) generate()
})
</script>

<template>
  <div class="page report-page">
    <PageHeader title="报告生成" description="基于运营数据生成结构化周期分析报告">
      <template #actions><button v-if="report" class="btn" @click="printReport"><AppIcon name="download" :size="15" />打印 / 保存 PDF</button></template>
    </PageHeader>

    <section class="card report-controls">
      <div class="control-intro"><span><AppIcon name="report" :size="21" /></span><div><h2>运营分析报告</h2><p>选择报告周期，系统将自动汇总并生成分析内容</p></div></div>
      <div class="control-fields">
        <div class="control-field"><label>报告类型</label><div class="segmented"><button :class="{ active: period === 'month' }" @click="changePeriod('month')">月度报告</button><button :class="{ active: period === 'week' }" @click="changePeriod('week')">周度报告</button></div></div>
        <label class="control-field"><span>统计周期</span><DatePicker v-model="date" :mode="period === 'month' ? 'month' : 'date'" :min="period === 'month' ? minDate.slice(0, 7) : minDate" :max="period === 'month' ? maxDate.slice(0, 7) : maxDate" /></label>
        <button class="btn btn-primary" :disabled="loading || !date" @click="generate"><span v-if="loading" class="spinner" /><AppIcon v-else name="report" :size="15" />{{ loading ? '正在生成' : '生成报告' }}</button>
      </div>
    </section>

    <div v-if="error" class="report-error"><AppIcon name="alert" :size="17" /><span>{{ error }}</span><button class="btn btn-sm" @click="generate">重试</button></div>

    <div v-if="loading" class="report-loading card">
      <div class="skeleton" style="width: 45%; height: 28px; margin: 35px auto 15px" />
      <div class="skeleton" style="width: 25%; height: 12px; margin: 0 auto 40px" />
      <div v-for="i in 3" :key="i" class="loading-section"><div class="skeleton" style="width: 25%; height: 18px" /><div class="skeleton" style="width: 100%; height: 12px; margin-top: 18px" /><div class="skeleton" style="width: 88%; height: 12px; margin-top: 12px" /></div>
    </div>

    <article v-else-if="report" class="report-document card">
      <header class="report-cover">
        <div class="report-brand"><AppIcon name="health" :size="17" /><span>医疗运营洞察</span></div>
        <div class="report-label">{{ period === 'month' ? 'MONTHLY OPERATIONS REPORT' : 'WEEKLY OPERATIONS REPORT' }}</div>
        <h1>{{ report.title }}</h1>
        <div class="report-period"><AppIcon name="calendar" :size="16" /><span>{{ report.period?.start }} 至 {{ report.period?.end }}</span></div>
        <div class="report-generated">生成时间：{{ formatDateTime(report.generated_at) }}</div>
      </header>
      <div class="report-sections">
        <section v-for="(section, index) in report.sections || []" :key="`${section.title}-${index}`" class="report-section">
          <div class="section-number">{{ String(index + 1).padStart(2, '0') }}</div>
          <div class="section-content"><h2>{{ section.title }}</h2><p v-for="(paragraph, pIndex) in paragraphs(section.content)" :key="pIndex">{{ paragraph }}</p><p v-if="evidenceText(section)" class="section-evidence">口径证据：{{ evidenceText(section) }}</p><p v-if="!paragraphs(section.content).length" class="text-muted">本章节暂无分析内容。</p></div>
        </section>
        <StateBlock v-if="!report.sections?.length" compact title="报告暂无章节内容" />
      </div>
      <footer class="report-footer"><span>医疗运营数据主题分析平台</span><span>本报告由系统基于当前数据自动生成</span></footer>
    </article>

    <StateBlock v-else class="card" title="生成您的运营分析报告" description="选择月度或周度周期，点击生成报告查看结构化分析" />
  </div>
</template>

<style scoped>
.report-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
  padding: 17px 20px;
}

.control-intro {
  display: flex;
  align-items: center;
  gap: 12px;
}

.control-intro > span {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  color: var(--primary);
  background: var(--primary-soft);
  border-radius: 9px;
}

.control-intro h2 {
  color: var(--text);
  font-size: 14px;
  font-weight: 600;
}

.control-intro p {
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 11px;
}

.control-fields,
.control-field {
  display: flex;
  align-items: flex-end;
  gap: 12px;
}

.control-field {
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}

.control-field > label,
.control-field > span {
  color: var(--text-muted);
  font-size: 11px;
}

.control-field .form-control {
  width: 160px;
}

.report-error {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 18px;
  padding: 11px 14px;
  color: var(--danger);
  font-size: 12px;
  background: var(--danger-soft);
  border-radius: 8px;
}

.report-error span {
  flex: 1;
}

.report-document {
  max-width: 1000px;
  margin: 0 auto;
  overflow: hidden;
}

.report-cover {
  position: relative;
  padding: 32px 50px 37px;
  text-align: center;
  background: #fbfcfe;
  border-bottom: 1px solid var(--border);
}

.report-brand {
  position: absolute;
  top: 22px;
  left: 25px;
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--navy);
  font-size: 11px;
  font-weight: 600;
}

.report-brand svg {
  color: var(--primary);
}

.report-label {
  margin-top: 18px;
  color: #86a0bd;
  font-size: 10px;
  letter-spacing: 2px;
}

.report-cover h1 {
  margin-top: 17px;
  color: #183550;
  font-size: 27px;
  font-weight: 600;
  letter-spacing: 1px;
}

.report-period {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  margin-top: 20px;
  color: #56708b;
  font-size: 12px;
}

.report-period svg {
  color: var(--primary);
}

.report-generated {
  margin-top: 10px;
  color: #9aa9b9;
  font-size: 11px;
}

.report-sections {
  padding: 15px 50px 30px;
}

.report-section {
  display: flex;
  gap: 22px;
  padding: 28px 0;
  border-bottom: 1px solid var(--border);
}

.report-section:last-of-type {
  border-bottom: 0;
}

.section-number {
  flex: 0 0 36px;
  padding-top: 2px;
  color: #a3bad4;
  font-family: Georgia, serif;
  font-size: 22px;
}

.section-content {
  flex: 1;
}

.section-content h2 {
  margin-bottom: 13px;
  color: #263f59;
  font-size: 17px;
  font-weight: 600;
}

.section-content p {
  color: #526a82;
  font-size: 13px;
  line-height: 2;
  text-align: justify;
}

.section-content p + p {
  margin-top: 8px;
}

.section-content .section-evidence {
  margin-top: 12px;
  padding: 8px 10px;
  color: #71849a;
  font-size: 11px;
  line-height: 1.6;
  background: #f6f9fc;
  border-radius: 5px;
}

.report-footer {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding: 16px 30px;
  color: #9baaba;
  font-size: 10px;
  background: #f8fafc;
  border-top: 1px solid var(--border);
}

.report-loading {
  max-width: 1000px;
  min-height: 550px;
  margin: 0 auto;
  padding: 25px 50px;
}

.loading-section {
  padding: 25px 0;
  border-bottom: 1px solid var(--border);
}

@media (max-width: 900px) {
  .report-controls {
    align-items: flex-start;
    flex-direction: column;
  }

  .control-fields {
    width: 100%;
    justify-content: flex-end;
  }
}

@media (max-width: 640px) {
  .control-fields {
    align-items: stretch;
    flex-direction: column;
  }

  .control-field .form-control {
    width: 100%;
  }

  .control-fields > .btn {
    align-self: flex-end;
  }

  .report-cover {
    padding: 65px 22px 30px;
  }

  .report-cover h1 {
    font-size: 22px;
  }

  .report-sections {
    padding: 5px 22px 20px;
  }

  .report-section {
    gap: 12px;
  }

  .report-footer {
    flex-direction: column;
    gap: 5px;
  }
}

@media print {
  :global(.app-sidebar),
  :global(.app-topbar),
  .report-controls,
  :global(.page-header),
  .report-error {
    display: none !important;
  }

  :global(.app-workspace) {
    margin: 0 !important;
  }

  :global(.app-main),
  :global(.page) {
    padding: 0 !important;
    background: #fff !important;
  }

  .report-document {
    box-shadow: none;
  }
}
</style>
