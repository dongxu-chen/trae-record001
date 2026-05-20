import { createApp } from 'vue'
import { VueQueryPlugin } from '@tanstack/vue-query'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import router from './router'
import { vueQueryConfig } from './config/vue-query'
import 'highlight.js/styles/github-dark.css'

const app = createApp(App)

app.use(createPinia())
app.use(VueQueryPlugin, vueQueryConfig)
app.use(router)

app.mount('#app')
