import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  // GitHub Pages serves this repo at /structnode/, not the domain root.
  base: mode === 'gh-pages' ? '/structnode/' : '/',
}))
