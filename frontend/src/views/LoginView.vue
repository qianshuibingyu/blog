<script setup>
import { ref } from "vue"
import { RouterLink, useRouter } from "vue-router"
import { login } from "../api/auth"

const router = useRouter()
const username = ref("")
const password = ref("")
const errorMessage = ref("")
const submitting = ref(false)

async function submitLogin() {
  errorMessage.value = ""
  submitting.value = true

  try {
    await login(username.value, password.value)
    router.push("/")
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || "登录失败，请检查后端服务。"
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page-width login-page">
    <RouterLink class="back-link" to="/">← 返回首页</RouterLink>
    <section class="login-panel">
      <p class="section-label">OwnerBlog / 登录</p>
      <h1>回来继续<br /><em>写点什么。</em></h1>
      <p class="login-intro">使用已经配置好的 Django 账号登录。当前 MVP 不开放公开注册。</p>
      <form class="login-form" @submit.prevent="submitLogin">
        <label for="username">用户名</label>
        <input id="username" v-model="username" autocomplete="username" required />
        <label for="password">密码</label>
        <input id="password" v-model="password" type="password" autocomplete="current-password" required />
        <p v-if="errorMessage" class="login-error" role="alert">{{ errorMessage }}</p>
        <button class="solid-button" type="submit" :disabled="submitting">{{ submitting ? "登录中……" : "登录" }}</button>
      </form>
    </section>
  </div>
</template>
