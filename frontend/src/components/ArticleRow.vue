<script setup>
import { RouterLink } from "vue-router"

defineProps({
  article: { type: Object, required: true },
})

function formatDate(value) {
  if (!value) return ""

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  return new Intl.DateTimeFormat(navigator.language, {
    dateStyle: "medium",
  }).format(date)
}
</script>

<template>
  <RouterLink class="article-row" :to="`/articles/${article.id}`">
    <div>
      <span class="article-category">OwnerBlog / 文章</span>
      <h3>{{ article.title }}</h3>
      <p>{{ article.summary }}</p>
    </div>
    <div class="article-meta">
      <time :datetime="article.published_at">{{ formatDate(article.published_at) }}</time>
      <span class="arrow" aria-hidden="true">↗</span>
    </div>
  </RouterLink>
</template>
