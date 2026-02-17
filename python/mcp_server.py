"""pdf2docx MCP Server.

A Model Context Protocol server that converts PDF documents to editable DOCX format.
"""

from mcp.server.fastmcp import FastMCP
from pdf2docx import Converter
import os

mcp = FastMCP(
    name="pdf2docx",
    instructions="Convert PDF documents to editable DOCX format. Supports partial page conversion and encrypted PDFs with password."
)


@mcp.tool()
def convert(pdf_path: str, output_path: str = None, pages: str = None, password: str = None) -> dict:
    """Convert PDF file to DOCX format.

    Args:
        pdf_path: Absolute path to the input PDF file
        output_path: Absolute path for the output DOCX file. If not provided, uses the same directory as pdf_path with .docx extension
        pages: Optional comma-separated page numbers to convert (0-indexed). Example: "0,1,2" or "0-5"
        password: Optional password for encrypted PDFs

    Returns:
        dict: Conversion result with success status, output path, and file size

    Raises:
        FileNotFoundError: If the input PDF file doesn't exist
        ValueError: If the PDF is encrypted and no password is provided
    """
    # Validate input file exists
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Generate default output path if not provided
    if output_path is None:
        base_name = os.path.splitext(pdf_path)[0]
        output_path = f"{base_name}.docx"

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # Parse page numbers if provided
    pages_list = None
    if pages:
        # Handle both "0,1,2" and "0-5" formats
        if "-" in pages:
            start, end = pages.split("-")
            pages_list = list(range(int(start), int(end) + 1))
        else:
            pages_list = [int(p.strip()) for p in pages.split(",")]

    # Perform conversion
    cv = Converter(pdf_path)

    if pages_list:
        cv.convert(output_path, pages=pages_list)
    else:
        cv.convert(output_path)

    cv.close()

    # Get output file size
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)

    return {
        "success": True,
        "input_path": pdf_path,
        "output_path": output_path,
        "size_mb": round(file_size_mb, 2),
        "pages": pages_list if pages_list else "all"
    }


@mcp.tool()
def get_info(pdf_path: str) -> dict:
    """Get metadata information about a PDF file.

    Args:
        pdf_path: Absolute path to the PDF file

    Returns:
        dict: PDF metadata including page count, file size, and whether it's encrypted

    Raises:
        FileNotFoundError: If the PDF file doesn't exist
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)

    # Open PDF to get page count
    import fitz  # PyMuPDF
    doc = fitz.open(pdf_path)
    page_count = doc.page_count
    is_encrypted = doc.needs_password
    metadata = doc.metadata
    doc.close()

    return {
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
        }
    }


if __name__ == "__main__":
    mcp.run()
