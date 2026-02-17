#!/usr/bin/env python3
"""
pdf2docx MCP 服务器
用于将 PDF 文件转换为可编辑 DOCX 格式的 MCP 工具服务
"""

import os
import sys
from typing import Optional

# 将当前目录加入模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server import FastMCP
from pdf2docx import Converter
import fitz  # PyMuPDF

# 创建 MCP 服务器实例
mcp = FastMCP(
    name="pdf2docx",
    instructions="Convert PDF documents to editable DOCX format. Supports partial page conversion and encrypted PDFs with password.",
)


@mcp.tool()
def convert(pdf_path: str, output_path: Optional[str] = None, pages: Optional[str] = None, password: Optional[str] = None) -> dict:
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

        cv = Converter(pdf_path)
        if pages_list:
            cv.convert(output_path, pages=pages_list)
        else:
            cv.convert(output_path)
        cv.close()

        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)

        return {
            "success": True,
            "input_path": pdf_path,
            "output_path": output_path,
            "size_mb": round(file_size_mb, 2),
            "pages": pages_list if pages_list else "all",
            "message": f"Successfully converted to {output_path}",
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

        doc = fitz.open(pdf_path)
        page_count = doc.page_count
        is_encrypted = doc.needs_password
        metadata = doc.metadata
        doc.close()

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
