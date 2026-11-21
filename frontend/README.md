# frontend · 可视化分析前端

Vue 3 + Vue Router + ECharts + Vite 构建的单页应用，承载管理驾驶舱、八类主题分析、指标查询、多维报表、智能问数与系统管理。

## 目录结构

```text
src/
  api/           axios 实例、统一 envelope 解析、文件下载
  components/    指标卡、筛选器、数据表格、导入弹窗、状态组件
  components/charts/
                 Line / Bar / Pie / Gauge / Scatter /
                 Radar / Heatmap / StackedBar / Waterfall
  layouts/       应用壳层、侧边导航、顶栏与告警铃铛
  views/         驾驶舱、8 个主题页、指标、报表、问数、质量、接入、系统管理
  router/        路由与登录守卫
  stores/        登录态、全局筛选、元数据
  styles/        设计变量与全局样式
e2e/smoke.mjs    24 项浏览器端到端检查
tests/           19 项 Node 单元测试
```

## 本地启动

```bash
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

开发服务器把 `/api` 代理到 `http://127.0.0.1:8765`，因此后端需先启动。

## 常用命令

| 命令 | 说明 |
|---|---|
| `npm run dev` | 本地开发 |
| `npm run build` | 生产构建 |
| `npm test` | 19 项单元测试 |
| `npm run lint` | ESLint 检查 |
| `npm run e2e` | 浏览器 E2E（需前后端已启动，使用本机 Edge） |

## 图表与交互

共 9 个图表组件、10 类图形：折线/面积、柱状、横向条形、饼/环、仪表盘、散点、雷达、热力、堆叠柱、瀑布。支持科室下钻、日/周/月粒度、同比/环比、自定义日期、Excel 导出与空态降级。
