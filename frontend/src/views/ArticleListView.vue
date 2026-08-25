<script setup>
import { computed, onMounted, ref } from "vue"
import { RouterLink } from "vue-router"
import ArticleRow from "../components/ArticleRow.vue"
import { getArticles } from "../api/articles"

const articles = ref([])
const loading = ref(true)
const activeCategory = ref("全部")

const categories = ["全部", "开发记录", "后端实践", "产品思考", "关于本站"]

const visibleArticles = computed(() => {
  if (activeCategory.value === "全部") return articles.value
  return articles.value.filter((article) => article.category === activeCategory.value)
})

onMounted(async () => {
  articles.value = await getArticles()
  loading.value = false
})
</script>

<template>
  <div class="page-width blog-home">
    <section class="blog-hero">
      <div class="blog-hero-main">
        <p class="blog-kicker">OwnerBlog / 个人博客</p>
        <h1>你好，我是 Owner。</h1>
        <p class="blog-description">这里记录我做项目、学技术，以及把一个想法慢慢做出来的过程。文章不追求一次写完，重要的是把当时的思考留下来。</p>
        <div class="blog-actions">
          <a class="text-link" href="#articles">开始阅读 <span>↓</span></a>
          <RouterLink class="quiet-link" to="/knowledge">从文章中提问</RouterLink>
        </div>
      </div>
      <aside class="author-note">
        <div class="author-avatar">O</div>
        <div>
          <strong>Owner</strong>
          <p>开发者 · 学习者<br />正在做 OwnerBlog</p>
        </div>
      </aside>
    </section>

    <div class="blog-layout" id="articles">
      <main class="post-column">
        <div class="blog-section-title">
          <div>
            <span class="blog-kicker">文章</span>
            <h2>最近写了什么</h2>
          </div>
          <span class="post-total">{{ visibleArticles.length }} 篇</span>
        </div>

        <div class="category-tabs" aria-label="文章分类">
          <button
            v-for="category in categories"
            :key="category"
            type="button"
            :class="{ active: activeCategory === category }"
            @click="activeCategory = category"
          >{{ category }}</button>
        </div>

        <div v-if="loading" class="empty-state">正在加载文章……</div>
        <div v-else-if="visibleArticles.length" class="article-list blog-article-list">
          <ArticleRow v-for="(article, index) in visibleArticles" :key="article.id" :article="article" :class="`note-note-${(index % 4) + 1}`" />
        </div>
        <div v-else class="empty-state">这个分类暂时还没有文章。</div>
      </main>

      <aside class="blog-sidebar">
        <section class="sidebar-block">
          <h3>关于这个博客</h3>
          <p>OwnerBlog 是我的公开笔记本。这里会留下开发记录、技术实践、产品思考，也会留下还没有想明白的问题。</p>
          <RouterLink class="text-link" to="/articles/1">先读读这篇介绍 <span>↗</span></RouterLink>
        </section>

        <section class="sidebar-block">
          <h3>分类</h3>
          <ul class="sidebar-list">
            <li v-for="category in categories.slice(1)" :key="category">
              <button type="button" @click="activeCategory = category; document.querySelector('#articles')?.scrollIntoView({ behavior: 'smooth' })">
                <span>{{ category }}</span><span>{{ articles.filter((article) => article.category === category).length }}</span>
              </button>
            </li>
          </ul>
        </section>

        <section class="sidebar-block">
          <h3>标签</h3>
          <div class="tag-cloud">
            <span v-for="tag in [...new Set(articles.flatMap((article) => article.tags || []))]" :key="tag">#{{ tag }}</span>
          </div>
        </section>

        <section class="sidebar-block sidebar-quiet">
          <p>文章会持续更新。你也可以订阅 RSS，或者登录后留下评论。</p>
          <RouterLink class="quiet-link" to="/knowledge">知识问答 →</RouterLink>
        </section>
      </aside>
    </div>
  </div>
</template>
