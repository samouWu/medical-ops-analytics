<script setup>
import { computed } from 'vue'
import EChart from '../EChart.vue'
import { radarOption } from '../../utils/chart'

const props = defineProps({
  indicators: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})
const option = computed(() => radarOption({ indicators: props.indicators, series: props.series }))
</script>

<template>
  <EChart :option="option" :loading="loading" />
</template>
