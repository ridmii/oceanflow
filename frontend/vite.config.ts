import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // Allow GLSL imports as raw strings
  assetsInclude: ['**/*.glsl'],
  resolve: {
    dedupe: ['three', '@react-three/fiber', '@react-three/drei'],
  },
  optimizeDeps: {
    force: true,
    exclude: ['three-globe'],
    include: ['three-globe > frame-ticker', 'three-globe > tinycolor2'],
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    target: 'es2022',
    rollupOptions: {
      output: {
        manualChunks: {
          three: ['three'],
          r3f: ['@react-three/fiber', '@react-three/drei'],
          globe: ['three-globe'],
        },
      },
    },
  },
  worker: {
    format: 'es',
  },
});
