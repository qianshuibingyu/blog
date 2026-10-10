<script setup>
// 使用 Vue 单文件组件脚本区域
import { ref } from "vue"                      // 导入响应式状态
import { RouterLink } from "vue-router"        // 导入返回链接组件
import { askKnowledge } from "../api/articles"  // 导入真实问答 API

// 保存输入问题、后端成功响应、用户可读错误、请求中状态
const question = ref("")
const result = ref(null)
const errorMessage = ref("")
const loading = ref(false)

// 提交一次问答请求
async function submitQuestion(){
  const value = question.value.trim()
  if(!value || loading.value) return
  loading.value = true
  result.value = null
  errorMessage.value = ""
  // 执行真实 API 请求
  try {
    result.value = await askKnowledge(value)
  } catch(error){
    errorMessage.value = error.response?.data?.error || "知识问答服务暂时不可用"
  }finally{
    loading.value = false
  }
}
</script>

<template>
  <div class="page-width knowledge-page">
    <RouterLink class="back-link" to="/">← 返回首页</RouterLink>
    <section class="knowledge-intro"><span class="section-label">知识库问答</span><h1>把问题说出来，<em>从已有知识开始。</em></h1><p>这是一个公开问答入口。你可以匿名提问，系统只会使用已公开并完成索引的文章作为回答资源。</p></section>
    <form class="question-form" @submit.prevent="submitQuestion"><label for="question">你的问题</label><textarea id="question" v-model="question" rows="4" placeholder="例如：如何设计一条清晰的文章发布链路？"></textarea><div class="form-footer"><span>单轮问答 · 公开文章范围</span><button class="solid-button" type="submit" :disabled="loading">{{ loading ? "思考中……" : "开始提问 ↗" }}</button></div></form>
    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    <section v-if="result" class="answer-panel">
      <span class="section-label">回答</span>
      <p class="answer-text">{{ result.answer }}</p>
      <div v-if="result.sources?.length" class="resource-list"> <!-- 只在有真实来源时显示来源区。 -->
        <span class="section-label">参考来源</span> <!-- 显示来源标题。 -->
        <article
          v-for="source in result.sources"
          :key="source.source_id"
        >
          <RouterLink :to="source.article_url">
            {{ source.article_title }}
          </RouterLink>

          <span>
            第 {{ source.chunk_index + 1 }} 段
          </span>
        </article>
      </div> <!-- 结束来源区域。 -->
    </section> <!-- 结束结果区域。 -->
  </div>
</template>
