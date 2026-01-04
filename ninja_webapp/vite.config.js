import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

// https://vite.dev/config/
export default defineConfig({
    plugins: [react()],

    // Build output for FastAPI serving
    build: {
        outDir: 'dist',
        assetsDir: 'assets',
        emptyOutDir: true,
    },

    // Development server proxy for API calls
    server: {
        port: 5173,
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
            '/ws': {
                target: 'ws://localhost:8000',
                ws: true,
            },
        },
    },

    // Resolve aliases for cleaner imports
    resolve: {
        alias: {
            '@': resolve(__dirname, 'src'),
            '@components': resolve(__dirname, 'src/components'),
            '@pages': resolve(__dirname, 'src/pages'),
            '@services': resolve(__dirname, 'src/services'),
            '@hooks': resolve(__dirname, 'src/hooks'),
        },
    },
});
