<script setup lang="ts">
import { mdiAccountOutline, mdiEmailOutline, mdiLockOutline } from '@mdi/js'
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage, fieldErrors } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import AuthShell from '../components/AuthShell.vue'

const auth = useAuthStore()
const router = useRouter()

const form = reactive({ full_name: '', email: '', password: '' })
const busy = ref(false)
const error = ref('')
const errors = ref<Record<string, string>>({})

async function submit() {
  busy.value = true
  error.value = ''
  errors.value = {}
  try {
    await auth.register(form)
    await router.replace({ name: 'onboarding' })
  } catch (e) {
    errors.value = fieldErrors(e)
    error.value = Object.keys(errors.value).length ? '' : errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AuthShell
    title="Create your account"
    subtitle="Start your own forwarding workspace in under a minute."
    :busy="busy"
    busy-message="Creating your account…"
  >
    <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mb-4" :text="error" />
    <v-form @submit.prevent="submit">
      <v-text-field
        v-model="form.full_name"
        label="Full name"
        autocomplete="name"
        :prepend-inner-icon="mdiAccountOutline"
        :error-messages="errors.full_name"
        class="mb-2"
      />
      <v-text-field
        v-model="form.email"
        label="Work email"
        type="email"
        autocomplete="email"
        :prepend-inner-icon="mdiEmailOutline"
        :error-messages="errors.email"
        class="mb-2"
      />
      <v-text-field
        v-model="form.password"
        label="Password"
        type="password"
        autocomplete="new-password"
        hint="At least 8 characters, not too common."
        :prepend-inner-icon="mdiLockOutline"
        :error-messages="errors.password"
      />
      <v-btn
        type="submit"
        color="primary"
        size="large"
        block
        class="mt-4"
        :disabled="!form.full_name || !form.email || form.password.length < 8"
      >
        Create account
      </v-btn>
    </v-form>
    <div class="text-body-2 text-center text-medium-emphasis mt-6">
      Just looking? <router-link :to="{ name: 'login' }" class="text-primary font-weight-bold">Try the live demo</router-link>
    </div>
  </AuthShell>
</template>
