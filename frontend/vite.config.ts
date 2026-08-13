import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // 本机 vite dev 时代理到后端容器
      '/api': { target: 'http://localhost:8000', changeOrigin: true }
    }
  }
})
