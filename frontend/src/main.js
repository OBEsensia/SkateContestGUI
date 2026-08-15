import { createApp } from 'vue';
import App from './App.vue';
import router from './router.js';

const app = createApp(App);

// Inject the router into the Vue application
app.use(router);

// Mount the app to the <div id="app"> in index.html
app.mount('#app');
