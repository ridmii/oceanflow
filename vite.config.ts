import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // Allow GLSL imports as raw strings
  assetsInclude: ['**/*.glsl'],
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
