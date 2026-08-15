import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  base: './',
  build: {
    // Outputs the compiled files directly to the Python backend
    outDir: '../backend/static',
    // Empties the folder before building to remove old files
    emptyOutDir: true,
  }
});
