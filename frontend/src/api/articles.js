import { apiClient } from "./client"
import { mockArticles } from "../data/mockArticles"

const useMocks = import.meta.env.VITE_USE_MOCKS !== "false"

export async function getArticles() {
  if (useMocks) return mockArticles
  const { data } = await apiClient.get("/articles")
  return data.items || []
}

export async function getArticle(id) {
  if (useMocks) return mockArticles.find((article) => String(article.id) === String(id),)
  const { data } = await apiClient.get(`/articles/${id}`)
  return data
}

export async function askKnowledge(question) {
  if (useMocks) {
    return {
      answer: `这是一个演示回答：你的问题是“${question}”。正式接入后，系统只会检索公开且索引成功的文章。`,
      resources: mockArticles.filter((article) => article.featured || article.category === "知识库").slice(0, 2),
    }
  }
  const { data } = await apiClient.post("/knowledge/ask", { question })
  return data
}

//获取当前用户文章，后端已经按照 request.user 过滤
export async function getMyArticles(){
  const { data } = await apiClient.get("/my-articles")
  return data.items || []
}

//创建草稿，payload 只放用户可编辑字段
export async function createArticle(payload){
  const { data } = await apiClient.post("/articles", payload)
  return data
}


//更新指定文章，id 决定后端操作哪一条记录
export async function updateArticle(id, payload){
  const { data } = await apiClient.patch(
    "/articles/"+id,
    payload,
  )
  return data
}

//删除指定文章，返回 Axios Promise 供页面等待完成
export async function deleteArticle(id){
  return apiClient.delete("/articles/"+id)
}

//提交指定草稿审核，后端负责执行状态转换
export async function submitArticleReview(id){
  const {data} = await apiClient.post(
    "/articles/"+id+"/submit-review",
  )
  return data
}