<script setup>
import { computed } from 'vue'
import EChart from '../EChart.vue'
import { stackedBarOption } from '../../utils/chart'

const props = defineProps({
  categories: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
  unit: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})
const option = computed(() => stackedBarOption({ categories: props.categories, series: props.series, unit: props.unit }))
</script>

<template>
  <EChart :option="option" :loading="loading" />
</template>
