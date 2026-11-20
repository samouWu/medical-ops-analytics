<script setup>
import { computed } from 'vue'
import EChart from '../EChart.vue'
import { barOption } from '../../utils/chart'

const props = defineProps({
  categories: { type: Array, default: () => [] },
  values: { type: Array, default: () => [] },
  name: { type: String, default: '数量' },
  horizontal: { type: Boolean, default: false },
  color: { type: String, default: '#2f7cf6' },
  loading: { type: Boolean, default: false },
})
defineEmits(['chart-click'])
const option = computed(() => barOption(props))
</script>

<template>
  <EChart :option="option" :loading="loading" @chart-click="$emit('chart-click', $event)" />
</template>
