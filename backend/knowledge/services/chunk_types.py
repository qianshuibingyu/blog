from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class TextChunk:
    """阶段4的内存片段，不是数据库模型"""
    chunk_index: int
    content: str
    content_length: int
    content_hash: str
    version: str | int | None
    section: str
    metadata: dict[str, Any] = field(default_factory=dict)