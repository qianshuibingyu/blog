<script setup>
import { onMounted, ref } from "vue"
import { RouterLink, useRoute } from "vue-router"
import { getArticle } from "../api/articles"

const route = useRoute()
const article = ref(null)
onMounted(async () => { article.value = await getArticle(route.params.id) })
</script>

<template>
  <div class="page-width detail-page">
    <RouterLink class="back-link" to="/">← 返回文章列表</RouterLink>
    <article v-if="article" class="article-detail">
      <header><span class="article-category">原创 · {{ article.category }}</span><h1>{{ article.title }}</h1><p class="detail-excerpt">{{ article.excerpt }}</p><div class="detail-meta"><span>Owner</span><span>{{ article.publishedAt }}</span><span>{{ article.wordCount }}</span><span>{{ article.readTime }}</span><span>评论 {{ article.commentsCount }}</span></div><div class="detail-tags"><span v-for="tag in article.tags" :key="tag">#{{ tag }}</span></div></header>
      <div class="detail-body"><p v-for="paragraph in article.content" :key="paragraph">{{ paragraph }}</p></div>
      <section class="comments-section" aria-labelledby="comments-title"><div class="section-heading"><span id="comments-title" class="section-label">评论</span><span class="section-rule"></span><span class="section-count">{{ article.commentsCount }} 条</span></div><p class="comments-note">登录后可以参与讨论。评论会在审核通过后公开。</p></section>
    </article>
    <div v-else class="empty-state">没有找到这篇文章。</div>
  </div>
</template>
