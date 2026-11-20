<script setup>
import { computed } from 'vue'
import EChart from '../EChart.vue'
import { lineOption } from '../../utils/chart'

const props = defineProps({
  dates: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
  yAxisName: { type: String, default: '' },
  yAxisName2: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})
defineEmits(['chart-click'])
const option = computed(() => lineOption(props))
</script>

<template>
  <EChart :option="option" :loading="loading" @chart-click="$emit('chart-click', $event)" />
</template>
