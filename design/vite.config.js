import { defineConfig } from 'vite'
import { fileURLToPath } from 'url'

export default defineConfig({
  plugins: [],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '~': fileURLToPath(new URL('./node_modules/', import.meta.url)),
    }
  },
  build: {
    outDir: '../multifactor/static/multifactor',
    emptyOutDir: false,
    rollupOptions: {
      input: {
        multifactor: fileURLToPath(new URL('./src/multifactor.js', import.meta.url)),
      },
      output: {
        entryFileNames: `[name].js`,
        assetFileNames: `[name].[ext]`
      }
    },
  }
})