import test from 'node:test'
import assert from 'node:assert/strict'
import { compactNumber, errorMessage, formatMetric, formatNumber } from '../src/utils/format.js'

test('formatNumber handles empty and non-numeric values', () => {
  assert.equal(formatNumber(null), '—')
  assert.equal(formatNumber(undefined), '—')
  assert.equal(formatNumber(''), '—')
  assert.equal(formatNumber('无数据'), '无数据')
})

test('formatNumber groups digits and respects integer format', () => {
  assert.equal(formatNumber(1234567), '1,234,567')
  assert.equal(formatNumber(1234.56, 'integer'), '1,235')
  assert.equal(formatNumber(0), '0')
})

test('formatNumber preserves decimal and percent values without scaling', () => {
  assert.equal(formatNumber(12.3, 'decimal'), '12.30')
  assert.equal(formatNumber(98.5, 'percent'), '98.50')
  assert.equal(formatNumber(12.3456, 'currency'), '12.35')
})

test('formatMetric appends units only for available values', () => {
  assert.equal(formatMetric(1234, '人次', 'integer'), '1,234人次')
  assert.equal(formatMetric(null, '人次'), '—')
  assert.equal(formatMetric(25, ''), '25')
})

test('compactNumber produces localized compact values', () => {
  assert.equal(compactNumber('invalid'), '—')
  assert.equal(compactNumber(0), '0')
  assert.ok(compactNumber(12000).length > 0)
})

test('errorMessage provides a fallback message', () => {
  assert.equal(errorMessage(new Error('网络异常')), '网络异常')
  assert.equal(errorMessage({}), '请求失败，请稍后重试')
  assert.equal(errorMessage(null), '请求失败，请稍后重试')
})
