<script setup>
import { onBeforeUnmount, onMounted, watch } from 'vue'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, required: true },
  width: { type: String, default: '560px' },
  closeOnBackdrop: { type: Boolean, default: true },
})
const emit = defineEmits(['close'])

function close() {
  emit('close')
}

function onKeydown(event) {
  if (props.open && event.key === 'Escape') close()
}

watch(() => props.open, (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
})

onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="open" class="modal-backdrop" @mousedown.self="closeOnBackdrop && close()">
        <section class="modal-panel" :style="{ maxWidth: width }" role="dialog" aria-modal="true" :aria-label="title">
          <header class="modal-header">
            <h2>{{ title }}</h2>
            <button class="icon-button" aria-label="关闭弹窗" @click="close"><AppIcon name="close" :size="19" /></button>
          </header>
          <div class="modal-content"><slot /></div>
          <footer v-if="$slots.footer" class="modal-footer"><slot name="footer" /></footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  z-index: 1000;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(9, 28, 47, 0.48);
}

.modal-panel {
  width: 100%;
  max-height: calc(100vh - 48px);
  overflow: auto;
  background: #fff;
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 14px;
  box-shadow: 0 24px 70px rgba(11, 33, 55, 0.24);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 17px 20px;
  border-bottom: 1px solid var(--border);
}

.modal-header h2 {
  color: var(--text);
  font-size: 16px;
  font-weight: 600;
}

.modal-content {
  padding: 22px;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 20px;
  background: #fafbfd;
  border-top: 1px solid var(--border);
  border-radius: 0 0 14px 14px;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 160ms ease;
}

.modal-fade-enter-active .modal-panel,
.modal-fade-leave-active .modal-panel {
  transition: transform 160ms ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-from .modal-panel,
.modal-fade-leave-to .modal-panel {
  transform: translateY(8px) scale(0.99);
}

@media (max-width: 640px) {
  .modal-backdrop {
    align-items: flex-end;
    padding: 12px;
  }

  .modal-panel {
    max-height: calc(100vh - 24px);
  }

  .modal-content {
    padding: 17px;
  }
}
</style>
