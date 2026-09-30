"""阶段 4：将 CleanedDocument 切分为稳定的 TextChunk。"""

from dataclasses import dataclass
from typing import Iterable

from django.conf import settings

from .chunk_types import TextChunk
from .content_types import CleanedDocument


class ChunkingError(ValueError):
    """输入、配置或切分结果不合法。"""


@dataclass(frozen=True)
class ChunkConfig:
    """不可变的切分配置，长度单位为 Unicode 字符数。"""

    chunk_size: int  # 保存单个片段允许的最大字符数。
    chunk_overlap: int  # 保存相邻片段允许重复的字符数。
    min_chunk_size: int  # 保存短片段合并策略使用的最小长度。
    max_chunks: int  # 保存单篇文章允许生成的最大数量。

    def validate(self) -> None:
        """检查切分配置，防止窗口无法前进或无限生成片段。"""

        if self.chunk_size <= 0:
            raise ChunkingError("chunk_size 必须大于 0")
        if self.chunk_overlap < 0:
            raise ChunkingError("chunk_overlap 不能小于 0")
        if self.chunk_overlap >= self.chunk_size:
            raise ChunkingError("chunk_overlap 必须小于 chunk_size")
        if self.min_chunk_size <= 0:
            raise ChunkingError("min_chunk_size 必须大于 0")
        if self.min_chunk_size > self.chunk_size:
            raise ChunkingError("min_chunk_size 不能大于 chunk_size")
        if self.max_chunks <= 0:
            raise ChunkingError("max_chunks 必须大于 0")


def default_chunk_config() -> ChunkConfig:
    """读取并校验 Django settings 中的阶段 4 配置。"""

    config = ChunkConfig(
        chunk_size=settings.RAG_CHUNK_SIZE,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP,
        min_chunk_size=settings.RAG_MIN_CHUNK_SIZE,
        max_chunks=settings.RAG_MAX_CHUNKS,
    )
    config.validate()
    return config


@dataclass(frozen=True)
class MarkdownBlock:
    """一个标题、段落、列表、引用、表格或代码块。"""

    content: str  # 保存结构块正文。
    section: str  # 保存结构块所属标题。
    is_code_block: bool = False  # 标记结构块是否为代码块。


def is_heading(line: str) -> bool:
    """判断一行是否为 1 至 6 级 ATX 标题。"""

    stripped = line.strip()
    count = len(stripped) - len(stripped.lstrip("#"))
    if count < 1 or count > 6:
        return False
    return len(stripped) == count or stripped[count:count + 1].isspace()


def parse_markdown_blocks(markdown_text: str) -> list[MarkdownBlock]:
    """按标题、空行和 fenced code block 解析稳定结构块。"""

    if not isinstance(markdown_text, str):
        raise ChunkingError("cleaned_markdown 必须是字符串")

    text = markdown_text.replace("\r\n", "\n").replace("\r", "\n")
    blocks: list[MarkdownBlock] = []
    current: list[str] = []
    section = ""
    in_code = False
    fence = ""

    def flush(*, code: bool = False) -> None:
        """把当前缓冲行提交为一个非空结构块。"""

        value = "\n".join(current).strip()
        if value:
            blocks.append(MarkdownBlock(value, section, code))
        current.clear()

    for line in text.split("\n"):
        stripped = line.strip()

        if in_code:
            current.append(line)
            if stripped.startswith(fence):
                flush(code=True)
                in_code = False
                fence = ""
            continue

        if stripped.startswith("```") or stripped.startswith("~~~"):
            flush()
            in_code = True
            fence = stripped[:3]
            current.append(line)
            continue

        if is_heading(line):
            flush()
            section = stripped.lstrip("#").strip()
            blocks.append(MarkdownBlock(stripped, section))
            continue

        if not stripped:
            flush()
            continue

        current.append(line)

    # 未闭合代码围栏也要保留，避免静默丢失正文。
    flush(code=in_code)
    return blocks


def split_oversized_block(
    block: MarkdownBlock,
    config: ChunkConfig,
) -> list[tuple[str, str]]:
    """确定性拆分超长结构块，保证每段不超过 chunk_size。"""

    content = block.content
    if len(content) <= config.chunk_size:
        return [(content, block.section)]

    pieces: list[tuple[str, str]] = []
    step = config.chunk_size - config.chunk_overlap
    start = 0

    while start < len(content):
        end = min(start + config.chunk_size, len(content))
        value = content[start:end].strip()
        if value:
            pieces.append((value, block.section))
        if end >= len(content):
            break
        start += step

    return pieces


def take_overlap(content: str, config: ChunkConfig) -> str:
    """取上一片段末尾的 overlap，且不制造空内容。"""

    if config.chunk_overlap == 0:
        return ""
    return content[-config.chunk_overlap:].strip()


class MarkdownTextChunker:
    """结构优先、长度兜底的确定性 Markdown 切分器。"""

    def __init__(self, *, config: ChunkConfig | None = None):
        self.config = config or default_chunk_config()
        self.config.validate()

    def _append_chunk(
        self,
        output: list[tuple[str, str]],
        content: str,
        section: str,
    ) -> None:
        """统一检查并追加一个候选片段。"""

        value = content.strip()
        if not value:
            return
        if len(value) > self.config.chunk_size:
            raise ChunkingError("切分器生成了超过 chunk_size 的片段")
        output.append((value, section))
        if len(output) > self.config.max_chunks:
            raise ChunkingError("片段数量超过 RAG_MAX_CHUNKS")

    def _pack_blocks(
        self,
        blocks: Iterable[MarkdownBlock],
    ) -> list[tuple[str, str]]:
        """组合结构块，并在 overlap 会超长时安全换片段。"""

        output: list[tuple[str, str]] = []
        current = ""
        current_section = ""

        for block in blocks:
            if len(block.content) > self.config.chunk_size:
                if current:
                    self._append_chunk(output, current, current_section)
                    current = ""
                    current_section = ""
                for piece, section in split_oversized_block(block, self.config):
                    self._append_chunk(output, piece, section)
                continue

            if not current:
                current = block.content
                current_section = block.section
                continue

            candidate = f"{current}\n\n{block.content}"
            if len(candidate) <= self.config.chunk_size:
                current = candidate
                if block.section:
                    current_section = block.section
                continue

            self._append_chunk(output, current, current_section)
            previous_section = current_section
            overlap = take_overlap(current, self.config)

            if block.section and block.section != previous_section:
                overlap = ""

            candidate = f"{overlap}\n\n{block.content}" if overlap else block.content
            if len(candidate) <= self.config.chunk_size:
                current = candidate
                current_section = block.section or previous_section
                continue

            # overlap 会超长时，丢弃 overlap 但保留完整的新结构块。
            current = block.content
            current_section = block.section

        if current:
            self._append_chunk(output, current, current_section)
        return output

    def split(self, document: CleanedDocument) -> list[TextChunk]:
        """把 CleanedDocument 转换为带显式契约字段的 TextChunk 列表。"""

        if not isinstance(document, CleanedDocument):
            raise ChunkingError("输入必须是 CleanedDocument")
        if not document.cleaned_markdown.strip():
            raise ChunkingError("清洗后的 Markdown 不能为空")

        blocks = parse_markdown_blocks(document.cleaned_markdown)
        raw_chunks = self._pack_blocks(blocks)
        if not raw_chunks:
            raise ChunkingError("切分后没有有效片段")

        source_metadata = dict(document.metadata or {})
        version = source_metadata.get("version")
        if version is None:
            version = source_metadata.get("article_version")

        result: list[TextChunk] = []
        for content, section in raw_chunks:
            metadata = dict(source_metadata)
            metadata["section"] = section
            result.append(
                TextChunk(
                    chunk_index=len(result),
                    content=content,
                    content_length=len(content),
                    content_hash=document.content_hash,
                    version=version,
                    section=section,
                    metadata=metadata,
                )
            )

        if any(
            chunk.content_length > self.config.chunk_size
            for chunk in result
        ):
            raise ChunkingError("输出片段超过 chunk_size")
        return result
