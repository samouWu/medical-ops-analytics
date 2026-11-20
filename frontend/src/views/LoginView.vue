<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import MedicalDecor from '../components/MedicalDecor.vue'
import { request } from '../api/client'
import { saveSession } from '../stores/auth'
import { errorMessage } from '../utils/format'

const route = useRoute()
const router = useRouter()
const form = reactive({ username: 'admin', password: 'admin123' })
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')

async function login() {
  error.value = ''
  if (!form.username.trim() || !form.password) {
    error.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  try {
    const data = await request('/auth/login', {
      method: 'POST',
      body: { username: form.username.trim(), password: form.password },
    })
    saveSession(data.token, data.user)
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
      ? route.query.redirect
      : '/management'
    await router.replace(redirect)
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <section class="login-brand-panel">
      <div class="brand-decoration decoration-one" />
      <div class="brand-decoration decoration-two" />
      <div class="login-brand">
        <span class="login-brand-symbol"><AppIcon name="health" :size="28" /></span>
        <div><strong>医疗运营洞察</strong><span>MEDICAL OPERATIONS ANALYTICS</span></div>
      </div>
      <div class="brand-hero">
        <span class="hero-eyebrow"><span />数据驱动医院精细化管理</span>
        <h1>让医疗运营决策<br>更清晰、更高效</h1>
        <p>汇聚全院运营数据，以统一指标与智能分析，<br>助力管理者洞察趋势、优化资源配置。</p>
        <div class="brand-features">
          <div class="brand-feature">
            <span><AppIcon name="dashboard" :size="21" /></span>
            <div><strong>运营全景</strong><p>多维指标实时汇聚，核心态势一屏掌握</p></div>
          </div>
          <div class="brand-feature">
            <span><AppIcon name="ai" :size="21" /></span>
            <div><strong>智能分析</strong><p>自然语言问数，让数据探索简单直接</p></div>
          </div>
          <div class="brand-feature">
            <span><AppIcon name="quality" :size="21" /></span>
            <div><strong>数据可信</strong><p>质量规则持续监测，分析口径统一透明</p></div>
          </div>
        </div>
      </div>
      <MedicalDecor variant="brand" />
      <div class="brand-footer">统一数据 · 统一指标 · 统一洞察</div>
    </section>

    <main class="login-form-panel">
      <div class="mobile-login-brand">
        <span class="login-brand-symbol"><AppIcon name="health" :size="24" /></span>
        <strong>医疗运营洞察</strong>
      </div>
      <div class="login-box">
        <div class="login-heading">
          <span class="login-welcome">WELCOME BACK</span>
          <h2>欢迎登录</h2>
          <p>登录医疗运营数据主题分析平台</p>
        </div>
        <form @submit.prevent="login">
          <label class="login-field">
            <span>用户名</span>
            <div class="input-with-icon">
              <AppIcon name="user" :size="18" />
              <input v-model="form.username" autocomplete="username" placeholder="请输入用户名" :disabled="loading">
            </div>
          </label>
          <label class="login-field">
            <span>密码</span>
            <div class="input-with-icon">
              <AppIcon name="lock" :size="18" />
              <input
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="请输入密码"
                :disabled="loading"
              >
              <button type="button" class="password-toggle" :aria-label="showPassword ? '隐藏密码' : '显示密码'" @click="showPassword = !showPassword">
                <AppIcon :name="showPassword ? 'eyeOff' : 'eye'" :size="17" />
              </button>
            </div>
          </label>
          <div v-if="error" class="login-error" role="alert"><AppIcon name="alert" :size="16" />{{ error }}</div>
          <button class="login-submit" type="submit" :disabled="loading">
            <span v-if="loading" class="spinner" />
            <template v-else>登录平台<AppIcon name="arrowRight" :size="18" /></template>
          </button>
        </form>
        <div class="default-account">
          <AppIcon name="info" :size="16" />
          <div><strong>默认演示账号</strong><p>用户名 admin，密码 admin123</p></div>
        </div>
        <p class="security-note"><AppIcon name="lock" :size="12" />登录即代表您同意遵守平台数据安全规范</p>
      </div>
      <footer class="login-footer">© {{ new Date().getFullYear() }} 医疗运营数据主题分析平台</footer>
    </main>
  </div>
</template>

<style scoped>
.login-page {
  display: grid;
  grid-template-columns: minmax(420px, 0.92fr) minmax(520px, 1.08fr);
  min-height: 100vh;
  background: #fff;
}

.login-brand-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  padding: 38px 54px 28px;
  overflow: hidden;
  color: #fff;
  background: #102d4b;
}

.brand-decoration {
  position: absolute;
  border: 1px solid rgba(130, 178, 225, 0.12);
  border-radius: 50%;
  pointer-events: none;
}

.decoration-one {
  top: -180px;
  right: -170px;
  width: 480px;
  height: 480px;
  box-shadow: 0 0 0 70px rgba(130, 178, 225, 0.025), 0 0 0 140px rgba(130, 178, 225, 0.018);
}

.decoration-two {
  bottom: -210px;
  left: -190px;
  width: 430px;
  height: 430px;
  box-shadow: 0 0 0 65px rgba(130, 178, 225, 0.02);
}

.login-brand {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 13px;
}

.login-brand-symbol {
  display: grid;
  flex: 0 0 44px;
  width: 44px;
  height: 44px;
  place-items: center;
  color: #fff;
  background: var(--primary);
  border-radius: 11px;
}

.login-brand > div {
  display: flex;
  flex-direction: column;
}

.login-brand strong {
  font-size: 19px;
  font-weight: 600;
  letter-spacing: 1px;
}

.login-brand > div span {
  margin-top: 5px;
  color: #84a2bf;
  font-size: 9px;
  letter-spacing: 1.5px;
}

.brand-hero {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 500px;
  margin: auto 0;
  padding: 50px 0;
}

.hero-eyebrow {
  display: flex;
  align-items: center;
  gap: 9px;
  color: #8eb7e3;
  font-size: 12px;
  letter-spacing: 1px;
}

.hero-eyebrow > span {
  width: 22px;
  height: 2px;
  background: #4a93e7;
}

.brand-hero h1 {
  margin-top: 23px;
  font-size: clamp(32px, 3.2vw, 45px);
  font-weight: 600;
  line-height: 1.5;
  letter-spacing: 2px;
}

.brand-hero > p {
  margin-top: 20px;
  color: #9ab2c9;
  font-size: 13px;
  line-height: 2;
}

.brand-features {
  display: grid;
  gap: 13px;
  margin-top: 42px;
}

.brand-feature {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 13px 15px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
}

.brand-feature > span {
  display: grid;
  flex: 0 0 38px;
  height: 38px;
  place-items: center;
  color: #87baff;
  background: rgba(74, 147, 231, 0.12);
  border-radius: 8px;
}

.brand-feature strong {
  font-size: 13px;
  font-weight: 550;
}

.brand-feature p {
  margin-top: 5px;
  color: #829eb8;
  font-size: 11px;
}

.brand-footer {
  position: relative;
  z-index: 1;
  color: #607f9d;
  font-size: 11px;
  letter-spacing: 2px;
}

.login-form-panel {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 60px 32px 75px;
  background: #fff;
}

.login-box {
  width: 100%;
  max-width: 390px;
}

.login-welcome {
  color: var(--primary);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 2px;
}

.login-heading h2 {
  margin-top: 10px;
  color: #172e49;
  font-size: 30px;
  font-weight: 600;
  letter-spacing: 1px;
}

.login-heading p {
  margin-top: 10px;
  color: var(--text-muted);
  font-size: 13px;
}

.login-box form {
  margin-top: 34px;
}

.login-field {
  display: block;
  margin-bottom: 21px;
}

.login-field > span {
  display: block;
  margin-bottom: 9px;
  color: #40566f;
  font-size: 12px;
  font-weight: 500;
}

.input-with-icon {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 47px;
  padding: 0 13px;
  color: #8a9bb0;
  background: #fafbfd;
  border: 1px solid #dfe6ee;
  border-radius: 8px;
  transition: border-color 160ms ease, box-shadow 160ms ease, background-color 160ms ease;
}

.input-with-icon:focus-within {
  color: var(--primary);
  background: #fff;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(47, 124, 246, 0.09);
}

.input-with-icon input {
  flex: 1;
  min-width: 0;
  height: 100%;
  padding: 0;
  color: var(--text);
  font-size: 13px;
  background: transparent;
  border: 0;
  outline: 0;
}

.input-with-icon input::placeholder {
  color: #a7b4c3;
}

.password-toggle {
  padding: 5px;
  color: #91a1b3;
  background: transparent;
}

.login-error {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: -5px 0 15px;
  padding: 9px 11px;
  color: #be4747;
  font-size: 12px;
  background: var(--danger-soft);
  border-radius: 6px;
}

.login-submit {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  width: 100%;
  height: 47px;
  margin-top: 7px;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 1px;
  background: var(--primary);
  border-radius: 8px;
  box-shadow: 0 7px 18px rgba(47, 124, 246, 0.22);
  transition: background-color 160ms ease, transform 160ms ease;
}

.login-submit:hover:not(:disabled) {
  background: var(--primary-dark);
  transform: translateY(-1px);
}

.default-account {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  margin-top: 24px;
  padding: 12px 14px;
  color: #6b86a5;
  background: #f3f7fc;
  border: 1px solid #e7eef6;
  border-radius: 8px;
}

.default-account strong {
  color: #536e8c;
  font-size: 11px;
  font-weight: 550;
}

.default-account p {
  margin-top: 4px;
  font-size: 11px;
}

.security-note {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  margin-top: 23px;
  color: #9aa8b8;
  font-size: 11px;
}

.login-footer {
  position: absolute;
  bottom: 25px;
  color: #a1aebb;
  font-size: 11px;
}

.mobile-login-brand {
  display: none;
}

@media (max-width: 960px) {
  .login-page {
    grid-template-columns: minmax(360px, 0.8fr) minmax(450px, 1.2fr);
  }

  .login-brand-panel {
    padding: 32px;
  }

  .brand-hero h1 {
    font-size: 32px;
  }
}

@media (max-width: 760px) {
  .login-page {
    display: block;
    background: #f4f7fb;
  }

  .login-brand-panel {
    display: none;
  }

  .login-form-panel {
    min-height: 100vh;
    padding: 95px 24px 70px;
    background: #f4f7fb;
  }

  .login-box {
    max-width: 420px;
    padding: 30px 26px;
    background: #fff;
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: var(--shadow-hover);
  }

  .mobile-login-brand {
    position: absolute;
    top: 28px;
    left: 28px;
    display: flex;
    align-items: center;
    gap: 10px;
    color: var(--navy);
  }

  .mobile-login-brand .login-brand-symbol {
    width: 36px;
    height: 36px;
    flex-basis: 36px;
  }

  .login-heading h2 {
    font-size: 26px;
  }
}
</style>
