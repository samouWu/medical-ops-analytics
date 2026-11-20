<script setup>
import { computed } from 'vue'
import EChart from '../EChart.vue'
import { waterfallOption } from '../../utils/chart'

const props = defineProps({
  items: { type: Array, default: () => [] },
  unit: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})
const option = computed(() => waterfallOption({ items: props.items, unit: props.unit }))
</script>

<template>
  <EChart :option="option" :loading="loading" />
</template>
