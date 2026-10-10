"""阶段 7：将 EmbeddedChunk 幂等写入 Chroma"""
import math
from typing import Any
import chromadb
from django.conf import settings
from django.db import transaction
from articles.models import Article
from .llm import EmbeddedChunk
from .models import ArticleChunk

"""向量校验、Chroma 写入或数据库映射失败"""
# 定义阶段 7 的统一错误类型
class VectorStoreError(RuntimeError):
    pass

"""返回 article:文章 ID:chunk:片段序号格式的稳定 ID"""
# 不能使用随机UUID，构造可重复的 Chroma 文档 ID
def build_vector_document_id(article_id:int, chunk_index:int) -> str:
    # 检验文章主键必须是正整数
    if not isinstance(article_id, int) or article_id <= 0:
        raise VectorStoreError("article_id 必须是正整数")
    # 检验片段序号必须是非负整数
    if not isinstance(chunk_index, int) or chunk_index < 0:
        raise VectorStoreError("chunk_index 必须是非负整数")
    # 使用稳定规则生成 ID
    document_id = f"article:{article_id}:chunk:{chunk_index}"
    # 确认不会超过 ArticleChunk.vector_document_id 的长度限制
    if len(document_id) > 200:
        raise VectorStoreError("Chroma 文档 ID 超过 200 个字符")
    return document_id       # 返回稳定文档 ID

"""提供文章片段 upsert、过期删除和 ArticleChunk 映射回写"""
# 封装本地 PersistentClient 和 collection 操作
class ChromaVectorStore:
    # 接收可选测试客户端以避免测试依赖磁盘
    def __init__(self, client:Any|None=None):
        # 创建或复用本地客户端
        self.client = client or chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)
        # 读取并清理 collection 名称
        collection_name = (
            f"{settings.CHROMA_COLLECTION_NAME}_"
            f"{settings.EMBEDDING_COLLECTION_VERSION}"
        ).strip()
        # collection 名称为空时无法安全写入
        if not collection_name:
            raise VectorStoreError("CHROMA_COLLECTION_NAME 不能为空")
        # 获取固定 collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        
    # 幂等写入一篇文章的全部向量
    def upsert_article_chunks(self, *, article_id:int, embedded_chunks:list[EmbeddedChunk]) -> int:
        # 确认文章真实存在、一次读取全部数据库片段
        article = self._load_article(article_id)
        chunks = list(ArticleChunk.objects.filter(article_id=article_id).order_by("chunk_index"))
        # 在任何 Chroma 操作前完成完整性校验
        self._validate_inputs(chunks, embedded_chunks)
        # 生成稳定 ID 列表
        ids = [build_vector_document_id(article_id, item.chunk_index) for item in embedded_chunks]
        # 使用阶段 6 生成向量时的正文、返回的乡里那个、构造标量 metadata
        documents = [item.content for item in embedded_chunks]
        embeddings = [item.embedding for item in embedded_chunks]
        metadatas = [self._build_metadata(article, chunk, item) for chunk, item in zip(chunks, embedded_chunks)]
        # 以稳定 ID 幂等写入、删除本次片段集合之外的旧向量
        self.collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        self._delete_stale_vectors(article_id=article_id,current_ids=ids)
        # 用短事务回写数据库映射
        with transaction.atomic():
            # 遍历数据库片段和 Chroma ID
            for chunk, document_id in zip(chunks, ids):
                # 只更新发生变化的映射
                if chunk.vector_document_id != document_id:
                    chunk.vector_document_id = document_id
                    chunk.save(update_fields=["vector_document_id", "updated_at"])    # 保存映射和更新时间
        return len(ids)         # 返回本次成功写入的片段数量

    # 为阶段 9 提供只读相似度查询入口
    def query(self, vector:list[float], top_k:int) -> list[dict[str, object]]:
        # 拒绝空向量和非法数值
        if not vector or not all(math.isfinite(float(value)) for value in vector):
            raise VectorStoreError("查询向量必须是有限数值列表")
        # 检查候选数量必须为正整数
        if not isinstance(top_k, int) or top_k <= 0:
            raise VectorStoreError("top_k 必须是正整数")
        # 调用 Chroma 只读查询接口、读取第一条查询的文档 ID 列表和查询的距离列表
        result = self.collection.query(query_embeddings=[vector], n_results=top_k, include=["distances"])
        ids = (result.get("ids") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        return [{"id": str(vector_id), "distance": float(distance)} for vector_id, distance in zip(ids, distances)]    # 转成阶段 9 的稳定候选结构

    # 删除指定文章的全部 Chroma 向量
    def delete_article_vectors(self, *, article_id:int) -> int:
        # 确认文章 ID 有效，避免误删掉用错误、查询当前文章的稳定记录 ID、读取 Chroma 返回的 ID 列表
        self._load_article(article_id)
        result=self.collection.get(where={"article_id": str(article_id)}, include=[])
        ids = list(result.get("ids", []))
        # 只有存在的记录才执行删除
        if ids:
            self.collection.delete(ids=ids)
        return len(ids)   # 返回实际删除数量

    # 读取文章并统一处理不存在错误
    def _load_article(self, article_id:int) -> Article:
        # 捕获 Django 的不存在异常
        try:
            return Article.objects.get(pk=article_id)     # 查询真实文章
        except Article.DoesNotExist as exc:
            raise VectorStoreError(f"文章不存在:{article_id}") from exc     # 阻止写入孤立向量

    # 检验数据库和内存契约
    def _validate_inputs(self, chunks:[ArticleChunk], embedded_chunks:list[EmbeddedChunk]) -> None:
        # 空向量集合不能代表成功索引
        if not embedded_chunks:
            raise VectorStoreError("embedded_chunks 不能为空")
        # 数量必须与数据库当前片段完全一致
        if len(chunks) != len(embedded_chunks):
            raise VectorStoreError("Embedding 数量与 ArticleChunk 数量不一致")
        # 生成应有的连续片段序号、读取数据库片段序号和 Embedding 片段序号
        expected_indexes = list(range(len(chunks)))
        actual_indexes = [chunk.chunk_index for chunk in chunks]
        input_indexes = [item.chunk_index for item in embedded_chunks]
        # 检查两边序号都从零连续
        if actual_indexes != expected_indexes or input_indexes != expected_indexes:
            raise VectorStoreError("chunk_index 必须从 0 开始连续")
        # 逐项比对数据库片段和 Embedding 结果
        for chunk, item in zip(chunks, embedded_chunks):
            # 检查结果回指正确数据库主键
            if item.article_chunk_id != chunk.id:
                raise VectorStoreError("EmbeddedChunk.article_chunk_id 与数据库不一致")
            # 检查向量正文与持久化正文一致
            if item.content != chunk.content:
                raise VectorStoreError("Embedding 正文与 ArticleChunk.content 不一致")
            # 模型名称必须可记录
            if not item.embedding_model.strip():
                raise VectorStoreError("embedding_model 不能为空")
            # 检查向量非空且数值有限
            if not item.embedding or not all(math.isfinite(float(value)) for value in item.embedding):
                raise VectorStoreError("embedding 必须是有限数值列表")
        # 收集本批次向量维度
        dimensions = {len(item.embedding) for item in embedded_chunks}
        # 一个 collection 内本批次必须只有一个维度
        if len(dimensions) != 1:
            raise VectorStoreError("同一批 Embedding 的维度必须一致")

    # 构造 Chroma 支持的标量 metadata
    def _build_metadata(self, article:Article, chunk:ArticleChunk, item:EmbeddedChunk) -> dict[str, str]:
        return {
            "article_id":str(article.id), 
            "article_chunk_id":str(chunk.id), 
            "chunk_index":str(chunk.chunk_index), 
            "title":article.title, 
            "content_hash":article.content_hash or "", 
            "version":str(article.version), 
            "embedding_model":item.embedding_model, 
            "embedding_provider": item.embedding_provider,
            "embedding_dimension": str(item.embedding_dimension),
            "source": "ownerblog"
        }

    # 删除当前文章不再使用的旧向量
    def _delete_stale_vectors(self, *, article_id:int, current_ids:list[str]) -> None:
        # 查询当前文章、计算不属于本次结果的旧 ID
        result = self.collection.get(where={"article_id":str(article_id)}, include=[])
        stale_ids = [item for item in result.get("ids", []) if item not in current_ids]
        # 只有存在旧记录时才调用删除
        if stale_ids:
            self.collection.delete(ids=stale_ids)
