import test from 'node:test'
import assert from 'node:assert/strict'
import { asArray, buildQuery, fileExtension, filenameFromDisposition } from '../src/utils/helpers.js'

test('buildQuery serializes filters and omits empty values', () => {
  const query = buildQuery({ start: '2025-06-01', end: '2025-06-30', dept_code: '', empty: null, ignored: undefined, count: 0 })
  assert.equal(query, '?start=2025-06-01&end=2025-06-30&count=0')
})

test('buildQuery encodes Chinese text and returns empty string without params', () => {
  assert.equal(buildQuery({ dept_name: '心血管内科' }), '?dept_name=%E5%BF%83%E8%A1%80%E7%AE%A1%E5%86%85%E7%A7%91')
  assert.equal(buildQuery(), '')
})

test('fileExtension supports uppercase and multi-dot filenames', () => {
  assert.equal(fileExtension('运营数据.XLSX'), 'xlsx')
  assert.equal(fileExtension('backup.data.csv'), 'csv')
  assert.equal(fileExtension('README'), '')
  assert.equal(fileExtension(), '')
})

test('asArray only returns arrays', () => {
  assert.deepEqual(asArray([1, 2]), [1, 2])
  assert.deepEqual(asArray(null), [])
  assert.deepEqual(asArray({ rows: [] }), [])
})

test('filenameFromDisposition reads plain and encoded filenames', () => {
  assert.equal(filenameFromDisposition('attachment; filename="report.xlsx"', 'fallback.xlsx'), 'report.xlsx')
  assert.equal(filenameFromDisposition("attachment; filename*=UTF-8''%E8%BF%90%E8%90%A5.xlsx", 'fallback.xlsx'), '运营.xlsx')
  assert.equal(filenameFromDisposition('', 'fallback.xlsx'), 'fallback.xlsx')
  assert.equal(filenameFromDisposition("filename*=UTF-8''%E0%A4%A", 'fallback.xlsx'), 'fallback.xlsx')
})
