import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte({runes: true})],
  // base: process.env.NODE_ENV === "production" ? "/verbiage/" : "/",
});
