import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The dashboard talks to the Java backend. In dev we proxy /api -> :8080 so the
// frontend code always fetches a relative path and CORS never enters the picture.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_URL || 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
});
