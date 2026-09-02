import { apiClient } from "./client"

export async function login(username, password) {
  const { data } = await apiClient.post("/auth/login", { username, password })
  return data
}

export async function logout() {
  const { data } = await apiClient.post("/auth/logout")
  return data
}

export async function getCurrentUser() {
  const { data } = await apiClient.get("/auth/me")
  return data
}

//请求 Django 设置 csrftoken Cookie
export async function getCsrfToken(){
  const {data} = await apiClient.get("/auth/csrf")
  return data
}
