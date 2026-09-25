import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { BRAND } from '@/config/brand'
import { useAuthStore } from '@/stores/auth'
import { useOrgStore } from '@/stores/org'
import { useUiStore } from '@/stores/ui'

declare module 'vue-router' {
  interface RouteMeta {
    guest?: boolean // only for signed-out users
    public?: boolean // no auth needed
    permission?: string // RBAC code required in the current org
    title?: string
  }
}

// Every page is lazy-loaded so the initial bundle stays small.
const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/modules/auth/pages/LoginPage.vue'),
    meta: { guest: true, title: 'Sign in' },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/modules/auth/pages/RegisterPage.vue'),
    meta: { guest: true, title: 'Create account' },
  },
  {
    path: '/onboarding',
    name: 'onboarding',
    component: () => import('@/modules/settings/pages/OnboardingPage.vue'),
    meta: { title: 'Set up your organization' },
  },
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('@/modules/dashboard/pages/DashboardPage.vue'),
        meta: { title: 'Control tower' },
      },
      {
        path: 'settings/organization',
        name: 'org-settings',
        component: () => import('@/modules/settings/pages/OrgSettingsPage.vue'),
        meta: { permission: 'org.view', title: 'Organization' },
      },
      {
        path: 'settings/members',
        name: 'members',
        component: () => import('@/modules/settings/pages/MembersPage.vue'),
        meta: { permission: 'members.view', title: 'Team & roles' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  useUiStore().navigating = true
  const auth = useAuthStore()
  await auth.bootstrap()

  if (to.meta.public) return true
  if (to.meta.guest) return auth.isAuthenticated ? { name: 'dashboard' } : true
  if (!auth.isAuthenticated) return { name: 'login', query: to.path === '/' ? {} : { redirect: to.fullPath } }

  const org = useOrgStore()
  await org.load()
  if (!org.current && to.name !== 'onboarding') return { name: 'onboarding' }
  if (to.meta.permission && !org.can(to.meta.permission)) return { name: 'dashboard' }
  return true
})

router.afterEach((to) => {
  const ui = useUiStore()
  ui.navigating = false
  ui.fullscreenMessage = null // e.g. "Signing you in…" ends when the next page is shown
  document.title = to.meta.title ? `${to.meta.title} · ${BRAND.name}` : BRAND.name
})

router.onError(() => {
  const ui = useUiStore()
  ui.navigating = false
  ui.fullscreenMessage = null
})

let prefetched = false
/** Download every lazy page chunk while the browser is idle, so later navigation is instant. */
export function prefetchRoutes() {
  if (prefetched) return
  prefetched = true
  const run = () => {
    for (const record of router.getRoutes()) {
      const loader = record.components?.default
      if (typeof loader === 'function') (loader as () => Promise<unknown>)().catch(() => {})
    }
  }
  if ('requestIdleCallback' in window) window.requestIdleCallback(run, { timeout: 3000 })
  else setTimeout(run, 1500)
}
