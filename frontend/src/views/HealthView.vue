<script setup>
import {onMounted, ref} from "vue"
import {apiClient} from "../api/client"
const loading=ref(true)
const status=ref("")
const errorMessage=ref("")

async function checkHealth(){
    loading.value=true
    errorMessage.value=""

    try{
        const response=await apiClient.get("/health")
        status.value=response.data.status
    }catch(error){
        errorMessage.value="后端连接失败，请确认 Django 服务是否启动。"
        console.error("Health 请求失败: ", error)
    }finally{
        loading.value=false
    }
}

onMounted(()=>{
    checkHealth()
})
</script>

<template>
<div class="page-width health-page">
    <section class="health-intro">
        <!-- 页面的小标题。 -->
        <p class="section-label">
            OwnerBlog / Health Check
        </p>

        <!-- 页面主标题。 -->
        <h1>
            检查前后端<br />
            <em>是否已经连通</em>
        </h1>

        <!-- 页面功能说明。 -->
        <p class="health-description">
            这个页面只检查 Vue、Axios、Vite Proxy 和 Django 之间的请求链接。
        </p>
    </section>

    <!--loading 状态区域。v-if 表示只有 loading 为 true 时才显示。-->
    <section v-if="loading" class="health-result health-loading">
        <span class="status-dot"></span>
        <h2>正在检查后端连接......</h2>
        <p>Axios 正在请求 /api/health</p>
    </section>

    <!--
      error 状态区域。
      v-else-if 表示：
      只有前面的 loading 为 false，
      并且 errorMessage 有内容时才显示。
    -->
    <section v-else-if="errorMessage" class="health-result health-error" role="alert">
        <span class="status-dot"></span>
        <h2>连接失败</h2>
        <p>{{errorMessage}}</p>

        <!--
            点击按钮后重新检查。
            @click 会监听点击事件。
            checkHealth 是点击后执行的函数。
        -->
        <button type="button" @click="checkHealth">
        重新检查
        </button>
    </section>

    <!--
      success 状态区域。
      v-else 表示：
      loading 为 false，
      并且 errorMessage 为空时显示。
    -->
    <section v-else class="health-result health-success">
        <span class="status-dot"></span>
        <h2>后端连接正常</h2>
        <p>Health API 返回状态： {{status}}</p>
    </section>
</div>
</template>

<style scoped>
/* Health 页面的整体容器。 */
.health-page{
    padding-top: 70px;
    padding-bottom: 100px;
}

/* 页面介绍区域。 */
.health-intro{
    max-width: 700px;
    margin-bottom: 60px;
}

/* Health 页面的主标题。 */
.health-intro h1{
    margin: 18px 0 24px;
    color: var(--ink);
    font-family: Newsreader, Georgia, serif;
    font-size: clamp(48px, 7vw, 82px);
    font-weight: 400;
    line-height: .95;
}

/* 页面功能说明文字。 */
.health-description{
    max-width: 520px;
    color: var(--muted);
    font-size: 15px;
    line-height: 1.8;
}

/* 三种状态共用的结果区域。 */
.health-result{
    max-width: 700px;
    border-top: 1px solid var(--ink);
    border-bottom: 1px solid var(--line);
    padding: 28px 0;
}

/* 状态标题。 */
.health-result h2{
    margin: 12px 0 8px;
    color: var(--link);
    font-family: Newsreader, Georgia, serif;
    font-size: 32px;
    font-weight: 400
}

/* 状态说明文字。 */
.health-result p{
    margin: 0;
    color: var(--muted);
    line-height: 1.7;
}

/* 三种状态前面的圆点。 */
.status-dot{
    display: block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--accent);
}

/* success 状态的圆点颜色。 */
.health-success .status-dot{
    background: #52718b;
}

/* error 状态的圆点颜色。 */
.health-error .status-dot{
    background: #a0525f;
}

/* 重新检查按钮。 */
.health-result button{
    margin-top: 20px;
    border: 1px solid var(--accent);
    background: var(--accent);
    color: white;
    padding: 11px 17px;
    cursor: pointer;
    font-size: 13px;
}

/* 鼠标悬停时降低按钮透明度。 */
.health-result button:hover{
    opacity: .85;
}
</style>