/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/upload': 'http://localhost:8000',
    }
  },
  optimizeDeps: {
    exclude: ['lucide-react']
  },
  build: {
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        manualChunks: undefined
      }
    }
  },
  test: {
    // Пока тестируем только чистые утилиты — jsdom не нужен.
    // Добавим `environment: 'jsdom'` + `@testing-library/react`, когда начнём тестировать компоненты.
    environment: 'node',
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    globals: false,
    reporters: ['default'],
  }
});
