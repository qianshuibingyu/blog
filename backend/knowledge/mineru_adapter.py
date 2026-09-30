"""MinerU 轻量级 API 适配器：只负责将原始文件转换为 ParsedDocument。"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .document_types import ParsedDocument, SourceBlock


_SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx", ".ppt", ".pptx"}
_DEFAULT_ENDPOINT = "https://mineru.net/api/v4"
_PARSER_VERSION = "mineru-api-v4"


class MineruAdapterError(RuntimeError):
    """MinerU 适配器的基础异常。"""


class MineruDependencyError(MineruAdapterError):
    """运行时缺少 MinerU API 所需的 HTTP 依赖。"""


def _load_http_client() -> Any:
    """延迟导入 HTTP 客户端，避免项目启动时强制依赖 requests。"""
    try:
        import requests
    except ImportError as exc:
        raise MineruDependencyError(
            "MinerU 适配器依赖 requests，请先安装 requests 后再调用解析。"
        ) from exc
    return requests


def _request_json(client: Any, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    """调用 MinerU 接口并统一处理 HTTP/API 错误，不记录响应正文。"""
    try:
        response = client.request(method, url, **kwargs)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise MineruAdapterError(f"MinerU API 请求失败：{method} {url}（{type(exc).__name__}）") from exc
    if not isinstance(payload, dict):
        raise MineruAdapterError("MinerU API 返回格式无效：顶层结果不是对象。")
    if payload.get("code") not in (None, 0):
        raise MineruAdapterError(f"MinerU API 返回错误（错误码：{payload.get('code')}）。")
    return payload


def _markdown_blocks(markdown: str) -> list[SourceBlock]:
    """将 MinerU Markdown 的标题、代码、表格和段落映射为统一区块。"""
    blocks: list[SourceBlock] = []
    offset = 0
    for raw_line in markdown.splitlines(keepends=True):
        text = raw_line.strip()
        start = offset
        offset += len(raw_line)
        if not text:
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", text)
        if heading:
            blocks.append(SourceBlock("heading", heading.group(2).strip(), len(heading.group(1)), start, offset))
        elif text.startswith("```"):
            blocks.append(SourceBlock("code", text, metadata={"source_offset": start}))
        elif text.startswith("|"):
            blocks.append(SourceBlock("table", text, source_start=start, source_end=offset))
        else:
            blocks.append(SourceBlock("paragraph", text, source_start=start, source_end=offset))
    return blocks


def _extract_markdown(result: dict[str, Any]) -> str:
    """从任务结果中提取 Markdown 文本，拒绝空结果而不伪造内容。"""
    data = result.get("data") or result.get("result") or result
    if isinstance(data, dict):
        for key in ("markdown", "md", "content"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value
        url = data.get("full_zip_url") or data.get("zip_url") or data.get("result_url")
        if isinstance(url, str) and url:
            client = _load_http_client()
            try:
                response = client.get(url, timeout=120)
                response.raise_for_status()
                import zipfile
                from io import BytesIO
                with zipfile.ZipFile(BytesIO(response.content)) as archive:
                    names = [name for name in archive.namelist() if name.lower().endswith(".md")]
                    if names:
                        return archive.read(names[0]).decode("utf-8")
            except Exception as exc:
                raise MineruAdapterError("MinerU 结果下载或读取失败。") from exc
    raise MineruAdapterError("MinerU 解析结果为空：未找到 Markdown 内容。")


def _parse_with_local_mineru(source_path: Path) -> str:
    """调用已安装的 MinerU 4 CLI 轻量解析模型并读取生成的 Markdown。"""
    executable = shutil.which("mineru")
    if not executable:
        raise MineruDependencyError("未找到 MinerU CLI，请先安装官方 mineru>=4.0。")
    with tempfile.TemporaryDirectory(prefix="mineru-") as output_dir:
        try:
            completed = subprocess.run(
                [executable, "parse", str(source_path), "--pages", "all", "-o", output_dir],
                capture_output=True, text=True, timeout=int(os.getenv("MINERU_TIMEOUT_SECONDS", "600")),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise MineruAdapterError("MinerU 本地解析超时。") from exc
        if completed.returncode != 0:
            raise MineruAdapterError(f"MinerU 本地解析失败（退出码：{completed.returncode}）。")
        markdown_files = list(Path(output_dir).rglob("*.md"))
        if not markdown_files:
            raise MineruAdapterError("MinerU 解析结果为空：未生成 Markdown 文件。")
        markdown = markdown_files[0].read_text(encoding="utf-8")
        if not markdown.strip():
            raise MineruAdapterError("MinerU 解析结果为空：Markdown 内容为空。")
        return markdown


def parse_with_mineru(*, source_path: Path, source_name: str) -> ParsedDocument:
    """调用本地 MinerU 轻量模型，将原始文件转换为 ParsedDocument。"""
    # 先校验输入，避免无效文件触发解析。
    if not source_path.exists() or not source_path.is_file():
        raise FileNotFoundError(f"待解析文件不存在：{source_path}")
    extension = source_path.suffix.lower()
    if extension not in _SUPPORTED_EXTENSIONS:
        raise ValueError(f"MinerU 不支持该文件扩展名：{extension or '无扩展名'}")

    # 优先使用本地 MinerU 轻量模型，不需要 API Key 或远程服务。
    markdown = _parse_with_local_mineru(source_path)
    return ParsedDocument("mineru", markdown, _markdown_blocks(markdown), source_name or source_path.name,
                          "mineru-local-cli", {"mode": "local"})

    # 保留以下远程 API 分支作为显式配置时的兼容路径；默认不会触发。
    api_key = os.getenv("MINERU_API_KEY") or os.getenv("MINERU_TOKEN")
    if not api_key:
        raise MineruDependencyError("未配置 MinerU API Key，请设置 MINERU_API_KEY。")
    client = _load_http_client()
    endpoint = os.getenv("MINERU_API_ENDPOINT", _DEFAULT_ENDPOINT).rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}"}

    # 按 MinerU v4 轻量级接口创建批量上传任务，并上传本地文件。
    with source_path.open("rb") as file_handle:
        payload = _request_json(client, "POST", f"{endpoint}/file-urls/batch", headers=headers,
                                 json={"files": [{"name": source_name or source_path.name}]}, timeout=30)
        data = payload.get("data") or {}
        urls = data.get("file_urls") or data.get("upload_urls") or []
        task_id = data.get("batch_id") or data.get("task_id")
        if not urls:
            raise MineruAdapterError("MinerU 未返回文件上传地址。")
        upload = client.put(urls[0], data=file_handle, headers={"Content-Type": "application/octet-stream"}, timeout=300)
        upload.raise_for_status()

    # 轮询任务状态，避免把提交成功误报为解析成功。
    if not task_id:
        raise MineruAdapterError("MinerU 未返回任务 ID。")
    deadline = time.monotonic() + float(os.getenv("MINERU_TIMEOUT_SECONDS", "600"))
    while time.monotonic() < deadline:
        result = _request_json(client, "GET", f"{endpoint}/extract/task/{task_id}", headers=headers, timeout=30)
        state = str((result.get("data") or result).get("state", "")).lower()
        if state in {"done", "success", "succeeded", "completed"}:
            markdown = _extract_markdown(result)
            return ParsedDocument("mineru", markdown, _markdown_blocks(markdown), source_name or source_path.name,
                                  _PARSER_VERSION, {"endpoint": endpoint, "task_id": task_id})
        if state in {"failed", "error", "cancelled", "canceled"}:
            raise MineruAdapterError(f"MinerU 解析失败（状态：{state}）。")
        time.sleep(2)
    raise MineruAdapterError("MinerU 解析超时：任务在限定时间内未完成。")
