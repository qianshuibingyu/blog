<script setup>
import { onMounted, ref } from "vue"
import { RouterLink, RouterView } from "vue-router"
import { getCurrentUser, logout } from "./api/auth"

const currentUser = ref(null)

onMounted(async () => {
  try {
    currentUser.value = await getCurrentUser()
  } catch {
    currentUser.value = null
  }
})

async function signOut() {
  await logout()
  currentUser.value = null
}

const particles = Array.from({ length: 34 }, (_, index) => ({
  id: index,
  left: `${(index * 37) % 100}%`,
  top: `${(index * 61) % 100}%`,
  delay: `${(index % 9) * -0.7}s`,
  duration: `${5 + (index % 5)}s`,
}))
</script>

<template>
  <div class="site-shell">
    <div class="tech-background" aria-hidden="true">
      <div class="tech-grid"></div>
      <span
        v-for="particle in particles"
        :key="particle.id"
        class="particle"
        :style="{ left: particle.left, top: particle.top, animationDelay: particle.delay, animationDuration: particle.duration }"
      ></span>
      <span class="tech-orbit tech-orbit-one"></span>
      <span class="tech-orbit tech-orbit-two"></span>
    </div>
    <header class="site-header page-width">
      <RouterLink class="brand" to="/" aria-label="返回首页">
        <span class="brand-mark">O</span>
        <span>OwnerBlog</span>
      </RouterLink>
      <nav class="site-nav" aria-label="主导航">
        <RouterLink to="/">文章</RouterLink>
        <RouterLink to="/knowledge">问答</RouterLink>
      </nav>
      <div v-if="currentUser" class="account-actions">
        <span class="account-name">{{ currentUser.username }}</span>
        <button class="text-button" type="button" @click="signOut">退出</button>
      </div>
      <RouterLink v-else class="text-button login-link" to="/login">登录</RouterLink>
    </header>

    <main><RouterView /></main>

    <footer class="site-footer page-width">
      <span>OwnerBlog</span>
      <span>一个人的开发记录、学习笔记和日常想法。</span>
    </footer>
  </div>
</template>
