import { defineConfig } from 'vite';

// build servita dalla LittleFS dell'ESP32
export default defineConfig({
  base: './',
  build: { outDir: '../firmware/data', emptyOutDir: true, assetsInlineLimit: 0, chunkSizeWarningLimit: 800 },
});
