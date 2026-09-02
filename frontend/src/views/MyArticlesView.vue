<script setup>
import { onMounted, ref } from "vue"
import { RouterLink, useRouter } from "vue-router"
import {
  createArticle,
  deleteArticle,
  getMyArticles,
  submitArticleReview,
  updateArticle,
} from "../api/articles"

// 用于未登录时跳转到登录页。
const router = useRouter()
// 当前用户的全部文章，包括草稿和待审核文章。
const articles = ref([])
// 首次加载文章时显示加载状态。
const loading = ref(true)
// 保存、删除和提交审核时防止重复点击。
const submitting = ref(false)
// 页面展示的错误信息。
const errorMessage = ref("")
// null 表示创建文章，有数字表示正在编辑文章。
const editingId = ref(null)
// 表单与模板通过 v-model 双向同步。
const form = ref({ title: "", summary: "", content: "" })

// 将后端状态转换成用户可以理解的中文标签。
function statusLabel(status) {
  const labels = {
    draft: "草稿",
    pending_review: "待审核",
    published: "已发布",
  }
  return labels[status] || status
}

// 清空表单并退出编辑状态。
function resetForm() {
  editingId.value = null
  form.value = { title: "", summary: "", content: "" }
}

// 处理登录失效，保留登录后要返回的页面。
function redirectToLogin() {
  router.push({ path: "/login", query: { next: "/my-articles" } })
}

// 读取当前登录用户的全部文章。
async function loadArticles() {
  loading.value = true
  errorMessage.value = ""

  try {
    articles.value = await getMyArticles()
  } catch (error) {
    if (error.response?.status === 401) {
      redirectToLogin()
      return
    }
    errorMessage.value = !error.response
      ? "无法连接后端服务。"
      : error.response.data?.detail || "文章加载失败。"
  } finally {
    loading.value = false
  }
}

// 将草稿内容填入表单，进入编辑状态。
function startEdit(article) {
  editingId.value = article.id
  form.value = {
    title: article.title,
    summary: article.summary,
    content: article.content,
  }
}

// 根据 editingId 判断当前操作是创建还是更新。
async function saveArticle() {
  submitting.value = true
  errorMessage.value = ""

  try {
    if (editingId.value === null) {
      await createArticle(form.value)
    } else {
      await updateArticle(editingId.value, form.value)
    }
    resetForm()
    await loadArticles()
  } catch (error) {
    if (error.response?.status === 401) {
      redirectToLogin()
      return
    }
    errorMessage.value = error.response?.data?.detail || "保存文章失败。"
  } finally {
    submitting.value = false
  }
}

// 删除文章并刷新列表。
async function removeArticle(id) {
  if (!window.confirm("确定删除这篇文章吗？")) return

  submitting.value = true
  errorMessage.value = ""

  try {
    await deleteArticle(id)
    await loadArticles()
  } catch (error) {
    if (error.response?.status === 401) {
      redirectToLogin()
      return
    }
    errorMessage.value = error.response?.data?.detail || "删除文章失败。"
  } finally {
    submitting.value = false
  }
}

// 将草稿提交为待审核状态并刷新列表。
async function submitReview(id) {
  submitting.value = true
  errorMessage.value = ""

  try {
    await submitArticleReview(id)
    await loadArticles()
  } catch (error) {
    if (error.response?.status === 401) {
      redirectToLogin()
      return
    }
    errorMessage.value = error.response?.data?.detail || "提交审核失败。"
  } finally {
    submitting.value = false
  }
}

// 页面加载后读取文章。
onMounted(loadArticles)
</script>

<template>
  <div class="page-width my-articles-page">
    <RouterLink class="back-link" to="/">返回文章列表</RouterLink>

    <section class="my-articles-header">
      <p class="section-label">OwnerBlog / 个人中心</p>
      <h1>我的文章</h1>
      <p>管理草稿、查看审核状态，并继续完成你的写作。</p>
    </section>

    <section class="article-editor">
      <div class="section-heading">
        <h2>{{ editingId === null ? "创建草稿" : "编辑草稿" }}</h2>
        <button v-if="editingId !== null" class="line-button" type="button" @click="resetForm">
          取消编辑
        </button>
      </div>

      <form class="article-form" @submit.prevent="saveArticle">
        <label for="article-title">标题</label>
        <input id="article-title" v-model="form.title" required />
        <label for="article-summary">摘要</label>
        <textarea id="article-summary" v-model="form.summary" rows="3"></textarea>
        <label for="article-content">正文</label>
        <textarea id="article-content" v-model="form.content" rows="10" required></textarea>
        <button class="solid-button" type="submit" :disabled="submitting">
          {{ submitting ? "保存中……" : editingId === null ? "创建草稿" : "保存修改" }}
        </button>
      </form>

      <p v-if="errorMessage" class="login-error" role="alert">{{ errorMessage }}</p>
    </section>

    <section class="my-article-list">
      <div class="section-heading">
        <h2>文章列表</h2>
        <span class="section-count">{{ articles.length }} 篇</span>
      </div>
      <p v-if="loading" class="empty-state">正在加载文章……</p>
      <p v-else-if="!articles.length" class="empty-state">还没有文章，先创建一篇草稿吧。</p>

      <article v-for="article in articles" v-else :key="article.id" class="my-article-item">
        <div>
          <div class="my-article-meta">
            <span class="status-label" :class="`status-${article.status}`">{{ statusLabel(article.status) }}</span>
            <span>#{{ article.id }}</span>
          </div>
          <h3>{{ article.title }}</h3>
          <p>{{ article.summary || "暂无摘要" }}</p>
        </div>
        <div class="my-article-actions">
          <button v-if="article.status === 'draft'" class="line-button" type="button" :disabled="submitting" @click="startEdit(article)">编辑</button>
          <button v-if="article.status === 'draft'" class="line-button" type="button" :disabled="submitting" @click="removeArticle(article.id)">删除</button>
          <button v-if="article.status === 'draft'" class="solid-button" type="button" :disabled="submitting" @click="submitReview(article.id)">提交审核</button>
        </div>
      </article>
    </section>
  </div>
</template>
