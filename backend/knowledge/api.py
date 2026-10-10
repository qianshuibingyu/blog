from rest_framework.permissions import AllowAny         # 导入匿名访问权限
from rest_framework.response import Response            # 导入统一响应对象
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_503_SERVICE_UNAVAILABLE      # 导入状态码
from rest_framework.views import APIView                # 导入 DRF 视图基类
from .answering import AnswerModelError, answer_from_retrieval       # 导入阶段 10 服务
from .retrieval import InvalidQuestionError, RetrievalServiceError, retrieve_public_chunks       # 导入阶段 9 服务


# 定义知识问题接口
class KnowledgeChatAPIView(APIView):
    # 公开知识问答允许匿名访问
    permission_classes = [AllowAny]
    # 处理 POST 请求
    def post(self, request):
        payload = request.data
        # 拒绝非对象请求体
        if not isinstance(payload, dict):
            return Response({"error": "请求体必须是 JSON 对象"}, status=HTTP_400_BAD_REQUEST)
        # 读取唯一允许的输入字段
        question = payload.get("question")
        # 执行检索和回答
        try:
            report = retrieve_public_chunks(question=question)
            result = answer_from_retrieval(report)
        # 捕获问题参数错误
        except InvalidQuestionError as exc:
            # 不暴露堆栈
            return Response({"error": str(exc)}, status=HTTP_400_BAD_REQUEST)
        except (RetrievalServiceError, AnswerModelError):
            # 外部检索或回答服务不可用时返回稳定的服务错误，而不是 500 堆栈。
            return Response(
                {"error": "知识问答服务暂时不可用，请稍后重试"},
                status=HTTP_503_SERVICE_UNAVAILABLE,
            )
        # 返回稳定响应
        return Response({"status": result.status, "answer": result.answer, "sources": result.sources}, status=HTTP_200_OK)
