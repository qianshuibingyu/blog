"""通过本地或 OpenAI-compatible provider 生成 Embedding。"""

import math
from dataclasses import dataclass
from functools import lru_cache
from time import sleep
from typing import Any, Sequence

from django.conf import settings
from openai import OpenAI

from .models import ArticleChunk


class EmbeddingError(ValueError):
    """Embedding 输入或配置错误。"""


class EmbeddingConfigurationError(EmbeddingError):
    """Embedding 配置不能使用。"""


class EmbeddingRequestError(EmbeddingError):
    """请求或本地模型推理失败。"""


class EmbeddingResponseError(EmbeddingError):
    """返回数据不能作为向量使用。"""


@dataclass(frozen=True)
class EmbeddedChunk:
    """ArticleChunk 与其 Embedding 向量的对应关系。"""

    article_chunk_id: int
    chunk_index: int
    content: str
    embedding: list[float]
    embedding_model: str


@lru_cache(maxsize=4)
def _load_local_model(model_name: str, device: str) -> Any:
    """按模型和设备缓存本地 Sentence Transformers 模型。"""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise EmbeddingConfigurationError(
            "EMBEDDING_PROVIDER=local 需要安装 sentence-transformers"
        ) from exc

    try:
        return SentenceTransformer(model_name, device=device)
    except Exception as exc:
        raise EmbeddingRequestError(
            f"本地 Embedding 模型加载失败：{type(exc).__name__}"
        ) from exc


class EmbeddingService:
    """统一封装本地 Sentence Transformers 和远程 Embedding API。"""

    LOCAL_PROVIDER = "local"
    REMOTE_PROVIDER = "openai_compatible"
    QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："

    def __init__(self, client: Any | None = None):
        provider = str(settings.EMBEDDING_PROVIDER).strip().lower()
        if provider not in {self.LOCAL_PROVIDER, self.REMOTE_PROVIDER}:
            raise EmbeddingConfigurationError(
                "EMBEDDING_PROVIDER 必须是 local 或 openai_compatible"
            )
        if not settings.EMBEDDING_MODEL:
            raise EmbeddingConfigurationError("EMBEDDING_MODEL 不能为空")
        if settings.EMBEDDING_BATCH_SIZE <= 0:
            raise EmbeddingConfigurationError("EMBEDDING_BATCH_SIZE 必须大于 0")
        if settings.EMBEDDING_MAX_RETRIES < 0:
            raise EmbeddingConfigurationError("EMBEDDING_MAX_RETRIES 不能小于 0")

        self.provider = provider
        self.model = settings.EMBEDDING_MODEL
        self.client = client

        # 本地模型延迟到第一次 embedding 时加载；远程 client 只在远程模式构造。
        if self.provider == self.REMOTE_PROVIDER and client is None:
            self.client = OpenAI(
                api_key=settings.MODEL_API_KEY,
                base_url=settings.MODEL_BASE_URL,
                timeout=settings.EMBEDDING_TIMEOUT_SECONDS,
            )

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """按配置的批量大小生成与输入同序的向量。"""
        return self._embed_texts(texts)

    def embed_query(self, query: str) -> list[float]:
        """生成查询向量；本地 BGE 模型使用检索查询指令。"""
        normalized = self._validate_texts([query])
        if self.provider == self.LOCAL_PROVIDER:
            normalized[0] = f"{self.QUERY_INSTRUCTION}{normalized[0]}"
            return self._embed_texts(normalized)[0]
        return self._embed_texts([query])[0]

    def embed_article_chunks(self, *, article_id: int) -> list[EmbeddedChunk]:
        """读取文章片段并生成供 Chroma 使用的映射结果。"""
        chunks = list(
            ArticleChunk.objects.filter(article_id=article_id).order_by("chunk_index")
        )
        if not chunks:
            raise EmbeddingError("文章没有可向量化的 ArticleChunk")

        vectors = self.embed_texts([chunk.content for chunk in chunks])
        return [
            EmbeddedChunk(
                chunk.id,
                chunk.chunk_index,
                chunk.content,
                vector,
                self.model,
            )
            for chunk, vector in zip(chunks, vectors)
        ]

    def _embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        normalized = self._validate_texts(texts)
        vectors: list[list[float]] = []
        for start in range(0, len(normalized), settings.EMBEDDING_BATCH_SIZE):
            batch = normalized[start : start + settings.EMBEDDING_BATCH_SIZE]
            vectors.extend(self._embed_batch(batch))

        if len(vectors) != len(normalized):
            raise EmbeddingResponseError("Embedding 数量与输入数量不一致")
        self._validate_vectors(vectors, len(normalized))
        return vectors

    def _validate_texts(self, texts: Sequence[str]) -> list[str]:
        normalized = list(texts)
        if not normalized:
            raise EmbeddingError("Embedding 输入不能为空")
        if any(not isinstance(text, str) or not text.strip() for text in normalized):
            raise EmbeddingError("Embedding 输入必须全部是非空字符串")
        return normalized

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        if self.provider == self.LOCAL_PROVIDER:
            return self._embed_local_batch(texts)
        return self._embed_remote_batch(texts)

    def _embed_local_batch(self, texts: list[str]) -> list[list[float]]:
        model = self.client
        if model is None:
            model = _load_local_model(
                self.model,
                str(getattr(settings, "EMBEDDING_DEVICE", "cpu")),
            )
            self.client = model

        try:
            raw_vectors = model.encode(
                texts,
                batch_size=settings.EMBEDDING_BATCH_SIZE,
                normalize_embeddings=True,
                convert_to_numpy=False,
                show_progress_bar=False,
            )
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingRequestError(
                f"本地 Embedding 推理失败：{type(exc).__name__}"
            ) from exc

        vectors = self._coerce_local_vectors(raw_vectors)
        self._validate_vectors(vectors, len(texts))
        return vectors

    def _embed_remote_batch(self, texts: list[str]) -> list[list[float]]:
        if self.client is None:
            raise EmbeddingConfigurationError("远程 Embedding client 未初始化")

        for attempt in range(settings.EMBEDDING_MAX_RETRIES + 1):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                )
                return self._parse_response(response, len(texts))
            except EmbeddingResponseError:
                raise
            except Exception as exc:
                if (
                    not self._is_retryable(exc)
                    or attempt >= settings.EMBEDDING_MAX_RETRIES
                ):
                    raise EmbeddingRequestError(
                        f"Embedding 请求失败：{type(exc).__name__}"
                    ) from exc
                delay = settings.EMBEDDING_RETRY_BACKOFF_SECONDS * (2**attempt)
                if delay > 0:
                    sleep(delay)

        raise EmbeddingRequestError("Embedding 请求未返回结果")

    def _coerce_local_vectors(self, raw_vectors: Any) -> list[list[float]]:
        """把 list、numpy.ndarray 或 torch.Tensor 转成普通 Python 列表。"""
        try:
            if hasattr(raw_vectors, "tolist"):
                raw_vectors = raw_vectors.tolist()
            if not isinstance(raw_vectors, (list, tuple)):
                raise TypeError("vectors must be a sequence")

            vectors: list[list[float]] = []
            for raw_vector in raw_vectors:
                if hasattr(raw_vector, "tolist"):
                    raw_vector = raw_vector.tolist()
                if not isinstance(raw_vector, (list, tuple)):
                    raise TypeError("vector must be a sequence")
                vectors.append([float(value) for value in raw_vector])
            return vectors
        except (TypeError, ValueError, OverflowError) as exc:
            raise EmbeddingResponseError("本地 Embedding 响应结构无效") from exc

    def _validate_vectors(
        self,
        vectors: list[list[float]],
        expected_count: int,
    ) -> None:
        if len(vectors) != expected_count or not vectors:
            raise EmbeddingResponseError("Embedding 响应数量不一致")
        if any(
            not vector
            or any(not math.isfinite(value) for value in vector)
            for vector in vectors
        ):
            raise EmbeddingResponseError(
                "Embedding 向量包含非有限或非数值元素"
            )
        dimension = len(vectors[0])
        if any(len(vector) != dimension for vector in vectors):
            raise EmbeddingResponseError("Embedding 向量维度不一致")

    def _parse_response(
        self,
        response: Any,
        expected_count: int,
    ) -> list[list[float]]:
        data = getattr(response, "data", None)
        if not isinstance(data, list) or len(data) != expected_count:
            raise EmbeddingResponseError("Embedding 响应数量不一致")

        indexed: list[tuple[int, list[float]]] = []
        for position, item in enumerate(data):
            index = getattr(item, "index", position)
            vector = getattr(item, "embedding", None)
            if not isinstance(index, int) or not isinstance(vector, list) or not vector:
                raise EmbeddingResponseError("Embedding 响应结构无效")
            if not all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(float(value))
                for value in vector
            ):
                raise EmbeddingResponseError(
                    "Embedding 向量包含非有限或非数值元素"
                )
            indexed.append((index, [float(value) for value in vector]))

        indexed.sort(key=lambda item: item[0])
        if [index for index, _ in indexed] != list(range(expected_count)):
            raise EmbeddingResponseError("Embedding 响应 index 不连续")
        vectors = [vector for _, vector in indexed]
        self._validate_vectors(vectors, expected_count)
        return vectors

    def _is_retryable(self, exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        return status_code in {
            408,
            409,
            429,
            500,
            502,
            503,
            504,
        } or type(exc).__name__ in {"APITimeoutError", "APIConnectionError"}
