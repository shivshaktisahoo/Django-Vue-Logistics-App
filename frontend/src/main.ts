import '@fontsource-variable/inter/wght.css'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { configureSession } from '@/api/http'
import vuetify from '@/plugins/vuetify'
import { router } from '@/router'
import { useAuthStore } from '@/stores/auth'
import { useOrgStore } from '@/stores/org'
import App from './App.vue'
import './styles/main.css'

const app = createApp(App)
const pinia = createPinia()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000, // serve cached data instantly; revalidate in background
      gcTime: 10 * 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

app.use(pinia).use(router).use(vuetify).use(VueQueryPlugin, { queryClient })

const auth = useAuthStore()
const orgStore = useOrgStore()
configureSession({
  onRefreshed: (res) => auth.applySession(res),
  onExpired: () => {
    auth.clearSession()
    orgStore.reset()
    queryClient.clear()
    router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
  },
})

// Restore the saved org header before the first API call.
orgStore.select(orgStore.currentId)

// Keep the HTML splash visible until the session check and first route are resolved.
router.isReady().then(() => app.mount('#app'))
