import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// 用 URL 解析项目目录，避免依赖 node 类型
const srcDir = decodeURIComponent(new URL('./src', import.meta.url).pathname)

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': srcDir,
    },
  },
  server: {
    port: 5173,
    proxy: {
      // 开发期把 /api 转发到本地 FastAPI，前端不写死地址
      '/api': 'http://127.0.0.1:8000',
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
