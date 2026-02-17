# pdf2docx MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that converts PDF documents to editable DOCX format.

## Installation

```bash
npm install -g @youhaozhao/pdf2docx-mcp
```

## Usage

### As an MCP Server

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "pdf2docx": {
      "command": "pdf2docx-mcp"
    }
  }
}
```

Or with npx:

```json
{
  "mcpServers": {
    "pdf2docx": {
      "command": "npx",
      "args": ["@youhaozhao/pdf2docx-mcp"]
    }
  }
}
```

### Available Tools

#### `convert`

Convert a PDF file to DOCX format.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pdf_path` | string | Yes | Absolute path to input PDF |
| `output_path` | string | No | Output path (default: same as input with .docx) |
| `pages` | string | No | Pages to convert: "0,1,2" or "0-5" |
| `password` | string | No | Password for encrypted PDFs |

**Returns:** Conversion result with output path and file size

#### `get_info`

Get metadata about a PDF file.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pdf_path` | string | Yes | Absolute path to PDF |

**Returns:** Page count, file size, encryption status, and metadata

## Requirements

- Node.js >= 18.0.0
- Python >= 3.10

Python dependencies are automatically installed during `npm install`.

## License

MIT
