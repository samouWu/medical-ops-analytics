<script setup>
import { ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'
import BaseModal from './BaseModal.vue'
import { request } from '../api/client'
import { fileExtension } from '../utils/helpers'
import { errorMessage } from '../utils/format'

const props = defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['close', 'success'])

const input = ref(null)
const file = ref(null)
const dragging = ref(false)
const uploading = ref(false)
const error = ref('')
const result = ref(null)

watch(() => props.open, (open) => {
  if (open) {
    file.value = null
    error.value = ''
    result.value = null
  }
})

function chooseFile(selected) {
  error.value = ''
  result.value = null
  if (!selected) return
  if (!['csv', 'xlsx', 'xlsm'].includes(fileExtension(selected.name))) {
    file.value = null
    error.value = '请选择 CSV、XLSX 或 XLSM 格式的文件'
    return
  }
  file.value = selected
}

function onInput(event) {
  chooseFile(event.target.files?.[0])
  event.target.value = ''
}

function onDrop(event) {
  dragging.value = false
  chooseFile(event.dataTransfer?.files?.[0])
}

function formatSize(bytes) {
  if (!Number.isFinite(bytes)) return ''
  return bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(2)} MB` : `${(bytes / 1024).toFixed(1)} KB`
}

function importErrorText(item) {
  if (typeof item === 'string') return item
  if (!item || typeof item !== 'object') return String(item)
  const location = item.row !== undefined ? `第 ${item.row} 行` : item.line !== undefined ? `第 ${item.line} 行` : ''
  return [location, item.field, item.reason || item.message || item.error || item.detail].filter(Boolean).join('：')
}

async function submit() {
  if (!file.value || uploading.value) return
  uploading.value = true
  error.value = ''
  try {
    const body = new FormData()
    body.append('file', file.value)
    result.value = await request('/imports/auto', { method: 'POST', body })
    emit('success', result.value)
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <BaseModal :open="open" title="导入业务数据" width="590px" @close="$emit('close')">
    <div class="import-intro">
      <span class="intro-icon"><AppIcon name="upload" :size="22" /></span>
      <div>
        <strong>上传数据文件</strong>
        <p>支持 CSV、XLSX、XLSM 格式，系统将自动识别源表并校验数据。</p>
      </div>
    </div>

    <label
      class="drop-zone"
      :class="{ dragging, 'has-file': file }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
    >
      <input ref="input" type="file" accept=".csv,.xlsx,.xlsm" @change="onInput">
      <template v-if="file">
        <span class="file-icon"><AppIcon name="file" :size="27" /></span>
        <strong>{{ file.name }}</strong>
        <span>{{ formatSize(file.size) }} · 点击可重新选择</span>
      </template>
      <template v-else>
        <span class="drop-icon"><AppIcon name="upload" :size="28" /></span>
        <strong>点击选择文件，或拖拽文件到此处</strong>
        <span>单次上传一个数据文件</span>
      </template>
    </label>

    <div v-if="error" class="import-message error"><AppIcon name="alert" :size="17" />{{ error }}</div>

    <div v-if="result" class="import-result">
      <div class="import-message success"><AppIcon name="check" :size="17" />文件导入处理完成</div>
      <dl>
        <div><dt>源数据表</dt><dd>{{ result.source_table || '—' }}</dd></div>
        <div><dt>导入行数</dt><dd>{{ result.row_count ?? 0 }}</dd></div>
        <div><dt>异常行数</dt><dd :class="{ 'text-danger': result.error_count }">{{ result.error_count ?? 0 }}</dd></div>
      </dl>
      <div v-if="result.errors?.length" class="import-errors">
        <strong>异常明细</strong>
        <ul><li v-for="(item, index) in result.errors" :key="index">{{ importErrorText(item) }}</li></ul>
      </div>
    </div>

    <template #footer>
      <button class="btn" :disabled="uploading" @click="$emit('close')">{{ result ? '完成' : '取消' }}</button>
      <button class="btn btn-primary" :disabled="!file || uploading || !!result" @click="submit">
        <span v-if="uploading" class="spinner" /><AppIcon v-else name="upload" :size="15" />
        {{ uploading ? '正在导入' : '开始导入' }}
      </button>
    </template>
  </BaseModal>
</template>

<style scoped>
.import-intro {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 20px;
}

.intro-icon {
  display: grid;
  flex: 0 0 42px;
  height: 42px;
  place-items: center;
  color: var(--primary);
  background: var(--primary-soft);
  border-radius: 10px;
}

.import-intro strong {
  color: var(--text);
  font-size: 14px;
  font-weight: 600;
}

.import-intro p {
  margin-top: 5px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.65;
}

.drop-zone {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  min-height: 190px;
  padding: 24px;
  color: var(--text-muted);
  text-align: center;
  background: #fafcff;
  border: 1.5px dashed #c7d5e5;
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 160ms ease, background-color 160ms ease;
}

.drop-zone:hover,
.drop-zone.dragging {
  background: var(--primary-soft);
  border-color: var(--primary);
}

.drop-zone.has-file {
  background: #f5fbf9;
  border-color: #8bcab8;
}

.drop-zone input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
}

.drop-icon,
.file-icon {
  display: grid;
  width: 54px;
  height: 54px;
  margin-bottom: 13px;
  place-items: center;
  color: var(--primary);
  background: #eaf2fd;
  border-radius: 50%;
}

.file-icon {
  color: var(--success);
  background: var(--success-soft);
}

.drop-zone strong {
  max-width: 100%;
  overflow: hidden;
  color: #405872;
  font-size: 13px;
  font-weight: 550;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.drop-zone > span:last-child {
  margin-top: 8px;
  font-size: 11px;
}

.import-message {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.5;
  border-radius: 7px;
}

.import-message.error {
  color: #b94343;
  background: var(--danger-soft);
}

.import-message.success {
  margin-top: 16px;
  color: #138061;
  background: var(--success-soft);
}

.import-result dl {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin: 14px 0 0;
  padding: 14px;
  background: #f7f9fc;
  border-radius: 8px;
}

.import-result dl div {
  text-align: center;
}

.import-result dt {
  color: var(--text-muted);
  font-size: 11px;
}

.import-result dd {
  margin: 6px 0 0;
  color: var(--text);
  font-size: 15px;
  font-weight: 600;
}

.import-errors {
  margin-top: 15px;
}

.import-errors strong {
  color: var(--text-secondary);
  font-size: 12px;
}

.import-errors ul {
  max-height: 140px;
  margin-top: 8px;
  padding: 10px 12px;
  overflow: auto;
  color: var(--danger);
  font-size: 11px;
  line-height: 1.8;
  background: var(--danger-soft);
  border-radius: 7px;
}
</style>
