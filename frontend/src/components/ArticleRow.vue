<script setup>
import { RouterLink } from "vue-router"

defineProps({
  article: { type: Object, required: true },
})
</script>

<template>
  <RouterLink class="article-row" :to="`/articles/${article.id}`">
    <div>
      <span class="article-category">原创 · {{ article.category }}</span>
      <h3>{{ article.title }}</h3>
      <p>{{ article.excerpt }}</p>
    </div>
    <div class="article-meta">
      <span>{{ article.publishedAt }}</span>
      <span>{{ article.wordCount }}</span>
      <span>评论 {{ article.commentsCount }}</span>
      <span class="arrow" aria-hidden="true">↗</span>
    </div>
  </RouterLink>
</template>
