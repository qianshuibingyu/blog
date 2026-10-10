from dataclasses import dataclass       # 导入不可变结果结构
import dataclasses
from math import isfinite          # 导入有限数值校验函数
from unicodedata import category
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

@dataclass(frozen=True)
# 表示一次检索报告
class RetrievalReport:
    question: str
    results: list[RetrievedChunk]
    candidate_count: int
    accepted_count: int

# 校验用户问题
def validate_question(question: str) -> str:
    # 拒绝非字符串
    if not isinstance(question, str):
        raise InvalidQuestionError("question 必须是字符串")
    value = question.strip()
    # 读取问题长度上限
    limit = int(getattr(settings, "QUERY_MAX_LENGTH", 1000))
    # 拒绝空问题
    if not value:
        raise InvalidQuestionError("question 不能为空")
    # 拒绝超长问题
    if len(value) > limit:
        raise InvalidQuestionError("question 超过长度限制")
    # 拒绝控制字符问题
    if not any(not char.isspace() and category(char) != "Cc" for char in value):
        raise InvalidQuestionError("question 不包含有效文字")
    return value     # 返回规范化问题

# 转换 cosine distance
def distance_to_similarity(distance: float) -> float:
    # 校验距离
    if not isinstance(distance, (int, float)) or not isfinite(distance):
        raise RetrievalServiceError("Chroma distance 非法")
    # 返回返回受限的相似度
    return max(0.0, min(1.0, 1.0-float(distance)))

# 执行公开检索
def retrieve_public_chunks(*, question:str, embedding_service=None, vector_store=None) -> RetrievalReport:
    # 校验输入、使用阶段6服务或测试替身、使用阶段7适配器或测试替身
    value = validate_question(question)
    embedder = embedding_service or EmbeddingService()
    store = vector_store or ChromaVectorStore()
    # 统一封装外部服务错误
    try:
        # 生成问题向量
        vector = embedder.embed_query(value)
        # 校验向量非空
        if not isinstance(vector, list) or not vector:
            raise RetrievalServiceError("查询向量为空")
        # 校验每个维度
        if not all(isinstance(item, (int, float)) and isfinite(item) for item in vector):
            raise RetrievalServiceError("查询向量包含非法数值")
        # 读取候选上限、访问量阶段7的向量库
        top_k = int(getattr(settings, "CHROMA_QUERY_TOP_K", 20))
        candidates = store.query(vector, top_k)
    # 保留已分类错误
    except RetrievalError:
        raise      # 继续向上层传播
    # 捕获底层 SDK 错误
    except Exception as exc:
        # 不伪装成空结果
        raise RetrievalServiceError("检索服务失败")

    # 校验适配器返回值
    if not isinstance(candidates, list):
        raise RetrievalServiceError("Chroma 返回结构错误")
    # 收集候选 ID
    ids = [item.get("id") for item in candidates if isinstance(item, dict) and item.get("id")]
    # 批量回查公开片段
    chunks = ArticleChunk.objects.filter(article__status=ArticleStatus.PUBLISHED,article__index_status=IndexStatus.INDEXED, vector_document_id__in=ids).select_related("article")
    # 建立向量　ID 映射
    by_id = {chunk.vector_document_id: chunk for chunk in chunks}
    # 读取相似度阈值、最终数量上限
    threshold = float(getattr(settings, "SIMILARITY_THRESHOLD", 0.75))
    maximum = int(getattr(settings, "MAX_RETRIEVED_CHUNKS", 5))
    # 创建结果列表、去重集合
    results = []
    seen = set()
    # 逐个处理候选
    for item in candidates:
        # 跳过非法候选
        if not isinstance(item, dict):
            continue
        # 读取向量 ID
        vector_id = item.get("id")
        # 跳过空值和重复值
        if not vector_id or vector_id in seen:
            continue
        # 获取数据库片段
        chunk = by_id.get(vector_id)
        # 过滤孤立向量
        if chunk is None:
            continue
        # 计算统一相似度
        score = distance_to_similarity(item.get("distance", 1.0))
        # 过滤低相关结果
        if score < threshold:
            continue
        # 标记已接收结果
        seen.add(vector_id)
        # 使用数据库权威正文
        results.append(RetrievedChunk(article_id=chunk.article_id, article_title=chunk.article.title, article_chunk_id=chunk.id, chunk_index=chunk.chunk_index, content=chunk.content, score=score, vector_document_id=vector_id))
        # 达到返回数量上限则停止收集
        if len(results) >= maximum:
            break
    # 按相似度降序
    results.sort(key=lambda item: item.score, reverse=True)
    # 返回报告
    return RetrievalReport(question=value, results=results, candidate_count=len(candidates), accepted_count=len(results))
