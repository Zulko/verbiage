import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    svelte({ runes: true }),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['logo.svg', 'logo192.png', 'logo512.png', 'calendar-icon.svg', 'github-icon.svg'],
      manifest: {
        name: 'Verbiage',
        short_name: 'Verbiage',
        description: 'A word clues game with new puzzles on Tuesdays and Fridays',
        start_url: '.',
        scope: '.',
        display: 'standalone',
        background_color: '#ffffff',
        theme_color: '#6b6d6e',
        icons: [
          {
            src: 'logo192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: 'logo512.png',
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: 'logo512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,webmanifest,svg,png}'],
        runtimeCaching: [
          {
            urlPattern: /\/puzzles\/.*\.json\.gz$/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'puzzles',
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
        ],
      },
    }),
  ],
  // base: process.env.NODE_ENV === "production" ? "/verbiage/" : "/",
})
