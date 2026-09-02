import axios from "axios"

//创建项目统一使用的Axios客户端
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  timeout: 10000,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
})

//从浏览器Cookie中读取指定名称的Cookie值
function getCookie(name){
  const cookies = document.cookie.split("; ")
  
  for(const cookie of cookies){
    const [key, ...valueParts] =  cookie.split("=")

    if(key===name){
      return decodeURIComponent(valueParts.join("="))
    }
  }
  return null
}

//注册Axios请求拦截器
apiClient.interceptors.request.use((config) => {
  const method = config.method?.toUpperCase()
  const csrfToken = getCookie("csrftoken")
  const writeMethods = ["POST", "PUT", "PATCH", "DELETE"]

  if(writeMethods.includes(method) && csrfToken){
    config.headers["X-CSRFToken"] = csrfToken
  }
  return config
})