<script setup lang="ts">
import {
  mdiAccountMultipleOutline,
  mdiAlertOctagonOutline,
  mdiChartBoxOutline,
  mdiCogOutline,
  mdiDatabaseImportOutline,
  mdiDomain,
  mdiEyeOutline,
  mdiGavel,
  mdiLogout,
  mdiMapMarkerPath,
  mdiMapMarkerRadiusOutline,
  mdiMenu,
  mdiPackageVariantClosed,
  mdiSpeedometer,
  mdiSwapHorizontal,
  mdiTruckOutline,
  mdiViewDashboardOutline,
  mdiWeatherNight,
  mdiWebhook,
  mdiWhiteBalanceSunny,
  mdiAccountGroupOutline,
  mdiWarehouse,
} from '@mdi/js'
import { useQueryClient } from '@tanstack/vue-query'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDisplay, useTheme } from 'vuetify'
import { errorMessage } from '@/api/http'
import type { Role } from '@/api/types'
import NameAvatar from '@/components/ui/NameAvatar.vue'
import { BRAND } from '@/config/brand'
import { ROLE_BY_VALUE, ROLES } from '@/constants/roles'
import { prefetchRoutes } from '@/router'
import { useAuthStore } from '@/stores/auth'
import { useNotify } from '@/stores/notify'
import { useOrgStore } from '@/stores/org'
import { useUiStore } from '@/stores/ui'
import { storage } from '@/utils/storage'

const auth = useAuthStore()
const orgStore = useOrgStore()
const ui = useUiStore()
const notify = useNotify()
const router = useRouter()
const route = useRoute()
const queryClient = useQueryClient()
const theme = useTheme()
const { mdAndUp } = useDisplay()

const drawer = ref(mdAndUp.value)
const rail = ref(storage.get('cp-rail') === '1')

onMounted(prefetchRoutes)

interface NavItem {
  title: string
  icon: string
  to?: string
  permission?: string
  soon?: boolean
}
interface NavGroup {
  label: string
  items: NavItem[]
}

const groups: NavGroup[] = [
  {
    label: '',
    items: [{ title: 'Control tower', icon: mdiViewDashboardOutline, to: '/' }],
  },
  {
    label: 'Operations',
    items: [
      { title: 'Shipments', icon: mdiPackageVariantClosed, to: '/shipments', permission: 'shipments.view' },
      { title: 'Live map', icon: mdiMapMarkerPath, to: '/live-map', permission: 'shipments.view' },
      { title: 'Exceptions', icon: mdiAlertOctagonOutline, to: '/exceptions', permission: 'exceptions.view' },
      { title: 'Trips', icon: mdiTruckOutline, permission: 'trips.view', soon: true },
    ],
  },
  {
    label: 'Procurement',
    items: [{ title: 'Tenders & bids', icon: mdiGavel, permission: 'tenders.view', soon: true }],
  },
  {
    label: 'Integration',
    items: [
      { title: 'Bulk imports', icon: mdiDatabaseImportOutline, permission: 'imports.manage', soon: true },
      { title: 'Webhooks', icon: mdiWebhook, permission: 'org.manage', soon: true },
    ],
  },
  {
    label: 'Master data',
    items: [
      { title: 'Parties', icon: mdiAccountGroupOutline, to: '/masterdata/parties', permission: 'masterdata.manage' },
      { title: 'Locations', icon: mdiMapMarkerRadiusOutline, to: '/masterdata/locations', permission: 'masterdata.manage' },
      { title: 'Carriers & fleet', icon: mdiWarehouse, to: '/masterdata/carriers', permission: 'masterdata.manage' },
    ],
  },
  {
    label: 'Insights',
    items: [
      { title: 'Reports', icon: mdiChartBoxOutline, permission: 'reports.view', soon: true },
      { title: 'Performance lab', icon: mdiSpeedometer, permission: 'audit.view', soon: true },
    ],
  },
  {
    label: 'Settings',
    items: [
      { title: 'Organization', icon: mdiDomain, to: '/settings/organization', permission: 'org.view' },
      { title: 'Team & roles', icon: mdiAccountMultipleOutline, to: '/settings/members', permission: 'members.view' },
    ],
  },
]
const visibleGroups = computed(() =>
  groups
    .map((g) => ({ ...g, items: g.items.filter((i) => !i.permission || orgStore.can(i.permission)) }))
    .filter((g) => g.items.length),
)
const isRail = computed(() => rail.value && mdAndUp.value)
const roleInfo = computed(() => (orgStore.role ? ROLE_BY_VALUE[orgStore.role] : null))

function toggleNav() {
  if (mdAndUp.value) {
    rail.value = !rail.value
    storage.set('cp-rail', rail.value ? '1' : '0')
  } else drawer.value = !drawer.value
}

const isDark = computed(() => theme.global.current.value.dark)
function toggleTheme() {
  const next = isDark.value ? 'light' : 'dark'
  theme.global.name.value = next
  storage.set('cp-theme', next)
}

function resetClientState() {
  orgStore.reset()
  queryClient.clear() // never show one tenant's (or role's) cached data under another
}

/** Demo only: hop between personas without typing credentials. */
async function switchDemoRole(role: Role) {
  if (role === orgStore.role) return
  ui.fullscreenMessage = `Switching to ${ROLE_BY_VALUE[role].label}…`
  try {
    await auth.logout()
    resetClientState()
    await auth.demoLogin(role)
    await orgStore.load(true)
    await router.replace('/')
  } catch (e) {
    ui.fullscreenMessage = null
    notify.error(errorMessage(e))
    router.push({ name: 'login' })
  }
}

async function logout() {
  ui.fullscreenMessage = 'Signing you out…'
  try {
    await auth.logout()
  } finally {
    resetClientState()
    router.push({ name: 'login' })
  }
}
</script>

<template>
  <v-navigation-drawer
    v-model="drawer"
    :rail="isRail"
    :temporary="!mdAndUp"
    :permanent="mdAndUp"
    width="264"
    rail-width="76"
    theme="dark"
    class="cp-sidebar"
    border="0"
  >
    <div class="d-flex align-center ga-3 px-4 pt-5 pb-4">
      <img src="/favicon.svg" width="34" height="34" alt="" class="flex-shrink-0" />
      <div v-if="!isRail" class="text-h6 font-weight-bold" style="letter-spacing: -0.02em">{{ BRAND.name }}</div>
    </div>

    <div class="cp-org mx-3 mb-3" :class="{ 'cp-org--rail': isRail }">
      <NameAvatar :name="orgStore.org?.name ?? '?'" :size="36" />
      <div v-if="!isRail" style="min-width: 0">
        <div class="text-body-2 font-weight-bold text-truncate">{{ orgStore.org?.name }}</div>
        <div class="text-caption text-truncate" style="opacity: 0.65">{{ roleInfo?.label }}</div>
      </div>
    </div>

    <v-list nav density="compact" class="px-2 pt-0">
      <template v-for="group in visibleGroups" :key="group.label">
        <div v-if="group.label && !isRail" class="cp-nav-label">{{ group.label }}</div>
        <v-divider v-else-if="group.label" class="my-2 mx-3" style="opacity: 0.15" />
        <v-tooltip v-for="item in group.items" :key="item.title" :text="item.title" location="end" :disabled="!isRail">
          <template #activator="{ props }">
            <v-list-item
              v-bind="props"
              :to="item.to"
              :exact="item.to === '/'"
              :prepend-icon="item.icon"
              :title="item.title"
              :disabled="item.soon"
              rounded="lg"
              class="cp-nav-item"
              active-class="cp-nav-item--active"
            >
              <template v-if="item.soon && !isRail" #append>
                <span class="cp-soon">Soon</span>
              </template>
            </v-list-item>
          </template>
        </v-tooltip>
      </template>
    </v-list>
  </v-navigation-drawer>

  <v-app-bar flat height="68" class="cp-appbar">
    <v-btn :icon="mdiMenu" variant="text" aria-label="Toggle navigation" @click="toggleNav" />
    <div class="ml-1" style="min-width: 0">
      <div class="text-subtitle-1 font-weight-bold text-truncate">{{ route.meta.title ?? BRAND.name }}</div>
      <div class="text-caption text-medium-emphasis text-truncate d-none d-sm-block">{{ orgStore.org?.name }}</div>
    </div>

    <v-spacer />

    <v-btn
      :icon="isDark ? mdiWhiteBalanceSunny : mdiWeatherNight"
      variant="text"
      :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
      @click="toggleTheme"
    />

    <v-menu offset="8">
      <template #activator="{ props }">
        <v-btn v-bind="props" icon aria-label="Account menu" class="mr-2 ml-1">
          <NameAvatar :name="auth.user?.full_name || auth.user?.email || '?'" :size="38" />
        </v-btn>
      </template>
      <v-card class="cp-card" min-width="280">
        <div class="d-flex align-center ga-3 pa-4">
          <NameAvatar :name="auth.user?.full_name || auth.user?.email || '?'" :size="42" />
          <div style="min-width: 0">
            <div class="font-weight-bold text-truncate">{{ auth.user?.full_name || 'My account' }}</div>
            <div class="text-caption text-medium-emphasis text-truncate">{{ auth.user?.job_title || auth.user?.email }}</div>
          </div>
        </div>
        <v-divider />
        <v-list density="comfortable">
          <v-list-item
            v-if="orgStore.can('org.view')"
            :prepend-icon="mdiCogOutline"
            title="Organization settings"
            to="/settings/organization"
          />
          <v-list-item :prepend-icon="mdiLogout" title="Sign out" base-color="error" @click="logout" />
        </v-list>
      </v-card>
    </v-menu>
  </v-app-bar>

  <v-main>
    <div v-if="auth.user?.is_demo" class="cp-demo-bar">
      <v-icon :icon="mdiEyeOutline" size="18" />
      <span>
        <strong>Live demo</strong> · you are the <strong>{{ roleInfo?.label }}</strong>. Create and edit freely — data
        resets nightly.
      </span>
      <v-spacer />
      <v-menu offset="6">
        <template #activator="{ props }">
          <v-btn v-bind="props" size="small" color="white" variant="flat" class="text-primary" :prepend-icon="mdiSwapHorizontal">
            Switch role
          </v-btn>
        </template>
        <v-card class="cp-card" min-width="300">
          <v-list density="comfortable">
            <v-list-item
              v-for="r in ROLES"
              :key="r.value"
              :prepend-icon="r.icon"
              :title="r.label"
              :subtitle="r.pitch"
              :active="r.value === orgStore.role"
              color="primary"
              @click="switchDemoRole(r.value)"
            />
          </v-list>
        </v-card>
      </v-menu>
    </div>
    <v-container fluid class="pa-4 pa-md-8" style="max-width: 1480px">
      <router-view v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <!-- Single wrapper element: pages with several root nodes can't be animated, which stalls out-in. -->
          <div :key="`${orgStore.currentId}-${route.path}`">
            <component :is="Component" />
          </div>
        </Transition>
      </router-view>
    </v-container>
  </v-main>
</template>

<style scoped>
.cp-sidebar {
  background: var(--cp-sidebar-gradient) !important;
}
.cp-demo-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding: 8px 20px;
  color: #fff;
  font-size: 0.875rem;
  background: var(--cp-brand-gradient);
}
.cp-appbar {
  background: rgba(var(--v-theme-background), 0.82) !important;
  backdrop-filter: saturate(180%) blur(12px);
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.cp-org {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.cp-org--rail {
  justify-content: center;
  padding: 8px;
}
.cp-nav-label {
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  opacity: 0.45;
  padding: 12px 12px 4px;
}
.cp-nav-item {
  margin-bottom: 1px !important;
  min-height: 38px !important;
}
.cp-sidebar :deep(.v-navigation-drawer__content) {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.15) transparent;
}
.cp-nav-item :deep(.v-list-item-title) {
  font-weight: 500;
  font-size: 0.9rem;
}
.cp-nav-item.v-list-item--disabled {
  opacity: 0.5;
}
.cp-nav-item--active {
  background: linear-gradient(90deg, rgba(34, 211, 238, 0.3), rgba(34, 211, 238, 0.08)) !important;
  color: #fff !important;
}
.cp-nav-item--active :deep(.v-list-item__overlay) {
  opacity: 0 !important;
}
.cp-soon {
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
}
</style>
