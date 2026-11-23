import { createApp } from 'vue'

import App from './app/App.vue'
import router from './app/router'
import { initTheme } from './shared/theme'
import './shared/styles.css'

initTheme()

createApp(App).use(router).mount('#app')
