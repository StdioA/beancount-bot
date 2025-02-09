import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA, ManifestOptions } from 'vite-plugin-pwa';
import manifest from './manifest.json';

export default defineConfig({
  plugins: [
    tailwindcss(),
    VitePWA({
      includeAssets: ["apple-touch-icon-180x180.png","beancount.svg","maskable-icon-512x512.png","pwa-512x512.png", "beancount.png","favicon.ico","pwa-192x192.png","pwa-64x64.png"],
      registerType: 'prompt',
      injectRegister: 'auto',
      manifest: manifest as ManifestOptions,
      workbox: {
        globPatterns: ['**/*.{js,css,html}'],
      },
    }),
  ],
  build: {
    sourcemap: false,
  },
})
