#!/usr/bin/env python3
"""
pdf2docx MCP 服务器
用于将 PDF 文件转换为可编辑 DOCX 格式的 MCP 工具服务
"""

import asyncio
import logging
import os
import re
import sys
import threading
import time
from typing import Optional

# 将当前目录加入模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server import FastMCP
from mcp.server.fastmcp import Context
from pdf2docx import Converter
import fitz  # PyMuPDF

# 创建 MCP 服务器实例
mcp = FastMCP(
    name="pdf2docx",
    instructions="Convert PDF documents to editable DOCX format. Supports partial page conversion and encrypted PDFs with password.",
)

# pdf2docx logs "(N/Total) Page X" at INFO level (root logger, not a named logger)
# Matches patterns like "(1/10) Page 1" or "(3/5)..."
_PAGE_LOG_RE = re.compile(r"\((\d+)/(\d+)\)")


class _ProgressLogHandler(logging.Handler):
    """Intercepts pdf2docx page-level log messages to emit MCP progress notifications.

    pdf2docx processes each page twice: once during parsing (phase 3/4) and once
    during docx creation (phase 4/4). We use a monotonic tick counter with
    total = 2 * pages_to_convert so progress flows 0% → 50% → 100%.
    """

    def __init__(
        self, ctx: Context, pages_to_convert: int, loop: asyncio.AbstractEventLoop
    ) -> None:
        super().__init__()
        self.ctx = ctx
        # Two phases per page; multiply so each log tick advances the bar evenly
        self.total = pages_to_convert * 2
        self.loop = loop
        self._ticks = 0
        # Set by bind_thread() from inside the worker thread so that concurrent
        # conversions do not cross-contaminate each other's progress counts.
        self._thread_id: Optional[int] = None

    def bind_thread(self) -> None:
        """Record the current thread's ID. Call this from the conversion thread."""
        self._thread_id = threading.current_thread().ident

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Drop records until bind_thread() has run, and always drop records
            # from threads other than the bound conversion thread.  This prevents
            # concurrent conversions from cross-contaminating each other's counts.
            if self._thread_id is None or record.thread != self._thread_id:
                return
            msg = self.format(record)
            if _PAGE_LOG_RE.search(msg):
                self._ticks = min(self._ticks + 1, self.total)
                asyncio.run_coroutine_threadsafe(
                    self.ctx.report_progress(self._ticks, self.total),
                    self.loop,
                )
        except Exception:
            self.handleError(record)


@mcp.tool()
async def convert(
    pdf_path: str,
    output_path: Optional[str] = None,
    pages: Optional[str] = None,
    password: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> dict:
    """
    Convert PDF file to DOCX format

    Args:
        pdf_path: Absolute path to the input PDF file
        output_path: Absolute path for the output DOCX file. If not provided, uses the same directory as pdf_path with .docx extension
        pages: Optional page numbers to convert (0-indexed). Formats: "0,1,2" or "0-5"
        password: Optional password for encrypted PDFs

    Returns:
        Dictionary containing:
        - success: Boolean indicating if the conversion was successful
        - input_path: Path to the input PDF file
        - output_path: Path to the output DOCX file
        - size_mb: Size of the output file in MB
        - pages: Pages that were converted
        - total_pages: Total number of pages in the PDF
        - pages_converted: Number of pages actually converted
        - duration_seconds: Time taken for conversion
    """
    try:
        if not os.path.exists(pdf_path):
            return {
                "success": False,
                "input_path": pdf_path,
                "message": f"PDF file not found: {pdf_path}",
            }

        if output_path is None:
            base_name = os.path.splitext(pdf_path)[0]
            output_path = f"{base_name}.docx"

        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        pages_list = None
        if pages:
            if "-" in pages:
                start, end = pages.split("-")
                pages_list = list(range(int(start), int(end) + 1))
            else:
                pages_list = [int(p.strip()) for p in pages.split(",")]

        # Get total page count before conversion for progress reporting.
        # Authenticate if the PDF is encrypted so page_count is accurate.
        with fitz.open(pdf_path) as doc:
            if password and doc.needs_pass:
                if not doc.authenticate(password):
                    return {
                        "success": False,
                        "input_path": pdf_path,
                        "message": "Invalid password for encrypted PDF",
                    }
            total_pages = doc.page_count

        pages_to_convert = len(pages_list) if pages_list else total_pages
        # pdf2docx runs two phases (parse + create), each logging N messages.
        # Use 2*N as the consistent total throughout all report_progress calls.
        progress_total = pages_to_convert * 2

        # Report initial progress (0%)
        if ctx:
            await ctx.report_progress(0, progress_total)

        # Attach a logging handler to the ROOT logger to intercept pdf2docx
        # per-page log messages (pdf2docx calls logging.info() directly).
        handler: Optional[_ProgressLogHandler] = None
        if ctx:
            loop = asyncio.get_running_loop()
            handler = _ProgressLogHandler(ctx, pages_to_convert, loop)
            handler.setLevel(logging.DEBUG)
            logging.getLogger().addHandler(handler)

        start_time = time.monotonic()
        try:
            # Run blocking conversion in a thread to avoid stalling the event loop.
            def _run_conversion() -> None:
                # Bind this thread so the handler ignores other concurrent jobs.
                if handler:
                    handler.bind_thread()
                cv = Converter(pdf_path, password=password)
                try:
                    if pages_list:
                        cv.convert(output_path, pages=pages_list)
                    else:
                        cv.convert(output_path)
                finally:
                    cv.close()

            await asyncio.to_thread(_run_conversion)
        finally:
            if handler:
                logging.getLogger().removeHandler(handler)

        duration = round(time.monotonic() - start_time, 1)

        # Report completion (100%) using the same total as the handler
        if ctx:
            await ctx.report_progress(progress_total, progress_total)

        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)

        return {
            "success": True,
            "input_path": pdf_path,
            "output_path": output_path,
            "size_mb": round(file_size_mb, 2),
            "pages": pages_list if pages_list else "all",
            "total_pages": total_pages,
            "pages_converted": pages_to_convert,
            "duration_seconds": duration,
            "message": (
                f"Successfully converted {pages_to_convert} page(s) to {output_path} "
                f"in {duration}s"
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "input_path": pdf_path,
            "output_path": output_path,
            "error": str(e),
            "message": f"Error converting PDF: {str(e)}",
        }


@mcp.tool()
def get_info(pdf_path: str) -> dict:
    """
    Get metadata information about a PDF file

    Args:
        pdf_path: Absolute path to the PDF file

    Returns:
        Dictionary containing:
        - success: Boolean indicating if the query was successful
        - path: Path to the PDF file
        - page_count: Number of pages in the PDF
        - size_mb: Size of the PDF file in MB
        - is_encrypted: Whether the PDF is encrypted
        - metadata: PDF metadata (title, author, subject, creator, producer)
    """
    try:
        if not os.path.exists(pdf_path):
            return {
                "success": False,
                "path": pdf_path,
                "message": f"PDF file not found: {pdf_path}",
            }

        file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)

        with fitz.open(pdf_path) as doc:
            page_count = doc.page_count
            is_encrypted = doc.needs_pass
            metadata = doc.metadata

        return {
            "success": True,
            "path": pdf_path,
            "page_count": page_count,
            "size_mb": round(file_size_mb, 2),
            "is_encrypted": is_encrypted,
            "metadata": {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
            },
            "message": f"Found PDF with {page_count} page(s)",
        }

    except Exception as e:
        return {
            "success": False,
            "path": pdf_path,
            "error": str(e),
            "message": f"Error reading PDF info: {str(e)}",
        }


if __name__ == "__main__":
    # 以 stdio 方式运行服务器
    mcp.run()
