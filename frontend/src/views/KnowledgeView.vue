<script setup>
import { ref } from "vue"
import { RouterLink } from "vue-router"
import { askKnowledge } from "../api/articles"

const question = ref("")
const result = ref(null)
const loading = ref(false)
async function submitQuestion() {
  if (!question.value.trim()) return
  loading.value = true
  result.value = await askKnowledge(question.value.trim())
  loading.value = false
}
</script>

<template>
  <div class="page-width knowledge-page">
    <RouterLink class="back-link" to="/">← 返回首页</RouterLink>
    <section class="knowledge-intro"><span class="section-label">知识库问答</span><h1>把问题说出来，<em>从已有知识开始。</em></h1><p>这是一个公开问答入口。你可以匿名提问，系统只会使用已公开并完成索引的文章作为回答资源。</p></section>
    <form class="question-form" @submit.prevent="submitQuestion"><label for="question">你的问题</label><textarea id="question" v-model="question" rows="4" placeholder="例如：如何设计一条清晰的文章发布链路？"></textarea><div class="form-footer"><span>单轮问答 · 公开文章范围</span><button class="solid-button" type="submit" :disabled="loading">{{ loading ? "思考中……" : "开始提问 ↗" }}</button></div></form>
    <section v-if="result" class="answer-panel"><span class="section-label">回答</span><p class="answer-text">{{ result.answer }}</p><div class="resource-list"><span class="section-label">参考资源</span><RouterLink v-for="resource in result.resources" :key="resource.id" :to="`/articles/${resource.id}`">{{ resource.title }} <span>↗</span></RouterLink></div></section>
  </div>
</template>
