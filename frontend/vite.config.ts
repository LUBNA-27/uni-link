import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// Same-origin in production (FastAPI serves /dist). In dev, proxy /api to FastAPI on :8000.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: './',
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
