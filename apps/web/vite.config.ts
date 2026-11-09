import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 开发期：/api 反向代理到本地后端，前端不需要知道后端地址。
// 生产期：请用同源部署（后端 main.py 会托管 apps/web/dist），因此 base 为空。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8077',
        changeOrigin: true,
      },
      // 自绘教学图是后端静态路由，开发期一并代理
      '/figures': {
        target: 'http://127.0.0.1:8077',
        changeOrigin: true,
      },
    },
  },
  // npm run preview 也走同样的代理，便于用生产构建做联调
  preview: {
    port: 4173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8077',
        changeOrigin: true,
      },
      '/figures': {
        target: 'http://127.0.0.1:8077',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 900,
  },
});
