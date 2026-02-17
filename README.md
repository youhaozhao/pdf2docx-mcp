# pdf2docx-mcp

[![npm version](https://img.shields.io/npm/v/@youhaozhao/pdf2docx-mcp)](https://www.npmjs.com/package/@youhaozhao/pdf2docx-mcp)

通过 MCP 协议将 PDF 文件转换为可编辑 DOCX 格式的工具，适用于 Claude Desktop。

## 使用方法

在 Claude Desktop / Claude Code 配置文件中添加：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "pdf2docx": {
      "command": "npx",
      "args": ["-y", "@youhaozhao/pdf2docx-mcp"]
    }
  }
}
```

重启 Claude Desktop 后即可使用。

## 可用工具

- **`convert`** — 将 PDF 转换为 DOCX，参数：PDF 路径（必填）、输出路径（可选）、页码范围（可选）、密码（可选）
- **`get_info`** — 获取 PDF 元信息，参数：PDF 路径（必填）

示例对话：

```
把 /Users/me/report.pdf 转换成 DOCX
获取 /Users/me/report.pdf 的页数和元信息
```

## 系统要求

- Node.js 18+
- Python 3.10+（Python 依赖会自动安装）

## Credits

基于 [dothinking/pdf2docx](https://github.com/dothinking/pdf2docx) 构建。
