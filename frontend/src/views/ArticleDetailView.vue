<script setup>
import { onMounted, ref } from "vue"
import { RouterLink, useRoute } from "vue-router"
import { getArticle } from "../api/articles"

const route = useRoute()
const article = ref(null)
const loading = ref(true)
const error = ref("")

onMounted(async () => {
  try {
    article.value = await getArticle(route.params.id)
  } catch (requestError) {
    error.value = "文章加载失败或文章不存在。"
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page-width detail-page">
    <RouterLink class="back-link" to="/">← 返回文章列表</RouterLink>
    <div v-if="loading" class="empty-state">
      正在加载文章……
    </div>

    <div v-else-if="error" class="empty-state">
      {{ error }}
    </div>

    <article v-else-if="article" class="article-detail">
      <header>
        <span class="article-category">OwnerBlog / 文章</span>

        <h1>{{ article.title }}</h1>

        <p class="detail-excerpt">
          {{ article.summary }}
        </p>

        <div class="detail-meta">
          <span>Owner</span>
          <time :datetime="article.published_at">
            {{ article.published_at }}
          </time>
        </div>
      </header>

      <div class="detail-body">
        <!-- 后端返回的是一整段 Markdown 字符串，不是数组 -->
        <p>{{ article.content }}</p>
      </div>
    </article>

    <div v-else class="empty-state">
      没有找到这篇文章。
    </div>
  </div>
</template>
