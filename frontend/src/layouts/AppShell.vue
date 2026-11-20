<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import MedicalDecor from '../components/MedicalDecor.vue'
import { clearSession, getStoredUser } from '../stores/auth'
import { appState, loadMeta } from '../stores/app'
import { request } from '../api/client'

const route = useRoute()
const router = useRouter()
const mobileOpen = ref(false)
const user = getStoredUser() || {}
const openAlerts = ref(0)

const navGroups = [
  {
    label: '运营总览',
    items: [{ to: '/management', label: '管理驾驶舱', icon: 'dashboard' }],
  },
  {
    label: '主题分析',
    items: [
      { to: '/outpatient', label: '门诊分析', icon: 'outpatient' },
      { to: '/inpatient', label: '住院分析', icon: 'inpatient' },
      { to: '/revenue', label: '收入分析', icon: 'revenue' },
      { to: '/drugs', label: '药品分析', icon: 'drugs' },
      { to: '/consumables', label: '耗材分析', icon: 'consumables' },
      { to: '/disease', label: '病种分析', icon: 'disease' },
      { to: '/resources', label: '资源效率', icon: 'resources' },
      { to: '/service', label: '患者服务', icon: 'service' },
    ],
  },
  {
    label: '数据应用',
    items: [
      { to: '/reports/multidimensional', label: '多维报表', icon: 'multidimensional' },
      { to: '/metrics', label: '指标查询', icon: 'metrics' },
      { to: '/ai-assistant', label: '智能问数', icon: 'ai' },
      { to: '/reports/generate', label: '报告生成', icon: 'report' },
    ],
  },
  {
    label: '数据治理',
    items: [
      { to: '/quality', label: '数据质量', icon: 'quality' },
      { to: '/integration', label: '数据接入与任务', icon: 'integration' },
      { to: '/audit', label: '系统审计', icon: 'audit' },
      { to: '/system', label: '系统管理', icon: 'user', adminOnly: true },
    ],
  },
]

const today = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
  weekday: 'short',
}).format(new Date())

const roleName = computed(() => ({ admin: '系统管理员', analyst: '数据分析师', department: '科室用户', engineer: '数据工程师' }[user.role] || user.role || '平台用户'))

watch(() => route.fullPath, () => {
  mobileOpen.value = false
  fetchAlerts()
})
onMounted(() => {
  loadMeta()
  fetchAlerts()
})

async function fetchAlerts() {
  try {
    const data = await request('/quality/summary')
    openAlerts.value = Number(data?.open ?? 0)
  } catch {
    openAlerts.value = 0
  }
}

function logout() {
  clearSession()
  router.replace('/login')
}
</script>

<template>
  <div class="app-layout">
    <button
      v-if="mobileOpen"
      class="sidebar-mask"
      aria-label="关闭导航"
      @click="mobileOpen = false"
    />

    <aside class="app-sidebar" :class="{ 'mobile-open': mobileOpen }">
      <RouterLink class="brand" to="/management" aria-label="医疗运营分析平台首页">
        <span class="brand-symbol"><AppIcon name="health" :size="23" /></span>
        <span class="brand-copy">
          <strong>医疗运营洞察</strong>
          <small>MEDICAL OPERATIONS</small>
        </span>
      </RouterLink>

      <nav class="sidebar-nav" aria-label="主导航">
        <div v-for="group in navGroups" :key="group.label" class="nav-group">
          <div class="nav-group-label">{{ group.label }}</div>
          <RouterLink
            v-for="item in group.items"
            v-show="!item.adminOnly || user.role === 'admin'"
            :key="item.to"
            :to="item.to"
            class="nav-item"
          >
            <AppIcon :name="item.icon" :size="18" />
            <span>{{ item.label }}</span>
            <span class="nav-active-mark" />
          </RouterLink>
        </div>
      </nav>

      <div class="sidebar-decor">
        <MedicalDecor variant="sidebar" />
      </div>

      <div class="sidebar-footer">
        <div class="sidebar-avatar">{{ (user.display_name || user.username || '用').slice(0, 1) }}</div>
        <div class="sidebar-user">
          <strong>{{ user.display_name || user.username || '平台用户' }}</strong>
          <span>{{ roleName }}</span>
        </div>
        <button class="sidebar-logout" title="退出登录" aria-label="退出登录" @click="logout">
          <AppIcon name="logout" :size="18" />
        </button>
      </div>
    </aside>

    <div class="app-workspace">
      <header class="app-topbar">
        <div class="topbar-left">
          <button class="icon-button mobile-menu" aria-label="打开导航" @click="mobileOpen = true">
            <AppIcon name="menu" :size="21" />
          </button>
          <div class="breadcrumb">
            <span>医疗运营</span>
            <AppIcon name="chevronRight" :size="13" />
            <span class="hide-mobile">{{ route.meta.section }}</span>
            <AppIcon class="hide-mobile" name="chevronRight" :size="13" />
            <strong>{{ route.meta.title }}</strong>
          </div>
        </div>
        <div class="topbar-right">
          <div v-if="appState.metaError" class="service-status offline" :title="appState.metaError">
            <span class="status-dot" />数据服务待连接
          </div>
          <div v-else-if="appState.meta.date_range.max" class="service-status">
            <span class="status-dot" />数据服务正常
          </div>
          <span class="topbar-divider" />
          <div class="topbar-date hide-mobile">
            <AppIcon name="calendar" :size="16" />
            <span>{{ today }}</span>
          </div>
          <RouterLink to="/quality" class="alert-bell" :class="{ active: openAlerts > 0 }" :title="openAlerts ? `${openAlerts} 条质量告警未处理` : '当前无质量告警'">
            <AppIcon name="alert" :size="17" />
            <span v-if="openAlerts" class="alert-count">{{ openAlerts > 99 ? '99+' : openAlerts }}</span>
          </RouterLink>
          <details class="user-dropdown">
            <summary>
              <span class="topbar-avatar">{{ (user.display_name || user.username || '用').slice(0, 1) }}</span>
              <span class="user-name hide-mobile">{{ user.display_name || user.username }}</span>
              <AppIcon name="chevronDown" :size="14" />
            </summary>
            <div class="dropdown-panel">
              <div class="dropdown-user">
                <strong>{{ user.display_name || user.username }}</strong>
                <span>{{ user.username }} · {{ roleName }}</span>
              </div>
              <button @click="logout"><AppIcon name="logout" :size="16" />退出登录</button>
            </div>
          </details>
        </div>
      </header>

      <main class="app-main">
        <RouterView v-slot="{ Component }">
          <Transition name="page-fade" mode="out-in">
            <component :is="Component" :key="route.meta.topic || route.name" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>

<style scoped>
.alert-bell {
  position: relative;
  display: grid;
  width: 34px;
  height: 34px;
  margin-right: 4px;
  place-items: center;
  color: #6b7f96;
  background: #f4f7fb;
  border-radius: 9px;
  transition: color 160ms ease, background 160ms ease;
}

.alert-bell:hover {
  color: var(--primary);
  background: var(--primary-soft);
}

.alert-bell.active {
  color: #c2410c;
  background: #fff3e8;
}

.alert-count {
  position: absolute;
  top: -5px;
  right: -5px;
  min-width: 17px;
  padding: 0 4px;
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  line-height: 17px;
  text-align: center;
  background: #e25555;
  border-radius: 9px;
}


.app-layout {
  min-height: 100vh;
}

.app-sidebar {
  position: fixed;
  z-index: 40;
  inset: 0 auto 0 0;
  display: flex;
  flex-direction: column;
  width: var(--sidebar-width);
  color: #d8e5f1;
  background: var(--navy);
  border-right: 1px solid rgba(255, 255, 255, 0.035);
}

.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  min-height: 78px;
  padding: 17px 21px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.brand-symbol {
  display: grid;
  flex: 0 0 37px;
  width: 37px;
  height: 37px;
  place-items: center;
  color: #fff;
  background: var(--primary);
  border-radius: 10px;
  box-shadow: 0 5px 14px rgba(0, 0, 0, 0.15);
}

.brand-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.brand-copy strong {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.6px;
  white-space: nowrap;
}

.brand-copy small {
  margin-top: 4px;
  color: #7e9ab5;
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 1.2px;
}

.sidebar-nav {
  flex: 1;
  padding: 13px 12px 20px;
  overflow-x: hidden;
  overflow-y: auto;
  scrollbar-color: #2b4964 transparent;
  scrollbar-width: thin;
}

.nav-group + .nav-group {
  margin-top: 12px;
}

.nav-group-label {
  padding: 9px 12px 7px;
  color: #7792ad;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 1.2px;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 11px;
  height: 39px;
  margin: 2px 0;
  padding: 0 12px;
  color: #b7c9d9;
  font-size: 13px;
  border-radius: 7px;
  transition: color 160ms ease, background-color 160ms ease;
}

.nav-item svg {
  color: #8fa9c0;
  transition: color 160ms ease;
}

.nav-item:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.055);
}

.nav-item.router-link-active {
  color: #fff;
  font-weight: 500;
  background: #2166c1;
  box-shadow: 0 4px 12px rgba(3, 18, 34, 0.16);
}

.nav-item.router-link-active svg {
  color: #fff;
}

.nav-active-mark {
  position: absolute;
  right: 0;
  width: 3px;
  height: 15px;
  background: transparent;
  border-radius: 3px 0 0 3px;
}

.nav-item.router-link-active .nav-active-mark {
  background: #9cc5ff;
}

.sidebar-decor {
  padding: 0 16px 6px;
  overflow: hidden;
}

.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 73px;
  padding: 13px 16px;
  background: var(--navy-deep);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.sidebar-avatar,
.topbar-avatar {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  color: #dceaff;
  font-size: 13px;
  font-weight: 600;
  background: #285174;
  border-radius: 50%;
}

.sidebar-avatar {
  width: 34px;
  height: 34px;
}

.sidebar-user {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.sidebar-user strong {
  overflow: hidden;
  color: #edf5fc;
  font-size: 12px;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-user span {
  margin-top: 4px;
  color: #7996b1;
  font-size: 11px;
}

.sidebar-logout {
  padding: 6px;
  color: #7f9bb5;
  background: transparent;
  border-radius: 5px;
}

.sidebar-logout:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.07);
}

.app-workspace {
  min-height: 100vh;
  margin-left: var(--sidebar-width);
}

.app-topbar {
  position: sticky;
  z-index: 30;
  top: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--topbar-height);
  padding: 0 28px;
  background: rgba(255, 255, 255, 0.97);
  border-bottom: 1px solid var(--border);
  box-shadow: 0 1px 5px rgba(25, 47, 74, 0.025);
}

.topbar-left,
.topbar-right,
.breadcrumb,
.topbar-date,
.service-status,
.user-dropdown summary {
  display: flex;
  align-items: center;
}

.breadcrumb {
  gap: 8px;
  color: var(--text-muted);
  font-size: 12px;
}

.breadcrumb strong {
  color: #344c66;
  font-weight: 550;
}

.topbar-right {
  gap: 16px;
}

.service-status {
  gap: 6px;
  color: #608274;
  font-size: 11px;
}

.service-status .status-dot {
  color: var(--success);
}

.service-status.offline {
  color: var(--warning);
}

.service-status.offline .status-dot {
  color: var(--warning);
}

.topbar-divider {
  width: 1px;
  height: 22px;
  background: var(--border);
}

.topbar-date {
  gap: 7px;
  color: var(--text-secondary);
  font-size: 12px;
}

.user-dropdown {
  position: relative;
}

.user-dropdown summary {
  gap: 8px;
  color: var(--text-secondary);
  font-size: 12px;
  list-style: none;
  cursor: pointer;
}

.user-dropdown summary::-webkit-details-marker {
  display: none;
}

.topbar-avatar {
  width: 32px;
  height: 32px;
  color: #2367bf;
  background: #eaf2fd;
}

.user-name {
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dropdown-panel {
  position: absolute;
  top: 44px;
  right: 0;
  width: 205px;
  padding: 8px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: 0 12px 32px rgba(23, 47, 74, 0.14);
}

.dropdown-user {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 10px 10px 12px;
  border-bottom: 1px solid var(--border);
}

.dropdown-user strong {
  color: var(--text);
  font-size: 13px;
}

.dropdown-user span {
  color: var(--text-muted);
  font-size: 11px;
}

.dropdown-panel button {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  margin-top: 5px;
  padding: 9px 10px;
  color: var(--danger);
  font-size: 12px;
  text-align: left;
  background: transparent;
  border-radius: 6px;
}

.dropdown-panel button:hover {
  background: var(--danger-soft);
}

.mobile-menu,
.sidebar-mask {
  display: none;
}

.app-main {
  min-height: calc(100vh - var(--topbar-height));
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 120ms ease, transform 120ms ease;
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(3px);
}

.page-fade-leave-to {
  opacity: 0;
}

@media (max-width: 900px) {
  .app-sidebar {
    transform: translateX(-100%);
    transition: transform 180ms ease;
  }

  .app-sidebar.mobile-open {
    transform: translateX(0);
  }

  .sidebar-mask {
    position: fixed;
    z-index: 39;
    inset: 0;
    display: block;
    background: rgba(6, 22, 38, 0.45);
  }

  .app-workspace {
    margin-left: 0;
  }

  .mobile-menu {
    display: inline-flex;
    margin-left: -8px;
  }

  .app-topbar {
    padding: 0 20px;
  }

  .service-status,
  .topbar-divider {
    display: none;
  }
}

@media (max-width: 640px) {
  .app-topbar {
    height: 60px;
    padding: 0 14px;
  }

  .breadcrumb > span:first-child,
  .breadcrumb > svg:first-of-type {
    display: none;
  }

  .topbar-right {
    gap: 8px;
  }
}
</style>
