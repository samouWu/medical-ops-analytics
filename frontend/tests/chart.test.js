import test from 'node:test'
import assert from 'node:assert/strict'
import { barOption, escapeHtml, gaugeOption, lineOption, pieOption, scatterOption } from '../src/utils/chart.js'

test('lineOption maps dates, series and dual axes', () => {
  const option = lineOption({
    dates: ['2025-06-01'],
    series: [
      { name: '门诊人次', data: [12] },
      { name: '收入', data: [20], yAxisIndex: 1, type: 'bar' },
    ],
  })
  assert.deepEqual(option.xAxis.data, ['2025-06-01'])
  assert.equal(option.yAxis.length, 2)
  assert.equal(option.series.length, 2)
  assert.equal(option.series[1].type, 'bar')
  assert.equal(option.series[1].yAxisIndex, 1)
})

test('lineOption handles empty datasets', () => {
  const option = lineOption()
  assert.deepEqual(option.xAxis.data, [])
  assert.deepEqual(option.series, [])
  assert.equal(option.legend.show, false)
})

test('barOption supports horizontal layout', () => {
  const option = barOption({ categories: ['内科'], values: [8], horizontal: true })
  assert.equal(option.xAxis.type, 'value')
  assert.equal(option.yAxis.type, 'category')
  assert.equal(option.yAxis.inverse, true)
  assert.deepEqual(option.series[0].data, [8])
})

test('escapeHtml sanitizes chart tooltip values', () => {
  assert.equal(escapeHtml('<img src=x onerror="alert(1)">'), '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;')
  assert.equal(escapeHtml("内科&'外科'"), '内科&amp;&#39;外科&#39;')
  assert.equal(escapeHtml(null), '')
})

test('pieOption preserves distribution data and disables labels', () => {
  const data = [{ name: '西药', value: 10 }]
  const option = pieOption(data, { unit: '万元' })
  assert.deepEqual(option.series[0].data, data)
  assert.equal(option.series[0].label.show, false)
  assert.equal(option.tooltip.trigger, 'item')
})

test('gaugeOption renders one bounded gauge value', () => {
  const option = gaugeOption({ value: 97.5, name: '质量得分', unit: '%' })
  assert.equal(option.series[0].type, 'gauge')
  assert.equal(option.series[0].max, 100)
  assert.equal(option.series[0].data[0].value, 97.5)
  assert.equal(option.series[0].data[0].name, '质量得分')
})

test('scatterOption maps named points and escapes tooltip text', () => {
  const option = scatterOption({
    points: [[120, 45.7, '<科室>', 12]],
    xName: '收入',
    yName: '使用率',
  })
  assert.equal(option.series[0].type, 'scatter')
  assert.deepEqual(option.series[0].data[0], [120, 45.7, '<科室>', 12])
  assert.equal(option.series[0].symbolSize([120, 45.7, '<科室>', 12]), 12)
  assert.match(option.tooltip.formatter({ data: [120, 45.7, '<科室>', 12] }), /&lt;科室&gt;/)
})
