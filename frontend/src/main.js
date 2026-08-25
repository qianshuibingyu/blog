import { createApp } from "vue"
import { createRouter, createWebHistory } from "vue-router"
import App from "./App.vue"
import ArticleListView from "./views/ArticleListView.vue"
import ArticleDetailView from "./views/ArticleDetailView.vue"
import KnowledgeView from "./views/KnowledgeView.vue"
import LoginView from "./views/LoginView.vue"
import "./styles/global.css"
import HealthView from "./views/HealthView.vue"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: ArticleListView },
    { path: "/articles/:id", component: ArticleDetailView },
    { path: "/knowledge", component: KnowledgeView },
    { path: "/login", component: LoginView },
    { path: "/health", component: HealthView },
  ],
})

createApp(App).use(router).mount("#app")
