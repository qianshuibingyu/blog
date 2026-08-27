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
