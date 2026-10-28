import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In development, forward /api to the FastAPI server so the frontend can use
// same-origin relative URLs everywhere (dev, Docker/nginx and Vercel).
export default defineConfig({
  plugins: [react()],
  // Recharts dominates the bundle (~180 kB gzipped); acceptable for a single-page dashboard.
  build: { chunkSizeWarningLimit: 700 },
  server: {
    proxy: {
      '/api': process.env.VITE_API_PROXY ?? 'http://127.0.0.1:8000',
    },
  },
})
