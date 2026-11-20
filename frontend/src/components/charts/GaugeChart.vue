<script setup>
import { computed } from 'vue'
import EChart from '../EChart.vue'
import { gaugeOption } from '../../utils/chart'

const props = defineProps({
  value: { type: Number, default: 0 },
  name: { type: String, default: '完成率' },
  unit: { type: String, default: '%' },
  color: { type: String, default: '#2f7cf6' },
  loading: { type: Boolean, default: false },
})
const option = computed(() => gaugeOption(props))
</script>

<template>
  <EChart :option="option" :loading="loading" />
</template>
