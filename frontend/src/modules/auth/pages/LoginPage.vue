<script setup lang="ts">
import { mdiArrowRight, mdiEmailOutline, mdiEyeOffOutline, mdiEyeOutline, mdiLockOutline } from '@mdi/js'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage, fieldErrors } from '@/api/http'
import type { Role } from '@/api/types'
import { ROLES } from '@/constants/roles'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import AuthShell from '../components/AuthShell.vue'
import ServerStatus from '../components/ServerStatus.vue'

const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const busy = ref(false)
const pendingRole = ref<Role | null>(null)
const error = ref('')
const errors = ref<Record<string, string>>({})

function goNext() {
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
  return router.replace(redirect)
}

async function demo(role: Role) {
  pendingRole.value = role
  error.value = ''
  try {
    await auth.demoLogin(role)
    ui.fullscreenMessage = 'Opening your control tower…'
    await goNext()
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    pendingRole.value = null
  }
}

async function submit() {
  busy.value = true
  error.value = ''
  errors.value = {}
  try {
    await auth.login(email.value, password.value)
    ui.fullscreenMessage = 'Signing you in…'
    await goNext()
  } catch (e) {
    errors.value = fieldErrors(e)
    error.value = Object.keys(errors.value).length ? '' : errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthShell title="Explore the live demo" subtitle="Pick a persona — no signup needed." :busy="busy" busy-message="Signing in…">
    <ServerStatus class="mb-5" />

    <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mb-4" :text="error" />

    <div class="cp-roles mb-8">
      <button
        v-for="r in ROLES"
        :key="r.value"
        type="button"
        class="cp-role"
        :disabled="!!pendingRole"
        :data-testid="`demo-${r.value}`"
        @click="demo(r.value)"
      >
        <v-avatar :color="r.color" variant="tonal" rounded="lg" size="40">
          <v-progress-circular v-if="pendingRole === r.value" indeterminate size="20" width="2" />
          <v-icon v-else :icon="r.icon" size="22" />
        </v-avatar>
        <div class="text-left" style="min-width: 0">
          <div class="font-weight-bold d-flex align-center ga-1">
            {{ r.label }} <v-icon :icon="mdiArrowRight" size="16" class="cp-role__arrow" />
          </div>
          <div class="text-caption text-medium-emphasis">{{ r.pitch }}</div>
        </div>
      </button>
    </div>

    <div class="d-flex align-center ga-3 mb-6">
      <v-divider />
      <span class="text-caption text-medium-emphasis text-no-wrap">or sign in with email</span>
      <v-divider />
    </div>

    <v-form @submit.prevent="submit">
      <v-text-field
        v-model="email"
        label="Work email"
        type="email"
        autocomplete="username"
        :prepend-inner-icon="mdiEmailOutline"
        :error-messages="errors.email"
        class="mb-2"
      />
      <v-text-field
        v-model="password"
        label="Password"
        :type="showPassword ? 'text' : 'password'"
        autocomplete="current-password"
        :prepend-inner-icon="mdiLockOutline"
        :append-inner-icon="showPassword ? mdiEyeOffOutline : mdiEyeOutline"
        :error-messages="errors.password"
        @click:append-inner="showPassword = !showPassword"
      />
      <v-btn type="submit" color="primary" size="large" block class="mt-2" :disabled="!email || !password">
        Sign in
      </v-btn>
    </v-form>

    <div class="text-body-2 text-center text-medium-emphasis mt-6">
      New here? <router-link :to="{ name: 'register' }" class="text-primary font-weight-bold">Create an account</router-link>
    </div>
  </AuthShell>
</template>

<style scoped>
.cp-roles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 12px;
}
.cp-role {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px;
  border-radius: 14px;
  text-align: left;
  color: inherit;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-border-color), 0.12);
  box-shadow: var(--cp-shadow-sm);
  transition:
    transform 0.15s ease,
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}
.cp-role:hover:not(:disabled),
.cp-role:focus-visible {
  transform: translateY(-2px);
  border-color: rgba(var(--v-theme-primary), 0.5);
  box-shadow: var(--cp-shadow-md);
  outline: none;
}
.cp-role:disabled {
  opacity: 0.7;
  cursor: progress;
}
.cp-role__arrow {
  opacity: 0;
  transform: translateX(-4px);
  transition: all 0.15s ease;
}
.cp-role:hover .cp-role__arrow {
  opacity: 1;
  transform: none;
}
</style>
