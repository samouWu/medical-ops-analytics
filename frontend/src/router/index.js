import { createRouter, createWebHistory } from 'vue-router'
import { getStoredUser, getToken } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/',
    component: () => import('../layouts/AppShell.vue'),
    children: [
      { path: '', redirect: '/management' },
      { path: 'management', name: 'management', component: () => import('../views/ManagementView.vue'), meta: { title: '管理驾驶舱', section: '运营总览' } },
      { path: 'outpatient', name: 'outpatient', component: () => import('../views/TopicView.vue'), meta: { title: '门诊分析', section: '主题分析', topic: 'outpatient', description: '洞察门诊服务规模、患者结构与科室运营表现' } },
      { path: 'inpatient', name: 'inpatient', component: () => import('../views/TopicView.vue'), meta: { title: '住院分析', section: '主题分析', topic: 'inpatient', description: '监测住院服务量、床位使用与住院运营趋势' } },
      { path: 'revenue', name: 'revenue', component: () => import('../views/TopicView.vue'), meta: { title: '收入分析', section: '主题分析', topic: 'revenue', description: '解析医疗收入构成、变化趋势与科室贡献' } },
      { path: 'drugs', name: 'drugs', component: () => import('../views/TopicView.vue'), meta: { title: '药品分析', section: '主题分析', topic: 'drugs', description: '跟踪药品使用、费用结构与重点药品表现' } },
      { path: 'consumables', name: 'consumables', component: () => import('../views/TopicView.vue'), meta: { title: '耗材分析', section: '主题分析', topic: 'consumables', description: '分析医用耗材消耗、费用分布与使用趋势' } },
      { path: 'disease', name: 'disease', component: () => import('../views/TopicView.vue'), meta: { title: '病种分析', section: '主题分析', topic: 'disease', description: '观察病种结构、诊疗规模与重点病种分布' } },
      { path: 'resources', name: 'resources', component: () => import('../views/ResourcesView.vue'), meta: { title: '资源效率', section: '主题分析', description: '评估医疗资源配置、利用效率与服务承载能力' } },
      { path: 'service', name: 'service', component: () => import('../views/TopicView.vue'), meta: { title: '患者服务', section: '主题分析', topic: 'service', description: '关注患者服务体验、满意度与服务质量变化' } },
      { path: 'reports/multidimensional', name: 'multidimensional', component: () => import('../views/MultidimensionalView.vue'), meta: { title: '多维报表', section: '数据应用', description: '自由组合指标与维度，快速生成个性化运营报表' } },
      { path: 'metrics', name: 'metrics', component: () => import('../views/MetricsView.vue'), meta: { title: '指标查询', section: '数据应用', description: '检索指标口径，查询不同时间粒度的指标结果' } },
      { path: 'ai-assistant', name: 'ai-assistant', component: () => import('../views/AiAskView.vue'), meta: { title: '智能问数', section: '数据应用', description: '使用自然语言探索医疗运营数据' } },
      { path: 'reports/generate', name: 'report-generate', component: () => import('../views/ReportsView.vue'), meta: { title: '报告生成', section: '数据应用', description: '基于运营数据生成结构化周期分析报告' } },
      { path: 'quality', name: 'quality', component: () => import('../views/QualityView.vue'), meta: { title: '数据质量', section: '数据治理', description: '监控质量规则执行结果与数据批次状态' } },
      { path: 'integration', name: 'integration', component: () => import('../views/DataIntegrationView.vue'), meta: { title: '数据接入与任务', section: '数据治理', description: '接入业务数据文件，管理数据同步任务' } },
      { path: 'audit', name: 'audit', component: () => import('../views/AuditView.vue'), meta: { title: '系统审计', section: '数据治理', description: '追踪系统操作行为与关键数据访问记录' } },
      { path: 'system', name: 'system', component: () => import('../views/SystemAdminView.vue'), meta: { title: '系统管理', section: '系统管理', description: '维护用户、角色、数据源与ETL任务', roles: ['admin'] } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/management' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  const token = getToken()
  if (!to.meta.public && !token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && token) return { name: 'management' }
  const user = getStoredUser()
  if (to.meta.roles?.length && !to.meta.roles.includes(user?.role)) return { name: 'management' }
  document.title = `${to.meta.title || '医疗运营'} · 医疗运营数据主题分析平台`
  return true
})

export default router
