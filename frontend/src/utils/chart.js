export const chartColors = ['#2f7cf6', '#20a995', '#efa43b', '#806ad5', '#e36d82', '#59a3d8']

export function escapeHtml(value) {
  const entities = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }
  return String(value ?? '').replace(/[&<>"']/g, (character) => entities[character])
}

const axisStyle = {
  axisLine: { lineStyle: { color: '#dfe6ee' } },
  axisTick: { show: false },
  axisLabel: { color: '#8191a5', fontSize: 11 },
  splitLine: { lineStyle: { color: '#edf1f5', type: 'dashed' } },
}

export const tooltipStyle = {
  trigger: 'axis',
  backgroundColor: 'rgba(20, 42, 66, 0.94)',
  borderWidth: 0,
  padding: [10, 13],
  textStyle: { color: '#fff', fontSize: 12 },
  axisPointer: { type: 'line', lineStyle: { color: '#a9c3e3', type: 'dashed' } },
}

export function lineOption({ dates = [], series = [], yAxisName = '', yAxisName2 = '' } = {}) {
  const hasSecondAxis = series.some((item) => item.yAxisIndex === 1)
  return {
    color: chartColors,
    tooltip: { ...tooltipStyle },
    legend: {
      show: series.length > 1,
      top: 0,
      right: 4,
      itemWidth: 12,
      itemHeight: 7,
      icon: 'roundRect',
      textStyle: { color: '#61738a', fontSize: 11 },
    },
    grid: { left: 18, right: hasSecondAxis ? 22 : 12, top: series.length > 1 ? 43 : 25, bottom: 12, containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      ...axisStyle,
      splitLine: { show: false },
      axisLine: { lineStyle: { color: '#dfe6ee' } },
    },
    yAxis: [
      { type: 'value', name: yAxisName, nameTextStyle: { color: '#8b9aaf', fontSize: 10 }, ...axisStyle },
      ...(hasSecondAxis ? [{ type: 'value', name: yAxisName2, nameTextStyle: { color: '#8b9aaf', fontSize: 10 }, ...axisStyle, splitLine: { show: false } }] : []),
    ],
    series: series.map((item, index) => ({
      name: item.name,
      type: item.type || 'line',
      data: item.data || [],
      yAxisIndex: item.yAxisIndex || 0,
      smooth: item.smooth ?? true,
      showSymbol: false,
      symbol: 'circle',
      symbolSize: 7,
      lineStyle: { width: 2.3, color: item.color || chartColors[index % chartColors.length] },
      itemStyle: { color: item.color || chartColors[index % chartColors.length], borderColor: '#fff', borderWidth: 2 },
      areaStyle: item.area === false || item.type === 'bar' ? undefined : { color: item.color || chartColors[index % chartColors.length], opacity: 0.055 },
      barMaxWidth: 32,
      emphasis: { focus: 'series' },
    })),
  }
}

export function barOption({ categories = [], values = [], name = '数量', horizontal = false, color = chartColors[0] } = {}) {
  const categoryAxis = {
    type: 'category',
    data: categories,
    ...axisStyle,
    splitLine: { show: false },
    axisLabel: {
      color: '#61738a', fontSize: 11, interval: 0, width: horizontal ? 90 : 80, overflow: 'truncate',
      // 分类较多时倾斜标签，避免科室名互相压字。
      ...(horizontal ? {} : { rotate: categories.length > 6 ? 32 : 0 }),
    },
  }
  const valueAxis = { type: 'value', ...axisStyle }
  return {
    color: [color],
    tooltip: { ...tooltipStyle, axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(47, 124, 246, 0.04)' } } },
    grid: { left: 14, right: 24, top: 22, bottom: horizontal || categories.length <= 6 ? 12 : 30, containLabel: true },
    xAxis: horizontal ? valueAxis : categoryAxis,
    yAxis: horizontal ? { ...categoryAxis, inverse: true } : valueAxis,
    series: [{
      name,
      type: 'bar',
      data: values,
      barMaxWidth: horizontal ? 18 : 34,
      itemStyle: { color, borderRadius: horizontal ? [0, 5, 5, 0] : [5, 5, 0, 0] },
      emphasis: { itemStyle: { color: '#1f64d8' } },
    }],
  }
}

export function gaugeOption({ value = 0, name = '完成率', unit = '%', color = '#2f7cf6' } = {}) {
  return {
    series: [{
      type: 'gauge',
      startAngle: 90,
      endAngle: -270,
      min: 0,
      max: 100,
      radius: '94%',
      center: ['50%', '50%'],
      progress: { show: true, width: 13, roundCap: true, itemStyle: { color } },
      axisLine: { roundCap: true, lineStyle: { width: 13, color: [[1, '#e9eff5']] } },
      pointer: { show: false },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      anchor: { show: false },
      title: { offsetCenter: [0, '28%'], color: '#8194a9', fontSize: 12 },
      detail: {
        valueAnimation: true,
        offsetCenter: [0, '-4%'],
        color: '#226fd9',
        fontSize: 35,
        fontWeight: 600,
        formatter: (current) => `${Number(current).toFixed(1)}${unit}`,
      },
      data: [{ value: Number(value) || 0, name }],
    }],
  }
}

export function scatterOption({ points = [], xName = '横轴', yName = '纵轴', name = '分布', color = '#20a995' } = {}) {
  return {
    color: [color],
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(20, 42, 66, 0.94)',
      borderWidth: 0,
      textStyle: { color: '#fff', fontSize: 12 },
      formatter: (params) => `${escapeHtml(params.data?.[2] || name)}<br/>${escapeHtml(xName)}：${escapeHtml(params.data?.[0])}<br/>${escapeHtml(yName)}：${escapeHtml(params.data?.[1])}`,
    },
    grid: { left: 18, right: 24, top: 24, bottom: 18, containLabel: true },
    xAxis: { type: 'value', name: xName, nameTextStyle: { color: '#8b9aaf', fontSize: 10 }, ...axisStyle },
    yAxis: { type: 'value', name: yName, nameTextStyle: { color: '#8b9aaf', fontSize: 10 }, ...axisStyle },
    series: [{
      name,
      type: 'scatter',
      data: points,
      symbolSize: (value) => Math.max(9, Math.min(24, Number(value?.[3] || 10))),
      itemStyle: { color, opacity: 0.72 },
      emphasis: { itemStyle: { color: '#1f64d8' } },
    }],
  }
}

export function pieOption(data = [], { name = '构成', unit = '' } = {}) {
  return {
    color: chartColors,
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(20, 42, 66, 0.94)',
      borderWidth: 0,
      textStyle: { color: '#fff', fontSize: 12 },
      formatter: (params) => `${params.marker}${escapeHtml(params.name)}<br/><b>${escapeHtml(params.value)}${escapeHtml(unit)}</b> · ${escapeHtml(params.percent)}%`,
    },
    legend: {
      orient: 'vertical',
      right: 8,
      top: 'center',
      itemWidth: 9,
      itemHeight: 9,
      icon: 'circle',
      itemGap: 15,
      textStyle: { color: '#61738a', fontSize: 11 },
    },
    series: [{
      name,
      type: 'pie',
      radius: ['49%', '72%'],
      center: ['35%', '50%'],
      avoidLabelOverlap: true,
      itemStyle: { borderColor: '#fff', borderWidth: 3, borderRadius: 4 },
      label: { show: false },
      emphasis: { scaleSize: 5, label: { show: false } },
      data,
    }],
  }
}
