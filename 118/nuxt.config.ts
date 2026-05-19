export default defineNuxtConfig({
  devtools: { enabled: true },
  runtimeConfig: {
    databaseUrl: process.env.DATABASE_URL || 'mysql://root:password@localhost:3306/ebook_reader',
    vapidPublicKey: process.env.VAPID_PUBLIC_KEY || '',
    vapidPrivateKey: process.env.VAPID_PRIVATE_KEY || '',
    public: {
      apiBase: '/api',
      vapidPublicKey: process.env.VAPID_PUBLIC_KEY || ''
    }
  },
  nitro: {
    plugins: ['~/server/plugins/multer.ts']
  },
  app: {
    head: {
      title: '电子书阅读器',
      meta: [
        { name: 'description', content: '支持离线阅读的现代化电子书阅读器' },
        { name: 'theme-color', content: '#667eea' },
        { name: 'apple-mobile-web-app-capable', content: 'yes' },
        { name: 'apple-mobile-web-app-status-bar-style', content: 'black-translucent' },
        { name: 'apple-mobile-web-app-title', content: 'EPUB Reader' }
      ],
      link: [
        { rel: 'manifest', href: '/manifest.json' },
        { rel: 'apple-touch-icon', href: '/icons/icon-192x192.png' },
        { rel: 'icon', type: 'image/png', href: '/icons/icon-96x96.png' }
      ]
    }
  },
  plugins: [
    '~/plugins/pwa.client.ts'
  ]
})
