import { createRouter, createWebHistory } from 'vue-router'
import { isAuthenticated, getAuthStatus } from '../api/auth'
import HomeView from '../views/HomeView.vue'
import OutlineView from '../views/OutlineView.vue'
import GenerateView from '../views/GenerateView.vue'
import ResultView from '../views/ResultView.vue'
import HistoryView from '../views/HistoryView.vue'
import SettingsView from '../views/SettingsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue')
    },
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/outline',
      name: 'outline',
      component: OutlineView
    },
    {
      path: '/generate',
      name: 'generate',
      component: GenerateView
    },
    {
      path: '/result',
      name: 'result',
      component: ResultView
    },
    {
      path: '/history',
      name: 'history',
      component: HistoryView
    },
    {
      path: '/history/:id',
      name: 'history-detail',
      component: HistoryView
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView
    }
  ]
})

// 路由守卫：未登录时跳转登录页
let _authEnabled: boolean | null = null

async function checkAuthEnabled(): Promise<boolean> {
  if (_authEnabled !== null) return _authEnabled
  _authEnabled = await getAuthStatus()
  return _authEnabled
}

router.beforeEach(async (to) => {
  // 登录页总是放行
  if (to.name === 'login') {
    return true
  }

  const authEnabled = await checkAuthEnabled()

  // 认证未启用，放行
  if (!authEnabled) {
    return true
  }

  // 认证已启用，检查 token
  if (isAuthenticated()) {
    return true
  }

  // 未登录，跳转登录页
  return { name: 'login', query: { redirect: to.fullPath } }
})

export default router
