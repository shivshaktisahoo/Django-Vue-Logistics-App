/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import vuetify from 'vite-plugin-vuetify'
import { BRAND } from './src/config/brand'

// Lets index.html use %VITE_BRAND_NAME% / %VITE_BRAND_TAGLINE%.
process.env.VITE_BRAND_NAME ??= BRAND.name
process.env.VITE_BRAND_TAGLINE ??= BRAND.tagline

export default defineConfig({
  plugins: [
    vue(),
    // Auto-imports only the Vuetify components actually used (tree-shaking).
    vuetify({ autoImport: true }),
  ],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: {
      // Same-origin API in dev (and via host rewrites in prod) so the httpOnly refresh cookie just works.
      '/api': { target: process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000', changeOrigin: true },
    },
  },
  build: {
    target: 'es2022',
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ['vue', 'vue-router', 'pinia'],
          query: ['@tanstack/vue-query', 'axios'],
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    server: { deps: { inline: ['vuetify'] } },
  },
})
