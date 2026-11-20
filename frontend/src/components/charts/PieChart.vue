<script setup>
import { computed } from 'vue'
import EChart from '../EChart.vue'
import { pieOption } from '../../utils/chart'

const props = defineProps({
  data: { type: Array, default: () => [] },
  name: { type: String, default: '构成' },
  unit: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})
defineEmits(['chart-click'])
const option = computed(() => pieOption(props.data, { name: props.name, unit: props.unit }))
</script>

<template>
  <EChart :option="option" :loading="loading" @chart-click="$emit('chart-click', $event)" />
</template>
