import { ref } from "vue"

// App.vue 和 LoginView.vue 共享当前登录用户。
export const currentUser = ref(null)
