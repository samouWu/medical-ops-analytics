<script setup>
import AppIcon from './AppIcon.vue'

defineProps({
  type: { type: String, default: 'empty' },
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  compact: { type: Boolean, default: false },
})
defineEmits(['retry'])
</script>

<template>
  <div class="state-block" :class="[`state-${type}`, { compact }]" role="status">
    <span v-if="type === 'loading'" class="spinner state-spinner" />
    <span v-else class="state-icon">
      <AppIcon :name="type === 'error' ? 'alert' : type === 'success' ? 'check' : 'table'" :size="24" />
    </span>
    <strong>{{ title || (type === 'loading' ? '数据加载中' : type === 'error' ? '暂时无法获取数据' : '暂无数据') }}</strong>
    <p v-if="description || type === 'empty'">{{ description || '当前筛选条件下没有可展示的数据' }}</p>
    <button v-if="type === 'error'" class="btn btn-sm" @click="$emit('retry')">
      <AppIcon name="refresh" :size="14" />重新加载
    </button>
    <slot />
  </div>
</template>

<style scoped>
.state-block {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 9px;
  min-height: 280px;
  padding: 30px 20px;
  color: var(--text-secondary);
  text-align: center;
}

.state-block.compact {
  min-height: 150px;
  padding: 20px;
}

.state-icon {
  display: grid;
  width: 50px;
  height: 50px;
  margin-bottom: 3px;
  place-items: center;
  color: #8ea6bf;
  background: #f1f5f9;
  border-radius: 50%;
}

.state-error .state-icon {
  color: var(--danger);
  background: var(--danger-soft);
}

.state-success .state-icon {
  color: var(--success);
  background: var(--success-soft);
}

.state-spinner {
  width: 28px;
  height: 28px;
  margin-bottom: 8px;
  color: var(--primary);
}

strong {
  color: #425a73;
  font-size: 13px;
  font-weight: 550;
}

p {
  max-width: 420px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.7;
}

.state-block .btn {
  margin-top: 4px;
}
</style>
