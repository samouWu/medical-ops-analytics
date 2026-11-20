<script setup>
import { computed } from 'vue'
import EChart from '../EChart.vue'
import { heatmapOption } from '../../utils/chart'

const props = defineProps({
  xLabels: { type: Array, default: () => [] },
  yLabels: { type: Array, default: () => [] },
  cells: { type: Array, default: () => [] },
  unit: { type: String, default: '%' },
  loading: { type: Boolean, default: false },
})
const option = computed(() => heatmapOption({ xLabels: props.xLabels, yLabels: props.yLabels, cells: props.cells, unit: props.unit }))
</script>

<template>
  <EChart :option="option" :loading="loading" />
</template>
