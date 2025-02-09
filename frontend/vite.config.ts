import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA, ManifestOptions } from 'vite-plugin-pwa';
import * as manifest from './manifest.json';

export default defineConfig({
  plugins: [
    tailwindcss(),
    VitePWA({
      registerType: 'prompt',
      injectRegister: 'auto',
      manifest: manifest.default as ManifestOptions,
      workbox: {
        globPatterns: ['**/*.{js,css,html}'],
      },
    }),
  ],
  build: {
    sourcemap: true,
  },
})
