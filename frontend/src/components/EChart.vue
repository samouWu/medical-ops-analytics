<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  option: { type: Object, required: true },
  loading: { type: Boolean, default: false },
  autoresize: { type: Boolean, default: true },
})
const emit = defineEmits(['chart-click'])

const element = ref(null)
let chart = null
let resizeObserver = null
let clickHandler = null

function render() {
  if (!chart || !props.option) return
  chart.setOption(props.option, { notMerge: true, lazyUpdate: true })
}

function resize() {
  chart?.resize()
}

function updateLoading() {
  if (!chart) return
  if (props.loading) {
    chart.showLoading({
      text: '数据加载中',
      color: '#2f7cf6',
      textColor: '#8b9aaf',
      maskColor: 'rgba(255, 255, 255, 0.82)',
      fontSize: 12,
    })
  } else {
    chart.hideLoading()
  }
}

onMounted(async () => {
  await nextTick()
  chart = echarts.init(element.value, null, { renderer: 'canvas' })
  clickHandler = (params) => emit('chart-click', {
    name: params.name,
    value: params.value,
    seriesName: params.seriesName,
    dataIndex: params.dataIndex,
  })
  chart.on('click', clickHandler)
  render()
  updateLoading()
  window.addEventListener('resize', resize)
  if (props.autoresize && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(element.value)
  }
})

watch(() => props.option, render, { deep: true })
watch(() => props.loading, updateLoading)

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  resizeObserver?.disconnect()
  if (chart && clickHandler) chart.off('click', clickHandler)
  chart?.dispose()
  chart = null
  clickHandler = null
})

defineExpose({ resize, getChart: () => chart })
</script>

<template>
  <div ref="element" class="echart-container" />
</template>

<style scoped>
.echart-container {
  width: 100%;
  height: 100%;
  min-height: 180px;
}
</style>
