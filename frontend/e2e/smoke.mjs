import { chromium } from 'playwright-core'
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const EDGE = process.env.EDGE_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
const BASE = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173'
const results = []

function record(name, passed, detail = '') {
  results.push({ name, passed, detail })
  console.log(`${passed ? 'PASS' : 'FAIL'} ${name}${detail ? ' - ' + detail : ''}`)
}

const browser = await chromium.launch({ executablePath: EDGE, headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 960 } })
try {
  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded' })
  await page.getByText('欢迎登录').waitFor({ timeout: 10000 })
  record('登录页加载', true)
  await page.getByRole('button', { name: /登录平台/ }).click()
  await page.waitForURL('**/management', { timeout: 15000 })
  await page.getByText('管理驾驶舱', { exact: true }).first().waitFor({ timeout: 10000 })
  record('管理员登录并进入驾驶舱', true)
  await page.locator('.metric-card').first().waitFor({ timeout: 10000 })
  record('驾驶舱指标卡渲染', true)

  await page.goto(`${BASE}/metrics`, { waitUntil: 'domcontentloaded' })
  await page.getByText('指标查询', { exact: true }).first().waitFor()
  await page.getByRole('button', { name: '按周' }).click()
  await page.waitForTimeout(1200)
  record('指标查询页与按周切换', await page.getByText(/个数据点/).isVisible().catch(() => false))

  await page.goto(`${BASE}/reports/multidimensional`, { waitUntil: 'domcontentloaded' })
  await page.getByText('报表配置').waitFor()
  record('多维报表配置页', await page.getByText('同比', { exact: true }).isVisible())

  await page.goto(`${BASE}/reports/generate`, { waitUntil: 'domcontentloaded' })
  await page.getByText('运营分析报告').first().waitFor()
  await page.getByRole('button', { name: /生成报告/ }).click()
  await page.waitForTimeout(1800)
  record('固定四章节报告渲染', await page.getByText('一、总体概览').isVisible().catch(() => false))

  await page.goto(`${BASE}/ai-assistant`, { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: '指标知识问答' }).click()
  await page.getByText('床位周转次数的口径是什么？').click()
  await page.waitForTimeout(1000)
  record('指标知识问答返回', await page.getByText(/床位周转|口径/).last().isVisible().catch(() => false))

  await page.goto(`${BASE}/system`, { waitUntil: 'domcontentloaded' })
  await page.getByText('用户管理', { exact: true }).first().waitFor()
  record('系统管理四个标签', await page.getByRole('button', { name: /角色权限/ }).isVisible() && await page.getByRole('button', { name: /ETL任务管理/ }).isVisible())

  await page.goto(`${BASE}/resources`, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(1000)
  record('资源效率页', await page.getByText('资源效率', { exact: true }).first().isVisible())

  const failed = results.filter((item) => !item.passed)
  const report = { total: results.length, passed: results.length-failed.length, failed: failed.length, results }
  const output = resolve(dirname(fileURLToPath(import.meta.url)), '../../data/derived/e2e_report.json')
  mkdirSync(dirname(output), { recursive: true })
  writeFileSync(output, JSON.stringify(report, null, 2), 'utf8')
  console.log(JSON.stringify(report, null, 2))
  if (failed.length) process.exitCode = 1
} finally {
  await browser.close()
}
