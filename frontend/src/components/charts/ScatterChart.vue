<script setup>
import { computed } from 'vue'
import EChart from '../EChart.vue'
import { scatterOption } from '../../utils/chart'

const props = defineProps({
  points: { type: Array, default: () => [] },
  xName: { type: String, default: '横轴' },
  yName: { type: String, default: '纵轴' },
  name: { type: String, default: '分布' },
  color: { type: String, default: '#20a995' },
  loading: { type: Boolean, default: false },
})
defineEmits(['chart-click'])
const option = computed(() => scatterOption(props))
</script>

<template>
  <EChart :option="option" :loading="loading" @chart-click="$emit('chart-click', $event)" />
</template>
