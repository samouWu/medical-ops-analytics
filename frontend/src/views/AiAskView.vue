<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import FilterBar from '../components/FilterBar.vue'
import LineChart from '../components/charts/LineChart.vue'
import AppIcon from '../components/AppIcon.vue'
import { request } from '../api/client'
import { filterParams, filters, loadMeta } from '../stores/app'
import { errorMessage } from '../utils/format'

const mode = ref('metric')
const examplesByMode = {
  metric: [
    '本月门诊人次趋势如何？',
    '2025年6月医疗收入是多少？',
    '近30天出院人数变化如何？',
    '2025年5月呼吸科床位使用率是多少？',
  ],
  knowledge: [
    '门诊人次和门诊人数有什么区别？',
    '床位周转次数的口径是什么？',
    '平台权限角色如何隔离？',
    'DRG入组率是正式分组结果吗？',
  ],
}
const examples = computed(() => examplesByMode[mode.value])
function changeMode(next) {
  mode.value = next
  clearChat()
}
const welcome = () => ({
  id: Date.now(),
  role: 'assistant',
  content: '您好，我是医疗运营数据助手。您可以询问运营指标、变化趋势或科室对比，我会基于当前筛选范围为您分析。',
})
const messages = ref([welcome()])
const question = ref('')
const asking = ref(false)
const conversation = ref(null)
let messageId = 1

function chartSeries(message) {
  return [{ name: message.data?.metric_code || '指标值', data: (message.data?.points || []).map((item) => item.value) }]
}

async function scrollToBottom() {
  await nextTick()
  if (conversation.value) conversation.value.scrollTop = conversation.value.scrollHeight
}

async function ask(text) {
  const content = String(text ?? question.value).trim()
  if (!content || asking.value) return
  asking.value = true
  question.value = ''
  messages.value.push({ id: messageId++, role: 'user', content })
  const pending = { id: messageId++, role: 'assistant', loading: true }
  messages.value.push(pending)
  await scrollToBottom()
  try {
    const endpoint = mode.value === 'knowledge' ? '/ai/knowledge' : '/ai/ask'
    const data = await request(endpoint, {
      method: 'POST',
      body: mode.value === 'knowledge' ? { question: content } : { question: content, ...filterParams() },
    })
    Object.assign(pending, { loading: false, content: data?.answer || '查询已完成。', data })
  } catch (error) {
    Object.assign(pending, {
      loading: false,
      error: errorMessage(error),
      content: '这次查询未能完成，请检查问题或稍后重试。',
      retryQuestion: content,
    })
  } finally {
    asking.value = false
    await scrollToBottom()
  }
}

function onKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    ask()
  }
}

function clearChat() {
  messages.value = [welcome()]
  question.value = ''
}

onMounted(async () => {
  await loadMeta()
  scrollToBottom()
})
</script>

<template>
  <div class="page">
    <PageHeader title="智能问数" description="使用自然语言探索医疗运营数据，让问题直接抵达答案">
      <template #actions><button class="btn" :disabled="asking" @click="clearChat"><AppIcon name="plus" :size="15" />新建对话</button></template>
    </PageHeader>
    <FilterBar :loading="asking" @apply="clearChat" />

    <div class="assistant-layout">
      <section class="card chat-card">
        <div class="chat-header">
          <div class="assistant-avatar"><AppIcon name="ai" :size="21" /></div>
          <div><h2>运营数据助手</h2><p><span />基于平台指标与数据服务回答</p></div>
          <span class="status-badge info">智能分析</span>
        </div>

        <div ref="conversation" class="chat-conversation" aria-live="polite">
          <div v-for="message in messages" :key="message.id" class="message-row" :class="message.role">
            <div class="message-avatar"><AppIcon :name="message.role === 'assistant' ? 'ai' : 'user'" :size="17" /></div>
            <div class="message-content">
              <div class="message-bubble" :class="{ 'has-chart': message.data?.points?.length }">
                <div v-if="message.loading" class="thinking"><span class="spinner" /><span>正在理解问题并查询数据</span></div>
                <template v-else>
                  <p class="answer-text">{{ message.content }}</p>
                  <div v-if="message.error" class="answer-error"><AppIcon name="alert" :size="14" />{{ message.error }}<button @click="ask(message.retryQuestion)">重试</button></div>
                  <div v-if="message.data?.points?.length" class="answer-chart">
                    <h3>{{ message.data.chart?.title || '指标数据趋势' }}</h3>
                    <div class="chart chart-sm">
                      <LineChart
                        :dates="message.data.points.map((item) => item.date)"
                        :series="chartSeries(message)"
                      />
                    </div>
                  </div>
                  <div v-if="message.data" class="answer-meta">
                    <span v-if="message.data.period">{{ message.data.period.start }} 至 {{ message.data.period.end }}</span>
                    <span v-if="message.data.intent">意图：{{ message.data.intent }}</span>
                    <span v-if="message.data.provider">服务：{{ message.data.provider }}</span>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>

        <div class="chat-input-area">
          <div class="chat-mode-switch">
            <button :class="{ active: mode === 'metric' }" @click="changeMode('metric')">指标问数</button>
            <button :class="{ active: mode === 'knowledge' }" @click="changeMode('knowledge')">指标知识问答</button>
          </div>
          <div class="chat-input">
            <textarea v-model="question" rows="2" placeholder="请输入您想了解的运营问题，Enter 发送，Shift + Enter 换行" :disabled="asking" @keydown="onKeydown" />
            <button class="send-button" :disabled="asking || !question.trim()" aria-label="发送问题" @click="ask()"><AppIcon name="send" :size="18" /></button>
          </div>
          <p>智能回答仅供运营分析参考，请结合指标口径与业务实际判断</p>
        </div>
      </section>

      <aside class="assistant-side">
        <section class="card examples-card">
          <div class="card-header"><div><h2 class="card-heading">试试这样问</h2><p class="card-subheading">点击示例快速发起查询</p></div><AppIcon name="ai" :size="18" /></div>
          <div class="example-list">
            <button v-for="(example, index) in examples" :key="example" :disabled="asking" @click="ask(example)">
              <span>{{ String(index + 1).padStart(2, '0') }}</span><p>{{ example }}</p><AppIcon name="arrowRight" :size="15" />
            </button>
          </div>
        </section>

        <section class="card guide-card">
          <div class="guide-icon"><AppIcon name="info" :size="20" /></div>
          <h3>获得更准确的回答</h3>
          <ul><li>明确指标名称，例如门诊人次、医疗收入</li><li>说明统计周期与需要对比的科室</li><li>结合上方筛选条件限定查询范围</li></ul>
          <div class="current-scope"><span>当前查询范围</span><strong>{{ filters.start || '全部日期' }} 至 {{ filters.end || '全部日期' }}</strong></div>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.assistant-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 290px;
  gap: 18px;
  align-items: start;
}

.chat-card {
  display: flex;
  flex-direction: column;
  height: 670px;
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  gap: 11px;
  min-height: 68px;
  padding: 13px 18px;
  border-bottom: 1px solid var(--border);
}

.assistant-avatar,
.message-avatar {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  color: var(--primary);
  background: var(--primary-soft);
  border-radius: 9px;
}

.assistant-avatar {
  width: 39px;
  height: 39px;
}

.chat-header > div:nth-child(2) {
  flex: 1;
}

.chat-header h2 {
  color: var(--text);
  font-size: 14px;
  font-weight: 600;
}

.chat-header p {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 5px;
  color: var(--text-muted);
  font-size: 11px;
}

.chat-header p span {
  width: 5px;
  height: 5px;
  background: var(--success);
  border-radius: 50%;
}

.chat-conversation {
  flex: 1;
  padding: 23px 20px;
  overflow-y: auto;
  background: #fafcfd;
  scroll-behavior: smooth;
}

.message-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 20px;
}

.message-row.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 31px;
  height: 31px;
  border-radius: 8px;
}

.message-row.user .message-avatar {
  color: #607891;
  background: #e8eef4;
}

.message-content {
  max-width: min(82%, 720px);
}

.message-bubble {
  padding: 12px 15px;
  color: #3b536e;
  font-size: 12px;
  line-height: 1.8;
  background: #fff;
  border: 1px solid #e5ebf2;
  border-radius: 3px 11px 11px 11px;
  box-shadow: 0 2px 6px rgba(24, 48, 79, 0.035);
}

.message-row.user .message-bubble {
  color: #fff;
  background: #337ce4;
  border-color: #337ce4;
  border-radius: 11px 3px 11px 11px;
  box-shadow: none;
}

.answer-text {
  white-space: pre-wrap;
}

.message-bubble.has-chart {
  width: 100%;
  min-width: min(560px, 65vw);
}

.answer-chart {
  margin-top: 13px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.answer-chart h3 {
  color: var(--text);
  font-size: 12px;
  font-weight: 550;
}

.answer-chart .chart {
  height: 235px;
  margin-top: 5px;
}

.answer-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  margin-top: 11px;
  padding-top: 9px;
  color: var(--text-muted);
  font-size: 10px;
  border-top: 1px solid #edf1f5;
}

.answer-error {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
  color: var(--danger);
  font-size: 11px;
}

.answer-error button {
  padding: 2px 6px;
  color: var(--primary);
  background: var(--primary-soft);
  border-radius: 4px;
}

.thinking {
  display: flex;
  align-items: center;
  gap: 9px;
  color: var(--text-secondary);
}

.thinking .spinner {
  width: 15px;
  height: 15px;
  color: var(--primary);
}

.chat-input-area {
  padding: 14px 17px 10px;
  background: #fff;
  border-top: 1px solid var(--border);
}

.chat-mode-switch {
  display: inline-flex;
  gap: 4px;
  margin-bottom: 9px;
  padding: 3px;
  background: #f2f6fa;
  border-radius: 7px;
}

.chat-mode-switch button {
  padding: 6px 11px;
  color: var(--text-secondary);
  font-size: 11px;
  background: transparent;
  border-radius: 5px;
}

.chat-mode-switch button.active {
  color: var(--primary);
  background: #fff;
  box-shadow: 0 1px 4px rgba(22, 51, 82, 0.1);
}

.chat-input {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 9px 9px 9px 13px;
  background: #f8fafc;
  border: 1px solid #dfe6ee;
  border-radius: 9px;
}

.chat-input:focus-within {
  background: #fff;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(47, 124, 246, 0.08);
}

.chat-input textarea {
  flex: 1;
  min-height: 42px;
  max-height: 100px;
  padding: 3px 0;
  color: var(--text);
  font-size: 12px;
  line-height: 1.6;
  background: transparent;
  border: 0;
  outline: 0;
  resize: none;
}

.send-button {
  display: grid;
  flex: 0 0 36px;
  width: 36px;
  height: 36px;
  place-items: center;
  color: #fff;
  background: var(--primary);
  border-radius: 7px;
}

.chat-input-area > p {
  margin-top: 7px;
  color: #a0adbb;
  font-size: 10px;
  text-align: center;
}

.assistant-side {
  display: grid;
  gap: 16px;
}

.examples-card {
  overflow: hidden;
}

.example-list {
  padding: 8px;
}

.example-list button {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 9px;
  color: var(--text-secondary);
  text-align: left;
  background: transparent;
  border-bottom: 1px solid #edf1f5;
}

.example-list button:last-child {
  border: 0;
}

.example-list button:hover:not(:disabled) {
  color: var(--primary);
  background: #f7faff;
}

.example-list button > span {
  color: #a2b4c8;
  font-family: monospace;
  font-size: 11px;
}

.example-list button p {
  flex: 1;
  font-size: 11px;
  line-height: 1.5;
}

.guide-card {
  padding: 19px;
}

.guide-icon {
  display: grid;
  width: 38px;
  height: 38px;
  margin-bottom: 13px;
  place-items: center;
  color: #188a79;
  background: var(--success-soft);
  border-radius: 9px;
}

.guide-card h3 {
  color: #3b536d;
  font-size: 13px;
  font-weight: 600;
}

.guide-card ul {
  margin-top: 12px;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.9;
}

.guide-card li {
  position: relative;
  padding-left: 12px;
}

.guide-card li::before {
  position: absolute;
  top: 8px;
  left: 0;
  width: 4px;
  height: 4px;
  content: '';
  background: #8fa8c2;
  border-radius: 50%;
}

.current-scope {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 15px;
  padding: 10px;
  background: #f6f9fc;
  border-radius: 6px;
}

.current-scope span {
  color: var(--text-muted);
  font-size: 10px;
}

.current-scope strong {
  color: #587089;
  font-size: 11px;
  font-weight: 500;
}

@media (max-width: 1100px) {
  .assistant-layout {
    grid-template-columns: 1fr;
  }

  .assistant-side {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 640px) {
  .chat-card {
    height: 640px;
  }

  .message-content {
    max-width: 88%;
  }

  .message-bubble.has-chart {
    min-width: 72vw;
  }

  .assistant-side {
    grid-template-columns: 1fr;
  }
}
</style>
