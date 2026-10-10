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

// 定义知识问答请求函数
export async function askKnowledge(question){
  const value = question.trim()
  if (!value){
    throw new Error("问题不能为空")
  }
  const { data } = await apiClient.post("/knowledge/chat", {question: value},)
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