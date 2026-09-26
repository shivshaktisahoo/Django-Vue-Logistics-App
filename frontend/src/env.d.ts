/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_MAP_TILES_LIGHT?: string
  readonly VITE_MAP_TILES_DARK?: string
  readonly VITE_MAP_ATTRIBUTION?: string
}
