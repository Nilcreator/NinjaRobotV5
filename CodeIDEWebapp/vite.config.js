import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['websiteicon.ico', 'apple-touch-icon.png', 'masked-icon.svg'],
      manifest: {
        name: 'NinjaRobot Code',
        short_name: 'NinjaRobot',
        description: 'Visual coding platform for NinjaRobot V5',
        theme_color: '#ffffff',
        icons: [
          {
            src: 'src/assets/images/websiteicon.ico',
            sizes: '64x64 32x32 24x24 16x16',
            type: 'image/x-icon'
          },
          {
            src: 'src/assets/images/websiteicon.ico',
            sizes: '192x192',
            type: 'image/x-icon'
          },
          {
            src: 'src/assets/images/websiteicon.ico',
            sizes: '512x512',
            type: 'image/x-icon'
          }
        ]
      }
    })
  ],
})
