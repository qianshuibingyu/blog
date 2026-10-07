from dataclasses import dataclass       # 导入不可变结果结构
import dataclasses
from math import isfinite          # 导入有限数值校验函数
from django.conf import settings      # 导入 Django 配置
from articles.models import ArticleStatus, IndexStatus        # 导入文章公开状态
from .models import ArticleChunk       # 导入真实 ArticleChunk 模型
from .llm import EmbeddingService          # 导入阶段 6 的 Embedding 服务
from .vector_store import ChromaVectorStore        # 导入阶段 7 的 Chroma 适配器
# 定义检索基础异常
class RetrievalError(RuntimeError):
    pass

# 定义输入错误
class InvalidQuestionError(RetrievalError):
    pass

# 定义外部服务错误
class RetrievalServiceError(RetrievalError):
    pass

# 保证结果创建后不能被修改
@dataclass(frozen=True)
# 表示一条公开片段
class RetrievedChunk:
    article_id: int
    article_title: str
    article_chunk_id: int
    chunk_index: int
    content: str
    score: float
    vector_document_id: str