import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig, loadEnv} from 'vite';

export default defineConfig(({mode}) => {
  // VITE_API_PROXY_TARGET: where the dev server forwards /api (FastAPI). Never a production URL.
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  const apiTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000';

  const proxy = {
    '/api': {target: apiTarget, changeOrigin: true, ws: true},
  };

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
        '@app': path.resolve(__dirname, 'src/app'),
        '@shared': path.resolve(__dirname, 'src/shared'),
        '@modules': path.resolve(__dirname, 'src/modules'),
      },
    },
    server: {
      port: 5173,
      proxy,
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modify—file watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Disable file watching when DISABLE_HMR is true to save CPU during agent edits.
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
    },
    preview: {port: 4173, proxy},
  };
});
