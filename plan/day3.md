# Day 3 实操手册：Session 认证与用户文章管理

> 阅读规则：代码示例中的注释说明每一行“做什么”；紧跟代码的文字说明“为什么这样做”。遇到没有注释的命令或 JSON，先看其上一行的目标说明，不要把示例代码当成黑盒直接复制。

本手册必须从上到下执行。每一步都包含：

```
1. 打开哪个文件
2. 修改什么内容
3. 为什么修改
4. 执行什么命令
5. 预期看到什么
6. 出错时检查什么
```

不要跳过验证直接进入下一步。

## Day 3 阶段总览

先用下面的分类判断当前步骤的性质：

```text
Phase 0       启动项目并确认基础功能
Phase 1-4     编写和验证 Session、Cookie、CSRF、Axios、Vue 登录状态
Phase 5-7     编写文章状态、Serializer 和后端文章 API
Phase 8       手动测试后端文章 API，不写 Vue 页面
Phase 9       编写 Vue 个人中心和 /my-articles 页面
Phase 10      运行自动化检查，并确认测试覆盖目标
Phase 11-12   复盘、提交和最终验收
```

每个阶段的判断标准：

- 看到“打开文件、添加代码、替换代码”时，是在实现功能。
- 看到浏览器 Console、`fetch`、Network 和预期状态码时，是在手动测试。
- 看到 `manage.py test`、`manage.py check` 或 `pnpm build` 时，是在运行自动化检查。

Phase 8 的 `fetch` 示例只用于当场验证，不要复制到 Vue 文件中。Phase 9 才会把相同的后端能力接入真正的个人中心页面。

## 0. 项目启动



### 0.1 启动后端

打开 PowerShell：

```
cd E:\Desktop\VibeCoding\ownerblog\backend
.\.venv\Scripts\python.exe manage.py check
```

预期：

```
System check identified no issues (0 silenced).
```

继续启动：

```
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

预期：

```
Starting development server at http://127.0.0.1:8000/
```

如果看到 No module named django，不要使用系统 Python，必须使用：

```
.\.venv\Scripts\python.exe
```



### 0.2 启动前端

另开一个 PowerShell：

```
cd E:\Desktop\VibeCoding\ownerblog\frontend
pnpm dev
```

访问终端显示的地址，通常是：

```
http://localhost:5173
```

当前请求链路：

```
浏览器 localhost:5173
  -> Axios 请求 /api/...
      -> Vite proxy
          -> Django 127.0.0.1:8000
```



### 0.3 确认 Day 2 公开文章功能

浏览器访问：

```
http://127.0.0.1:8000/api/articles
```

预期：

```
返回 JSON
状态码 200
```

前端访问：

```
http://localhost:5173/
```

预期：

```
能打开文章列表页面
```

完成后勾选：

- [x] 后端 check 通过
- [x] 后端运行在 8000
- [x] 前端运行在 5173
- [x] /api/articles 返回 200
- [x] Vue 文章列表页面可以打开



## 1. 认证路由和 CSRF 接口

这一阶段只处理认证基础，不处理文章写入。

### 1.1 检查认证路由

打开：

```
backend/config/urls.py
```

确认只保留一条认证模块路由：

```
path("api/auth/", include("accounts.urls")),
```

如果出现两条相同的 path，删除重复的那一条。

然后打开：

```
backend/accounts/urls.py
```

将整个文件整理成：

```
from django.urls import path

from .views import csrf_view, login_view, logout_view, me_view


urlpatterns = [
    path("csrf", csrf_view, name="csrf"),
    path("login", login_view, name="login"),
    path("logout", logout_view, name="logout"),
    path("me", me_view, name="me"),
]
```

这里的 csrf 是子路径，最终地址由两层拼接：

```
api/auth/ + csrf = /api/auth/csrf
```

不要在 accounts/urls.py 中写：

```
path("api/auth/", include("accounts.urls"))
```

否则会让 accounts 路由包含自己。

### 1.2 检查 accounts/views.py 的导入

打开：

```
backend/accounts/views.py
```

顶部导入应整理为：

```
# 解析前端发送的 JSON 请求体。
import json

# authenticate 校验账号；login 创建 Session；logout 清理 Session。
from django.contrib.auth import authenticate, login, logout
# 将 Django 响应转换为 JSON。
from django.http import JsonResponse
# 让响应设置 CSRF Cookie。
from django.views.decorators.csrf import ensure_csrf_cookie
# 限制视图允许的 HTTP 方法。
from django.views.decorators.http import require_http_methods
```

删除没有使用的：

```
from django.views.decorators.csrf import csrf_exempt
```

原因：登录和退出都是 POST 写请求，需要接受 CSRF 检查。

### 1.3 检查 CSRF View

在同一个文件中，确认文件最后有：

```
# 给浏览器设置 csrftoken Cookie。
@ensure_csrf_cookie
# 该接口只负责读取 Cookie，不允许使用 POST。
@require_http_methods(["GET"])
def csrf_view(request):
    # Cookie 已由装饰器写入，这里返回调试提示。
    return JsonResponse({"detail": "CSRF cookie set."})
```

这个接口只做一件事：

```
GET /api/auth/csrf
-> Django 给浏览器设置 csrftoken Cookie
-> 返回 200
```



### 1.4 检查 Django 配置

打开：

```
backend/config/settings.py
```

确认 INSTALLED_APPS 中有：

```
"django.contrib.auth",
"django.contrib.sessions",
```

确认 MIDDLEWARE 中有：

```
"django.contrib.sessions.middleware.SessionMiddleware",
"django.middleware.csrf.CsrfViewMiddleware",
"django.contrib.auth.middleware.AuthenticationMiddleware",

"django.middleware.csrf.CsrfViewMiddleware",
"django.contrib.auth.middleware.AuthenticationMiddleware",
```

打开：

```
backend/.env
```

确认：

```
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

前端用哪个地址打开，就必须把哪个完整 Origin 写进去。Origin 必须包括 http://，不能写路径。

### 1.5 验证 CSRF 接口

在后端终端执行：

```
Invoke-WebRequest http://127.0.0.1:8000/api/auth/csrf -UseBasicParsing
```

预期：

```
StatusCode: 200
```

然后在浏览器打开：

```
http://localhost:5173/login
```

按 F12：

```
Application -> Cookies -> http://localhost:5173
```

预期看到：

```
csrftoken
```

如果浏览器打开接口后只看到 JSON：

```
{"detail": "CSRF cookie set."}
```

这也是正常的，Cookie 需要在 Application 的 Cookies 中看。

完成后勾选：

- [x] /api/auth/csrf 返回 200
- [x] 浏览器出现 csrftoken
- [x] 登录和退出没有 csrf_exempt
- [x] Trusted Origins 包含当前前端地址



## 2. Axios 携带 CSRF 和 Session



### 2.1 打开 Axios 客户端

打开：

```
frontend/src/api/client.js
```

完整内容应为：

```
// 导入 Axios 库，用于发送 HTTP 请求。
import axios from "axios"

// 创建项目统一使用的 Axios 客户端。
// 创建全项目复用的 Axios 实例。
export const apiClient = axios.create({
  // /api 请求由 Vite proxy 转发到 Django。
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",

  // 请求超过 10 秒仍没有响应时失败。
  timeout: 10000,

  // 告诉 Django 请求体使用 JSON。
  headers: { "Content-Type": "application/json" },

  // 允许浏览器携带 sessionid 和 csrftoken Cookie。
  withCredentials: true,
})

// 从浏览器 Cookie 中读取指定名称的 Cookie。
function getCookie(name) {
  // Cookie 之间使用分号和空格分隔。
  const cookies = document.cookie.split("; ")

  // 逐个查找目标 Cookie。
  for (const cookie of cookies) {
    // 将 Cookie 拆成名称和值。
    const [key, ...valueParts] = cookie.split("=")

    // 找到目标 Cookie 后返回它的值。
    if (key === name) {
      return decodeURIComponent(valueParts.join("="))
    }
  }

  // 没有找到目标 Cookie 时返回 null。
  return null
}

// 在 Axios 发送请求前执行。
// 每次请求发送前执行，统一补充 CSRF 请求头。
apiClient.interceptors.request.use((config) => {
  // 获取当前请求方法。
  const method = config.method?.toUpperCase()

  // 读取 Django 设置的 csrftoken。
  const csrfToken = getCookie("csrftoken")

  // 这些方法会修改服务器数据。
  const writeMethods = ["POST", "PUT", "PATCH", "DELETE"]

  // 写请求有 CSRF Token 时添加 Django 要求的请求头。
  if (writeMethods.includes(method) && csrfToken) {
    config.headers["X-CSRFToken"] = csrfToken
  }

  // 返回请求配置，继续发送请求。
  return config
})
```

重点检查：

```
document.cookie.split("; ")
```

不能写成：

```
document.cookie.split(", ")
```

错误的逗号会导致 Axios 找不到 csrftoken，登录请求返回 403。

### 2.2 检查 auth.js

打开：

```
frontend/src/api/auth.js
```

整理为：

```
// 复用配置好 Cookie、超时和 CSRF 的 Axios 实例。
import { apiClient } from "./client"

// 调用登录接口。
// 登录函数接收表单值，并返回后端用户数据。
export async function login(username, password) {
  // POST 会提交账号密码并创建服务端 Session。
  const { data } = await apiClient.post(
    "/auth/login",
    { username, password },
  )
  return data
}

// 调用退出接口。
// 退出函数请求后端清理 Session。
export async function logout() {
  // POST 是写请求，Axios 拦截器会自动添加 CSRF 头。
  const { data } = await apiClient.post("/auth/logout")
  return data
}

// 获取当前登录用户。
// 页面刷新时调用该函数恢复登录状态。
export async function getCurrentUser() {
  // Django 根据 sessionid 判断当前 request.user。
  const { data } = await apiClient.get("/auth/me")
  return data
}

// 请求 Django 设置 csrftoken Cookie。
// 登录前先请求 CSRF Cookie。
export async function getCsrfToken() {
  // GET 不修改业务数据，只让 Django 设置 Cookie。
  const { data } = await apiClient.get("/auth/csrf")
  return data
}
```



### 2.3 登录前获取 CSRF

打开：

```
frontend/src/views/LoginView.vue
```

确认导入：

```
import { getCsrfToken, login } from "../api/auth"
```

登录函数中的 try 必须按照这个顺序：

```
try {
  // 先获取 csrftoken Cookie。
  await getCsrfToken()

  // 再提交账号密码。
  const user = await login(
    username.value,
    password.value,
  )

  // 暂时先跳转首页。
  router.push("/")
} catch (error) {
  errorMessage.value =
    error.response?.data?.detail ||
    "登录失败，请检查后端服务。"
}
```

不能先调用 login，再调用 getCsrfToken。

### 2.4 验证 Axios 和 CSRF

刷新：

```
http://localhost:5173/login
```

打开：

```
F12 -> Network -> Fetch/XHR
```

提交正确账号，预期看到：

```
csrf   200
login  200
```

点击 login 请求，检查 Request Headers：

```
X-CSRFToken: 一串随机值
```

检查 Cookies：

```
csrftoken
sessionid
```

如果看到：

```
csrf 200
login 403
```

按顺序检查：

```
1. document.cookie 中有没有 csrftoken。
2. client.js 是否使用 split("; ")。
3. login 请求是否有 X-CSRFToken。
4. Trusted Origins 是否包含当前前端地址。
5. login_view 上是否还存在 csrf_exempt。
```

如果看到：

```
login 401
```

说明 CSRF 已经通过，接下来检查用户名、密码和账号是否激活。

## 3. 验证 Session 和 /api/auth/me



### 3.1 检查后端登录逻辑

打开：

```
backend/accounts/views.py
```

登录函数必须包含：

```
# 根据账号密码查找用户；失败时返回 None。
user = authenticate(
    request,
    username=username,
    password=password,
)
```

认证失败时：

```
# 认证失败时返回 401，不创建 Session。
if user is None:
    return JsonResponse(
        {"detail": "用户名或密码错误。"},
        status=401,
    )
```

认证成功后：

```
# 将用户 ID 写入 Django Session，浏览器随后保存 sessionid Cookie。
login(request, user)
```

这句由 Django 创建 Session。不要自己生成 sessionid。

退出函数必须包含：

```
# 清理服务端 Session，不能只清空前端变量。
logout(request)
```

不要只在 Vue 中把用户变量设为 null。那只能改变页面，不能清理后端 Session。

### 3.2 创建或重置普通测试用户

执行：

```
cd E:\Desktop\VibeCoding\ownerblog\backend
.\.venv\Scripts\python.exe manage.py shell
```

逐行输入：

```
from django.contrib.auth import get_user_model
User = get_user_model()
user, created = User.objects.get_or_create(username="user")
user.set_password("123321")
user.is_active = True
user.is_staff = False
user.is_superuser = False
user.save()
print(user.username, user.is_active, user.is_staff)
exit()
```

预期：

```
user True False
```

管理员使用：

```
.\.venv\Scripts\python.exe manage.py createsuperuser
```



### 3.3 验证未登录的 me

先退出前端账号，或者清除浏览器的 sessionid。

打开：

```
http://127.0.0.1:8000/api/auth/me
```

页面显示：

```
{"detail": "未登录。"}
```

这是响应正文。要看状态码：

```
F12 -> Network -> 点击 me -> Headers -> General -> Status Code
```

预期：

```
401 Unauthorized
```



### 3.4 验证登录后的 me

回到：

```
http://localhost:5173/login
```

填写：

```
用户名：user
密码：123321
```

提交后确认：

```
login -> 200
```

再打开：

```
http://127.0.0.1:8000/api/auth/me
```

预期：

```
{
  "id": 2,
  "username": "user",
  "is_staff": false
}
```

如果 login=200 但页面顶部仍显示“登录”，那是 Vue 没有把登录结果写入共享状态，进入 Phase 4 检查。

### 3.5 验证退出

点击前端的退出按钮。

Network 预期：

```
POST /api/auth/logout -> 200
```

退出后重新打开：

```
http://127.0.0.1:8000/api/auth/me
```

预期：

```
401
```

完成后勾选：

- [x] 错误密码返回 401
- [x] 未登录 me 返回 401
- [x] 正确登录返回 200
- [x] 登录后 me 返回当前用户
- [x] 退出后 me 返回 401
- [x] 浏览器有 csrftoken 和 sessionid



## 4. Vue 登录状态自动更新

这一阶段解决：登录成功后不用手动刷新，顶部立即显示用户名。

### 4.1 创建共享状态文件

创建目录：

```
frontend/src/stores
```

创建文件：

```
frontend/src/stores/authState.js
```

写入：

```
// 导入 Vue 的响应式引用工具。
import { ref } from "vue"

// App.vue 和 LoginView.vue 共享同一个响应式用户对象。
export const currentUser = ref(null)
```

作用：

```
App.vue 和 LoginView.vue 操作同一个 currentUser。
登录页面更新它后，顶部导航可以立即得到新值。
```



### 4.2 修改 App.vue 的导入

打开：

```
frontend/src/App.vue
```

将顶部导入：

```
import { onMounted, ref } from "vue"
import { RouterLink, RouterView } from "vue-router"
import { getCurrentUser, logout } from "./api/auth"
```

改为：

```
import { onMounted } from "vue"
import { RouterLink, RouterView } from "vue-router"
import { getCurrentUser, logout } from "./api/auth"
import { currentUser } from "./stores/authState"
```

删除：

```
const currentUser = ref(null)
```

原因：

```
不能让 App.vue 自己再创建一个 currentUser。
否则 LoginView.vue 更新的是另一个变量。
```



### 4.3 修改 App.vue 的登录状态检查

在 App.vue 的  中，保留或添加：

```
// 组件挂载后执行一次，用后端 Session 恢复登录状态。
onMounted(async () => {
  try {
    // 页面加载时向后端确认 Session 是否有效。
    currentUser.value = await getCurrentUser()
  } catch {
    // 401 表示当前没有登录。
    currentUser.value = null
  }
})
```

这里不是 Django 主动推送数据，而是页面加载时前端主动请求。

### 4.4 修改 App.vue 的退出函数

在同一个  中：

```
// 处理退出按钮点击事件。
async function signOut() {
  // 请求后端清理 Session。
  await logout()

  // 清空共享状态，让页面立即显示登录入口。
  currentUser.value = null
}
```



### 4.5 修改 App.vue 的模板

在  的 header 中确认有：

```
<!-- currentUser 有值时显示账号操作区。 -->
<div v-if="currentUser" class="account-actions">
  <span class="account-name">
    {{ currentUser.username }}
  </span>

  <button
    class="text-button"
    type="button"
    @click="signOut"
  >
    退出
  </button>
</div>

<!-- currentUser 为空时显示登录入口。 -->
<RouterLink
  v-else
  class="text-button login-link"
  to="/login"
>
  登录
</RouterLink>
```

含义：

```
currentUser 有值 -> 显示用户名和退出
currentUser 为 null -> 显示登录链接
```



### 4.6 修改 LoginView.vue 的导入

打开：

```
frontend/src/views/LoginView.vue
```

在导入区域添加：

```
import { currentUser } from "../stores/authState"
```



### 4.7 修改 LoginView.vue 的登录函数

找到：

```
await login(username.value, password.value)
router.push("/")
```

替换为：

```
// 请求登录接口，并接收后端返回的用户数据。
const user = await login(
  username.value,
  password.value,
)

// 将后端返回的用户信息写入共享状态。
// 更新共享 ref，其他组件会立即重新渲染。
currentUser.value = user

// 切换到首页。
router.push("/")
```

完整的 try 结构应为：

```
try {
  await getCsrfToken()

  const user = await login(
    username.value,
    password.value,
  )

  currentUser.value = user
  router.push("/")
} catch (error) {
  errorMessage.value =
    error.response?.data?.detail ||
    "登录失败，请检查后端服务。"
} finally {
  submitting.value = false
}
```



### 4.8 验证自动更新

刷新一次前端页面，让浏览器加载新代码。

然后：

```
1. 打开 /login。
2. 输入 user 和密码。
3. 点击登录。
4. 不要手动刷新。
5. 等待 router.push("/") 完成。
```

预期：

```
顶部立即显示 user
顶部出现退出按钮
```

如果登录 Network 是 200，但顶部没有变化，检查：

```
1. LoginView.vue 是否导入了 ../stores/authState。
2. App.vue 是否导入了 ./stores/authState。
3. 两个文件的路径是否指向同一个 authState.js。
4. App.vue 是否还保留 const currentUser = ref(null)。
5. LoginView.vue 是否执行 currentUser.value = user。
```

完成后勾选：

- [x] 登录成功后不刷新页面即可显示用户名
- [x] 退出后立即显示登录链接
- [x] 刷新页面后仍能恢复登录状态
- [x] 不使用 localStorage 保存密码或 Session ID



## 5. 文章状态模型

现在开始文章管理。先改模型，再做 API。

### 5.1 修改文章状态

打开：

```
backend/articles/models.py
```

找到：

```
class ArticleStatus(models.TextChoices):
    DRAFT = "draft", "草稿"
    PUBLISHED = "published", "已发布"
```

替换为：

```
# 用枚举集中管理允许的文章状态，避免散落字符串拼写错误。
class ArticleStatus(models.TextChoices):
    # 草稿可以由作者编辑。
    DRAFT = "draft", "草稿"
    # 待审核文章等待管理员处理。
    PENDING_REVIEW = "pending_review", "待审核"
    # 已发布文章可以进入公开查询。
    PUBLISHED = "published", "已发布"
```

作用：

```
draft -> pending_review -> published
```

普通用户只能：

```
创建 draft
编辑 draft
删除 draft
提交 draft 为 pending_review
```



### 5.2 执行迁移

```
cd E:\Desktop\VibeCoding\ownerblog\backend
.\.venv\Scripts\python.exe manage.py makemigrations articles
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
```

预期：

```
System check identified no issues (0 silenced).
```

如果 makemigrations 没有生成文件，检查 models.py 是否真的保存。

## 6. 用户文章 Serializer

打开：

```
backend/articles/serializers.py
```

把文件整理为：

```
from rest_framework import serializers

from .models import Article


class ArticleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "summary",
            "published_at",
        )


class ArticleDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "summary",
            "content",
            "published_at",
        )


class MyArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "summary",
            "content",
            "status",
            "created_at",
            "updated_at",
            "published_at",
        )
        read_only_fields = (
            "id",
            "status",
            "created_at",
            "updated_at",
            "published_at",
        )
```

解释：

```
author 没有放进 fields。
status 在 read_only_fields 中。
作者和状态必须由后端决定。
```

保存后执行：

```
.\.venv\Scripts\python.exe manage.py check
```



## 7. 用户文章后端 API



### 7.1 先理解路由合并

公开读取和用户写入使用相同文章路径：

```
GET    /api/articles
POST   /api/articles
GET    /api/articles/{id}
PATCH  /api/articles/{id}
DELETE /api/articles/{id}
```

因此不能在 config/urls.py 中把同一路径注册两次。

做法：

```
一个 View 处理 /api/articles
根据 HTTP 方法分别执行 get、post、patch、delete
```



### 7.2 替换 articles/views.py

打开：

```
backend/articles/views.py
```

将整个文件替换为：

```
# 找不到对象时自动返回 404，减少重复判断。
from django.shortcuts import get_object_or_404
# AllowAny 用于公开读取；写入接口另外检查登录状态。
from rest_framework.permissions import AllowAny, IsAuthenticated
# 返回 JSON 数据和 HTTP 状态码。
from rest_framework.response import Response
# APIView 会把 HTTP 方法分发到同名函数。
from rest_framework.views import APIView

# 导入文章模型和集中定义的状态枚举。
from .models import Article, ArticleStatus
from .serializers import (
    ArticleDetailSerializer,
    ArticleListSerializer,
    MyArticleSerializer,
)


# 处理 /api/articles 集合路径的 GET 和 POST。
class ArticleCollectionAPIView(APIView):
    # GET 对访客开放，只返回已发布文章。
    def get(self, request):
        # 通过数据库条件过滤公开内容，不能在前端过滤草稿。
        articles = Article.objects.filter(
            status=ArticleStatus.PUBLISHED,
        )
        # 把多个 Article 对象转换成列表 JSON。
        serializer = ArticleListSerializer(
            articles,
            many=True,
        )
        # 用 items 包装列表，保持前端接口结构稳定。
        return Response({"items": serializer.data})

    # POST 创建草稿，必须先确认用户已登录。
    def post(self, request):
        # request.user 由 Django Session 认证产生。
        if not request.user.is_authenticated:
            return Response(
                {"detail": "未登录。"},
                status=401,
            )

        # 使用前端数据初始化 Serializer，先做字段校验。
        serializer = MyArticleSerializer(data=request.data)
        # 校验失败时 DRF 自动返回 400 错误。
        serializer.is_valid(raise_exception=True)
        # 作者和状态由后端强制设置，忽略客户端伪造值。
        article = serializer.save(
            author=request.user,
            status=ArticleStatus.DRAFT,
        )
        return Response(
            MyArticleSerializer(article).data,
            status=201,
        )


# 处理单篇文章的读取、编辑和删除。
class ArticleItemAPIView(APIView):
    # 详情接口仍然只公开已发布文章。
    def get(self, request, pk):
        # pk 来自 URL，例如 /api/articles/3 中的 3。
        article = get_object_or_404(
            Article.objects.filter(
                status=ArticleStatus.PUBLISHED,
            ),
            pk=pk,
        )
        return Response(
            ArticleDetailSerializer(article).data,
        )

    # 把“登录 + 是否本人文章”的判断集中到一个函数。
    def _get_owned_article(self, request, pk):
        # 未登录时不能查询用户文章。
        if not request.user.is_authenticated:
            return None

        # 同时按 id 和 author 过滤，阻止跨用户操作。
        return get_object_or_404(
            Article,
            pk=pk,
            author=request.user,
        )

    # PATCH 只允许作者修改自己的草稿。
    def patch(self, request, pk):
        article = self._get_owned_article(request, pk)

        if article is None:
            return Response(
                {"detail": "未登录。"},
                status=401,
            )

        if article.status != ArticleStatus.DRAFT:
            return Response(
                {"detail": "只有草稿可以编辑。"},
                status=400,
            )

        # partial=True 允许只提交要修改的字段。
        serializer = MyArticleSerializer(
            article,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        # Serializer 的只读字段仍不能被客户端改变。
        serializer.save()
        return Response(serializer.data)

    # DELETE 删除当前用户自己的文章。
    def delete(self, request, pk):
        article = self._get_owned_article(request, pk)

        if article is None:
            return Response(
                {"detail": "未登录。"},
                status=401,
            )

        article.delete()
        return Response(status=204)


# 处理 /api/my-articles，只返回当前用户的文章。
class MyArticleListAPIView(APIView):
    # 当前用户通过 request.user 确定，不能接收 user_id 参数。
    def get(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "未登录。"},
                status=401,
            )

        # 这个过滤条件是数据隔离的核心。
        articles = Article.objects.filter(
            author=request.user,
        )
        serializer = MyArticleSerializer(
            articles,
            many=True,
        )
        return Response({"items": serializer.data})


# 处理作者提交草稿审核的状态动作。
class ArticleSubmitReviewAPIView(APIView):
    # POST 表示执行一次状态变更。
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "未登录。"},
                status=401,
            )

        article = get_object_or_404(
            Article,
            pk=pk,
            author=request.user,
        )

        if article.status != ArticleStatus.DRAFT:
            return Response(
                {"detail": "只有草稿可以提交审核。"},
                status=400,
            )

        # 状态转换由服务端执行，不能让客户端直接提交 status。
        article.status = ArticleStatus.PENDING_REVIEW
        # 将新的状态持久化到数据库。
        article.save()
        return Response(
            MyArticleSerializer(article).data,
        )
```

说明：

```
ArticleCollectionAPIView.get：公开读取已发布文章。
ArticleCollectionAPIView.post：登录用户创建草稿。
ArticleItemAPIView.get：公开读取已发布文章详情。
ArticleItemAPIView.patch：只能编辑自己的草稿。
ArticleItemAPIView.delete：只能删除自己的文章。
MyArticleListAPIView.get：只返回当前用户文章。
ArticleSubmitReviewAPIView.post：草稿变成待审核。
```

为什么没有直接使用 Article.objects.all()：

```
因为那会返回所有用户的文章。
```

为什么使用 author=request.user：

```
因为作者必须由服务端根据 Session 决定。
```



### 7.3 修改 config/urls.py

打开：

```
backend/config/urls.py
```

文章 View 导入改为：

```
from articles.views import (
    ArticleCollectionAPIView,
    ArticleDetailAPIView,
    ArticleItemAPIView,
    ArticleSubmitReviewAPIView,
    MyArticleListAPIView,
)
```

urlpatterns 中认证路由只保留一条：

```
path("api/auth/", include("accounts.urls")),
```

文章路由整理为：

```
path(
    "api/articles",
    ArticleCollectionAPIView.as_view(),
    name="article-collection",
),
path(
    "api/articles/<int:pk>",
    ArticleItemAPIView.as_view(),
    name="article-item",
),
path(
    "api/my-articles",
    MyArticleListAPIView.as_view(),
    name="my-article-list",
),
path(
    "api/articles/<int:pk>/submit-review",
    ArticleSubmitReviewAPIView.as_view(),
    name="article-submit-review",
),
```

不要再保留旧的：

```
ArticleListAPIView
ArticleDetailAPIView
```

如果导入了但不再使用，删除旧导入。

### 7.4 后端检查

```
cd E:\Desktop\VibeCoding\ownerblog\backend
.\.venv\Scripts\python.exe manage.py check
```

预期：

```
System check identified no issues (0 silenced).
```



## 8. 手动验证用户文章 API

> 本阶段是测试，不是 Vue 页面开发。
>
> 你只使用浏览器 Console 中的 `fetch` 临时发送请求，确认后端接口的状态码、返回数据和权限规则是否正确。这里的 `fetch` 不需要保存到项目文件中，也不需要添加到 Vue 页面。
>
> 如果后端代码还没有通过 Phase 7.4 的 `manage.py check`，先回到 Phase 7 修复错误，再开始本阶段。

本阶段只验证后端是否具备这些能力：

- 登录用户可以读取自己的文章。
- 未登录用户访问用户文章接口会得到 `401`。
- 创建文章时，作者由后端从 `request.user` 确定。
- 创建文章时，状态由后端强制设为 `draft`。
- 只有作者可以编辑、删除和提交自己的文章。

本阶段完成后，后端能力已经验证，但还没有个人中心页面，也还不能点击用户名进入个人中心。

先确认前端或浏览器已经登录普通用户。

### 8.1 查询自己的文章

打开：

```
http://localhost:5173
```

在浏览器 Console 执行：

```
fetch("/api/my-articles", {
  credentials: "include",
}).then(async (response) => {
  console.log(response.status)
  console.log(await response.json())
})
```

预期登录用户：

```
200
{"items": [...]}
```

未登录用户：

```
401
{"detail": "未登录。"}
```



### 8.1.1 先记录前端页面需要实现的行为

这一小节是前端实现要求的说明，不在 Phase 8 编写代码。

后端 API 不负责把请求重定向到登录页。后端只返回 `401`，由 Vue 页面决定跳转地址。

用户访问 `/my-articles` 时，前端应执行以下流程：

```text
访问 /my-articles
  -> 请求 GET /api/my-articles
  -> 后端返回 401
  -> Vue 跳转 /login?next=/my-articles
  -> 登录成功
  -> 读取 next 参数
  -> 返回 /my-articles
```

这些行为会在 Phase 9 的 `MyArticlesView.vue` 和 `LoginView.vue` 中实现。先记住目标流程：

如果 Session 过期，创建、编辑、删除和提交审核返回 `401` 时，Phase 9 的页面也要跳转到 `/login?next=/my-articles`。

### 8.2 创建草稿

在 Console 执行：

```
fetch("/api/articles", {
  method: "POST",
  credentials: "include",
  headers: {
    "Content-Type": "application/json",
    "X-CSRFToken": document.cookie
      .split("; ")
      .find((item) => item.startsWith("csrftoken="))
      ?.split("=")[1],
  },
  body: JSON.stringify({
    title: "我的第一篇草稿",
    summary: "草稿摘要",
    content: "# 草稿正文",
    author: 999,
    status: "published",
  }),
}).then(async (response) => {
  console.log(response.status)
  console.log(await response.json())
})
```

预期：

```
201
返回的 status 是 draft
返回的作者是当前登录用户
```

注意：

```
即使提交 author=999 和 status=published，
后端也必须使用当前用户并强制保存为 draft。
```

记录返回的文章 id，后面继续验证。

### 8.3 编辑自己的草稿

```
fetch("/api/articles/文章ID", {
  method: "PATCH",
  credentials: "include",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    title: "修改后的标题",
  }),
}).then(async (response) => {
  console.log(response.status)
  console.log(await response.json())
})
```

预期：

```
200
标题已经修改
```



### 8.4 提交审核

```
fetch("/api/articles/文章ID/submit-review", {
  method: "POST",
  credentials: "include",
  headers: {
    "Content-Type": "application/json",
  },
}).then(async (response) => {
  console.log(response.status)
  console.log(await response.json())
})
```

预期：

```
200
status 是 pending_review
```



### 8.5 验证待审核文章不能编辑

再次执行 PATCH。

预期：

```
400
{"detail": "只有草稿可以编辑。"}
```



### 8.6 验证删除

重新创建一篇草稿，然后：

```
fetch("/api/articles/文章ID", {
  method: "DELETE",
  credentials: "include",
  headers: {
    "Content-Type": "application/json",
  },
}).then((response) => {
  console.log(response.status)
})
```

预期：

```
204
```



## 9. 实现 Vue 个人中心 /my-articles 页面

> 本阶段才开始写前端页面代码。
>
> 目标是完成一个最小可用的“个人中心 / 我的文章”页面：登录用户可以创建草稿、编辑草稿、删除草稿和提交审核；未登录用户访问时跳转到登录页。

完成本阶段后，才具备下面的页面操作：

```text
点击顶部用户名
  -> 进入 /my-articles
  -> 加载当前用户的文章
  -> 点击“创建草稿”填写文章
```

注意：当前后端的“发布”不是普通用户直接发布。普通用户只能创建草稿并提交审核；最终发布应由管理员在 Django Admin 或后续管理员页面完成。

### 9.1 添加 API 方法

打开：

```
frontend/src/api/articles.js
```

保留已有公开文章函数，在文件最后添加：

```
// 获取当前用户文章；后端已经按 request.user 过滤。
export async function getMyArticles() {
  // 从响应中取出 items；没有 items 时使用空数组避免页面报错。
  const { data } = await apiClient.get("/my-articles")
  return data.items || []
}

// 创建草稿；payload 只放用户可编辑字段。
export async function createArticle(payload) {
  const { data } = await apiClient.post("/articles", payload)
  return data
}

// 更新指定文章；id 决定后端操作哪一条记录。
export async function updateArticle(id, payload) {
  const { data } = await apiClient.patch(
    "/articles/" + id,
    payload,
  )
  return data
}

// 删除指定文章；返回 Axios Promise 供页面等待完成。
export async function deleteArticle(id) {
  return apiClient.delete("/articles/" + id)
}

// 提交指定草稿审核，后端负责执行状态转换。
export async function submitArticleReview(id) {
  const { data } = await apiClient.post(
    "/articles/" + id + "/submit-review",
  )
  return data
}
```



### 9.2 创建页面文件

创建：

```
frontend/src/views/MyArticlesView.vue
```

写入：

```
<script setup>
import { onMounted, ref } from "vue"
import { RouterLink, useRouter } from "vue-router"
import {
  createArticle,
  deleteArticle,
  getMyArticles,
  submitArticleReview,
  updateArticle,
} from "../api/articles"

// 获取路由控制器，用于未登录时跳转 /login。
const router = useRouter()
// 页面展示的当前用户文章列表。
const articles = ref([])
// 首次读取文章时显示加载状态。
const loading = ref(true)
// 保存、删除或提交时防止重复点击。
const submitting = ref(false)
// 保存当前页面要展示的错误信息。
const errorMessage = ref("")
// null 表示新建；有数字表示正在编辑该文章。
const editingId = ref(null)
// 表单数据与模板中的 v-model 双向同步。
const form = ref({
  title: "",
  summary: "",
  content: "",
})

// 清空表单，并退出编辑模式。
function resetForm() {
  editingId.value = null
  form.value = {
    title: "",
    summary: "",
    content: "",
  }
}

// 从后端加载文章列表，并处理登录失效和网络错误。
async function loadArticles() {
  loading.value = true
  errorMessage.value = ""

  try {
    articles.value = await getMyArticles()
  } catch (error) {
    if (error.response?.status === 401) {
      router.push("/login")
      return
    }

    if (!error.response) {
      errorMessage.value = "无法连接后端服务。"
      return
    }

    errorMessage.value =
      error.response.data?.detail || "文章加载失败。"
  } finally {
    loading.value = false
  }
}

// 将文章数据复制到表单，开始编辑草稿。
function startEdit(article) {
  editingId.value = article.id
  form.value = {
    title: article.title,
    summary: article.summary,
    content: article.content,
  }
}

// 根据 editingId 判断创建还是更新。
async function saveArticle() {
  submitting.value = true
  errorMessage.value = ""

  try {
    // 有 ID 时更新已有文章。
    if (editingId.value) {
      await updateArticle(editingId.value, form.value)
    } else {
      // 没有 ID 时创建新草稿。
      await createArticle(form.value)
    }

    resetForm()
    await loadArticles()
  } catch (error) {
    errorMessage.value =
      error.response?.data?.detail || "保存文章失败。"
  } finally {
    submitting.value = false
  }
}

// 删除文章前确认，并在成功后重新加载列表。
async function removeArticle(id) {
  if (!window.confirm("确定删除这篇草稿吗？")) {
    return
  }

  submitting.value = true
  errorMessage.value = ""

  try {
    await deleteArticle(id)
    await loadArticles()
  } catch (error) {
    errorMessage.value =
      error.response?.data?.detail || "删除文章失败。"
  } finally {
    submitting.value = false
  }
}

// 提交审核后重新加载列表，显示最新状态。
async function submitReview(id) {
  submitting.value = true
  errorMessage.value = ""

  try {
    await submitArticleReview(id)
    await loadArticles()
  } catch (error) {
    errorMessage.value =
      error.response?.data?.detail || "提交审核失败。"
  } finally {
    submitting.value = false
  }
}

// 页面首次挂载时执行文章加载。
onMounted(loadArticles)
</script>

<template>
  <div class="page-width">
    <RouterLink class="back-link" to="/">
      返回文章列表
    </RouterLink>

    <section class="login-panel">
      <p class="section-label">OwnerBlog / 我的文章</p>
      <h1>管理我的文章</h1>

      <form @submit.prevent="saveArticle">
        <label for="article-title">标题</label>
        <input
          id="article-title"
          v-model="form.title"
          required
        />

        <label for="article-summary">摘要</label>
        <textarea
          id="article-summary"
          v-model="form.summary"
        ></textarea>

        <label for="article-content">正文</label>
        <textarea
          id="article-content"
          v-model="form.content"
          required
        ></textarea>

        <button type="submit" :disabled="submitting">
          {{ editingId ? "保存修改" : "创建草稿" }}
        </button>

        <button
          v-if="editingId"
          type="button"
          :disabled="submitting"
          @click="resetForm"
        >
          取消编辑
        </button>
      </form>

      <p v-if="errorMessage" role="alert">
        {{ errorMessage }}
      </p>
    </section>

    <section>
      <p v-if="loading">正在加载文章……</p>
      <p v-else-if="!articles.length">还没有文章。</p>

      <article
        v-for="article in articles"
        :key="article.id"
      >
        <h2>{{ article.title }}</h2>
        <p>状态：{{ article.status }}</p>
        <p>更新时间：{{ article.updated_at }}</p>

        <button
          v-if="article.status === 'draft'"
          type="button"
          :disabled="submitting"
          @click="startEdit(article)"
        >
          编辑
        </button>

        <button
          v-if="article.status === 'draft'"
          type="button"
          :disabled="submitting"
          @click="removeArticle(article.id)"
        >
          删除
        </button>

        <button
          v-if="article.status === 'draft'"
          type="button"
          :disabled="submitting"
          @click="submitReview(article.id)"
        >
          提交审核
        </button>

        <span v-if="article.status === 'pending_review'">
          等待审核
        </span>
      </article>
    </section>
  </div>
</template>
```



### 9.3 注册路由

打开：

```
frontend/src/main.js
```

导入：

```
// 导入用户文章管理页面。
import MyArticlesView from "./views/MyArticlesView.vue"
```

routes 中加入：

```
// /my-articles 显示当前登录用户的文章。
{
  path: "/my-articles",
  component: MyArticlesView,
}
```

登录成功后，LoginView.vue 不应永远固定跳转首页，需要读取 `next` 查询参数。

在导入中加入 `useRoute`，并创建路由对象：

```js
// 读取 /login?next=... 中的目标地址。
import { useRoute } from "vue-router"
// 获取当前登录页面的路由信息。
const route = useRoute()
```

把 LoginView.vue 中：

```
router.push("/")
```

改为：

```
// 读取用户登录前想访问的页面。
const nextPath = route.query.next
// 只允许站内路径，避免开放重定向。
const safeNextPath =
  typeof nextPath === "string" && nextPath.startsWith("/")
    ? nextPath
    : "/my-articles"
// 登录成功后返回原页面。
router.push(safeNextPath)
```



### 9.4 页面验证

浏览器操作：

```
1. 先退出登录，访问 /my-articles。
2. 确认跳转到 /login?next=/my-articles。
3. 登录 user。
4. 确认自动回到 /my-articles，而不是固定回首页。
5. 创建标题、摘要和正文。
6. 点击创建草稿。
7. Network 确认 POST /api/articles 返回 201。
8. 确认列表显示 draft。
9. 点击编辑并保存。
10. 点击删除，确认列表移除。
11. 创建另一篇草稿。
12. 点击提交审核。
13. 确认显示 pending_review。
14. 确认待审核文章没有编辑按钮。
```



### 9.5 页面错误检查

```
/my-articles 返回 401
-> 登录状态失效，跳转 /login?next=/my-articles

登录成功
-> 读取 next 参数
-> 返回登录前的站内页面

POST 返回 403
-> 检查 csrftoken 和 X-CSRFToken

页面一直显示 mock 文章
-> frontend/.env 必须有 VITE_USE_MOCKS=false

页面请求失败且没有 response
-> 检查 Django 是否运行在 127.0.0.1:8000
```



## 10. 自动化检查与回归测试

> 本阶段运行可以重复执行的检查。它和 Phase 8、Phase 9 的浏览器手动验证不是同一件事。

自动化检查适合确认项目以后没有被改坏，例如：

- Django 配置和 URL 是否可以加载。
- 已写入 `tests.py` 的后端测试是否通过。
- 数据库迁移是否与模型一致。
- Vue 项目是否可以正常构建。

`manage.py test` 只会运行已经写在测试文件中的测试，不会自动替你测试所有功能。如果某个场景没有测试代码，它不会因为命令执行成功就代表该场景已经被覆盖。

### 10.1 先补充 `tests.py`，不要替换原文件

打开：

```
backend/articles/tests.py
```

当前文件已经有公开文章相关的 4 个测试。不要删除原来的导入、`setUp`、已存在的测试，也不要把下面代码粘贴到文件最外层。

把下面代码追加到现有 `ArticleAPITests` 类的最后一个测试方法后面。注意：这些方法必须和已有的 `test_...` 方法保持相同的缩进，仍然属于 `ArticleAPITests` 类。

```python
    def test_unauthenticated_user_article_requests_return_401(self):
        # 未登录用户不能读取自己的文章列表。
        response = self.client.get("/api/my-articles")
        self.assertEqual(response.status_code, 401)

        # 未登录用户不能创建文章。
        response = self.client.post(
            "/api/articles",
            {
                "title": "未登录文章",
                "content": "正文",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_my_articles_includes_all_statuses_but_only_current_user(self):
        # 创建另一个用户的文章，用来验证数据隔离。
        other_user = get_user_model().objects.create_user(
            username="other-user",
            password="other-password",
        )
        other_article = Article.objects.create(
            author=other_user,
            title="其他用户文章",
            content="其他用户正文",
            status=ArticleStatus.DRAFT,
        )

        # 模拟当前用户已经登录。
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/my-articles")

        self.assertEqual(response.status_code, 200)
        returned_ids = {item["id"] for item in response.data["items"]}
        returned_statuses = {item["status"] for item in response.data["items"]}
        self.assertIn(self.published_article.id, returned_ids)
        self.assertIn(self.draft_article.id, returned_ids)
        self.assertNotIn(other_article.id, returned_ids)
        self.assertIn("published", returned_statuses)
        self.assertIn("draft", returned_statuses)

    def test_create_article_uses_current_user_and_forces_draft(self):
        # 模拟当前用户已经登录。
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/articles",
            {
                "title": "新文章",
                "summary": "新文章摘要",
                "content": "新文章正文",
                "author": 999,
                "status": "published",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        article = Article.objects.get(id=response.data["id"])
        self.assertEqual(article.author, self.user)
        self.assertEqual(article.status, ArticleStatus.DRAFT)

    def test_owner_can_edit_draft_but_not_pending_review(self):
        # 模拟当前用户已经登录。
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/articles/{self.draft_article.id}",
            {"title": "修改后的标题"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.draft_article.refresh_from_db()
        self.assertEqual(self.draft_article.title, "修改后的标题")

        # 待审核文章不能再次编辑。
        self.draft_article.status = ArticleStatus.PENDING_REVIEW
        self.draft_article.save()
        response = self.client.patch(
            f"/api/articles/{self.draft_article.id}",
            {"title": "不应保存"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_owner_can_submit_draft_for_review(self):
        # 模拟当前用户已经登录。
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f"/api/articles/{self.draft_article.id}/submit-review",
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.draft_article.refresh_from_db()
        self.assertEqual(
            self.draft_article.status,
            ArticleStatus.PENDING_REVIEW,
        )

    def test_owner_can_delete_article(self):
        # 模拟当前用户已经登录。
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            f"/api/articles/{self.draft_article.id}"
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            Article.objects.filter(id=self.draft_article.id).exists()
        )

    def test_other_user_cannot_operate_my_article(self):
        # 创建另一个用户并登录该用户。
        other_user = get_user_model().objects.create_user(
            username="another-user",
            password="another-password",
        )
        self.client.force_authenticate(user=other_user)

        # 跨用户文章统一返回 404，不泄露文章是否存在。
        response = self.client.patch(
            f"/api/articles/{self.draft_article.id}",
            {"title": "越权修改"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.delete(
            f"/api/articles/{self.draft_article.id}"
        )
        self.assertEqual(response.status_code, 404)
```

这一步是“补充”，不是“替换”：

```
原来的 4 个测试       -> 保留，继续验证公开文章 API
新增的 7 个测试       -> 验证登录、用户文章、状态流转和权限
```

如果你看到 `IndentationError`，通常是因为新增方法没有放在 `ArticleAPITests` 类中，或者缩进没有和原来的 `test_...` 方法一致。

### 10.2 运行后端测试

```
cd E:\Desktop\VibeCoding\ownerblog\backend
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check
.\.venv\Scripts\python.exe manage.py test
```

预期：

```
OK
```



### 10.3 运行前端构建

```
cd E:\Desktop\VibeCoding\ownerblog\frontend
pnpm build
```

预期：

```
built successfully
```



### 10.4 测试覆盖目标

下面是 Day 3 应该覆盖的场景清单。当前项目如果还没有对应的 `tests.py` 测试代码，这些项目仍然需要通过 Phase 8、Phase 9 的手动操作验证；勾选它们不代表 `manage.py test` 已经自动覆盖。

认证：

- [x] 正确登录返回 200
- [x] 错误密码返回 401
- [x] 未登录 me 返回 401
- [x] 缺少 CSRF 返回 403
- [x] 登录后刷新仍保持登录
- [x] 退出后 me 返回 401

权限：

- [x] 未登录创建文章返回 401
- [x] 创建文章返回 201 且状态为 draft
- [x] 伪造 author 仍使用当前用户
- [x] 伪造 published 仍保存为 draft
- [x] 只能看到自己的文章
- [x] 不能查看他人的文章
- [x] 不能编辑他人的文章
- [x] 不能删除他人的文章
- [x] 草稿可以编辑
- [x] 草稿可以删除
- [x] 草稿可以提交审核
- [x] pending_review 不能编辑
- [x] 公开 API 不返回草稿和待审核文章



## 11. 复盘和提交

用自己的话回答：

```
1. Session 保存在哪里，Cookie 保存什么？
    Session保存在服务器，Cookie保存在浏览器
2. authenticate、login、logout 分别做什么？
     authenticate做身份认证，login做登录（保证登录状态共享），logout做退出登录（清理Session中的用户登录状态）
3. request.user 从哪里来？
      从Session返回的用户对象，没有登录则是匿名用户（通过Session中间件和Authentication中间件）
4. csrftoken 和 sessionid 的区别是什么？
     csrftoken是csrf防护主要是向服务器证明是真实请求不是伪造的校验值，sessionid存在Cookie中存储具体是哪一条Session通过Session中间件得到Session，用户登录状态存在服务器没有存在浏览器
5. 为什么 author 必须由后端设置？
     如果让用户自己设置那就可能导致填写不存在的用户或者直接访问到其他用户的数据获得其他用户的操作权限，这样就做不到数据隔离了，也不安全
6. 为什么前端隐藏按钮不能代替后端权限？
     因为用户还可以在地址栏输入URL，这样也可以跳过按钮直接访问到其他用户的数据
7. 为什么跨用户操作返回 404？
     因为进入View之后再查询数据的时候对应的用户不一致，找不到当前用户下的这篇文章就会返回http404
8. user、loading、submitting 分别表示什么？
    user表示用户，loading表示内标请求，submitting表示请求进行中
9. 为什么不把密码和 Session ID 放入 localStorage？
    因为localStorage可以被JS获取到，一般用来存储用户的偏好，如果存密码可能获取到密码内容，而且Django的密码存储也是哈希值（不可逆）如果放Session ID那别人也能拿到这条Session也就可以被别人拿到之后冒充这个人访问
    
```

确认没有提交私密文件后：

```
cd E:\Desktop\VibeCoding\ownerblog
git status
git add backend frontend plan/day3.md
git commit -m "feat(auth): add session authentication and user article management"
```



## 12. Day 3 最终标准

- [x] 后端 check 通过
- [x] makemigrations --check 通过
- [x] 正确登录、错误登录和退出验证通过
- [x] CSRF 验证通过
- [x] Session 创建和清理验证通过
- [x] Vue 登录状态可以自动更新
- [x] 用户文章 API 完成
- [x] 对象级权限完成
- [x] /my-articles 页面完成
- [x] 至少 12 个认证、权限和状态场景通过
- [x] Day 2 公开文章列表和详情没有回归
- [x] 完成 Git commit