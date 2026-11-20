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

export function radarOption({ indicators = [], series = [] } = {}) {
  return {
    color: chartColors,
    tooltip: { ...tooltipStyle, trigger: 'item' },
    legend: {
      bottom: 0, itemWidth: 10, itemHeight: 6, icon: 'roundRect',
      textStyle: { color: '#61738a', fontSize: 11 },
    },
    radar: {
      indicator: indicators,
      radius: '62%',
      center: ['50%', '46%'],
      splitNumber: 4,
      axisName: { color: '#61738a', fontSize: 11 },
      splitLine: { lineStyle: { color: '#e6edf5' } },
      splitArea: { areaStyle: { color: ['#fbfdff', '#f6faff'] } },
      axisLine: { lineStyle: { color: '#e6edf5' } },
    },
    series: [{
      type: 'radar',
      symbolSize: 5,
      data: series.map((item) => ({
        name: item.name,
        value: item.value,
        areaStyle: { opacity: 0.16 },
        lineStyle: { width: 2 },
      })),
    }],
  }
}

export function heatmapOption({ xLabels = [], yLabels = [], cells = [], unit = '%' } = {}) {
  const values = cells.map((cell) => cell[2]).filter((value) => Number.isFinite(value))
  return {
    tooltip: {
      ...tooltipStyle,
      trigger: 'item',
      formatter: (params) => `${escapeHtml(yLabels[params.value[1]] || '')} · ${escapeHtml(xLabels[params.value[0]] || '')}<br/><b>${escapeHtml(params.value[2])}${escapeHtml(unit)}</b>`,
    },
    grid: { left: 14, right: 16, top: 18, bottom: 52, containLabel: true },
    xAxis: { type: 'category', data: xLabels, ...axisStyle, splitLine: { show: false } },
    yAxis: { type: 'category', data: yLabels, ...axisStyle, splitLine: { show: false }, axisLabel: { color: '#61738a', fontSize: 11 } },
    visualMap: {
      min: Math.floor(Math.min(...values, 0)),
      max: Math.ceil(Math.max(...values, 1)),
      calculable: false,
      orient: 'horizontal',
      left: 'center',
      bottom: 4,
      itemWidth: 11,
      itemHeight: 80,
      textStyle: { color: '#8b9aaf', fontSize: 10 },
      inRange: { color: ['#eaf3ff', '#9cc4f5', '#2f7cf6'] },
    },
    series: [{
      type: 'heatmap',
      data: cells,
      label: { show: true, color: '#1b2b41', fontSize: 10, formatter: (params) => `${params.value[2]}` },
      itemStyle: { borderColor: '#fff', borderWidth: 2, borderRadius: 3 },
      emphasis: { itemStyle: { shadowBlur: 6, shadowColor: 'rgba(24,48,79,.25)' } },
    }],
  }
}

export function stackedBarOption({ categories = [], series = [], unit = '' } = {}) {
  return {
    color: chartColors,
    tooltip: { ...tooltipStyle, axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(47, 124, 246, 0.04)' } } },
    legend: { top: 0, right: 4, itemWidth: 12, itemHeight: 7, icon: 'roundRect', textStyle: { color: '#61738a', fontSize: 11 } },
    grid: { left: 14, right: 20, top: 38, bottom: 12, containLabel: true },
    xAxis: {
      type: 'category', data: categories, ...axisStyle, splitLine: { show: false },
      axisLabel: { color: '#61738a', fontSize: 11, interval: 0, rotate: categories.length > 6 ? 28 : 0, width: 80, overflow: 'truncate' },
    },
    yAxis: { type: 'value', ...axisStyle, name: unit, nameTextStyle: { color: '#8b9aaf', fontSize: 10 } },
    series: series.map((item, index) => ({
      name: item.name,
      type: 'bar',
      stack: 'total',
      data: item.data,
      barMaxWidth: 26,
      itemStyle: { color: item.color || chartColors[index % chartColors.length], borderRadius: index === series.length - 1 ? [4, 4, 0, 0] : 0 },
      emphasis: { focus: 'series' },
    })),
  }
}

export function waterfallOption({ items = [], unit = '' } = {}) {
  const placeholders = items.map((item) => (item.base === null ? 0 : item.base))
  const values = items.map((item) => item.value)
  return {
    tooltip: {
      ...tooltipStyle,
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(47, 124, 246, 0.04)' } },
      formatter: (params) => {
        const item = items[params[0]?.dataIndex ?? 0] || {}
        return `${escapeHtml(item.name || '')}<br/><b>${escapeHtml(item.display ?? item.value)}${escapeHtml(unit)}</b>`
      },
    },
    grid: { left: 14, right: 20, top: 34, bottom: items.length > 6 ? 26 : 12, containLabel: true },
    xAxis: { type: 'category', data: items.map((item) => item.name), ...axisStyle, splitLine: { show: false }, axisLabel: { color: '#61738a', fontSize: 11, interval: 0, rotate: items.length > 6 ? 30 : 0 } },
    yAxis: { type: 'value', ...axisStyle, name: unit, nameTextStyle: { color: '#8b9aaf', fontSize: 10 } },
    series: [
      { type: 'bar', stack: 'wf', silent: true, itemStyle: { color: 'transparent' }, emphasis: { itemStyle: { color: 'transparent' } }, data: placeholders },
      {
        type: 'bar', stack: 'wf', barMaxWidth: 30,
        data: values.map((value, index) => ({
          value,
          itemStyle: { color: items[index].color || (value >= 0 ? '#2f7cf6' : '#e25555'), borderRadius: 3 },
        })),
        label: { show: true, position: 'top', color: '#61738a', fontSize: 9, formatter: (params) => items[params.dataIndex]?.display ?? params.value },
      },
    ],
  }
}
