import { createApp } from 'vue'
import VueKonva from 'vue-konva'
import App from './App.vue'
import './styles/global.css'

const app = createApp(App)
app.use(VueKonva)
app.mount('#app')
