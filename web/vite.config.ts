import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig(() => ({
  plugins: [react()],
  // Served at the root of structnode.juhongstructural.com (a CNAME'd
  // custom domain -- see public/CNAME), not under a /structnode/ subpath.
  base: '/',
}))
