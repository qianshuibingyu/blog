<script setup>
import { onMounted, ref } from "vue"
import { RouterLink } from "vue-router"
import ArticleRow from "../components/ArticleRow.vue"
import { getArticles } from "../api/articles"

const articles = ref([])
const loading = ref(true)
const error = ref("")

onMounted(async () => {
  try{
    articles.value = await getArticles()
  }catch(requestError){
    error.value = "文章加载失败，请稍后重试。"
  }finally{
    loading.value = false
  }
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
          <span class="post-total">{{ articles.length }} 篇</span>
        </div>

        <div v-if="loading" class="empty-state">正在加载文章……</div>
        <div v-else-if="error" class="empty-state">
          {{ error }}
        </div>
        <div v-else-if="articles.length" class="article-list blog-article-list">
          <ArticleRow v-for="(article, index) in articles" :key="article.id" :article="article" :class="`note-note-${(index % 4) + 1}`" />
        </div>
        <div v-else class="empty-state">这个分类暂时还没有文章。</div>
      </main>

      <aside class="blog-sidebar">
        <section class="sidebar-block">
          <h3>关于这个博客</h3>
          <p>OwnerBlog 是我的公开笔记本。这里会留下开发记录、技术实践、产品思考，也会留下还没有想明白的问题。</p>
          <RouterLink class="text-link" to="/articles/1">先读读这篇介绍 <span>↗</span></RouterLink>
        </section>

        <section class="sidebar-block sidebar-quiet">
          <p>文章会持续更新。你也可以订阅 RSS，或者登录后留下评论。</p>
          <RouterLink class="quiet-link" to="/knowledge">知识问答 →</RouterLink>
        </section>
      </aside>
    </div>
  </div>
</template>
