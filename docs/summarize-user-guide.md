# 文档摘要功能使用指南

## 快速开始

### 1. 配置AI功能

```bash
# 设置环境变量
export SIMPLE_TOOLS_AI_ENABLED=true
export DEEPSEEK_API_KEY="your-actual-api-key-here"
```

或创建配置文件 `~/.simple-tools.yml`:
```yaml
ai:
  enabled: true
  api_key: "your-actual-api-key-here"
  # 可选配置
  daily_limit: 10.0     # 每日费用限额（元）
  monthly_limit: 300.0  # 每月费用限额（元）
```

### 2. 基本使用

```bash
# 查看帮助
tools summarize --help

# 生成单个文档的摘要
tools summarize document.pdf

# 批量处理目录中的所有文档
tools summarize ~/Documents --batch

# 指定摘要长度（默认200字）
tools summarize report.docx --length 300

# 保存摘要结果
tools summarize ~/Documents --batch -o summaries.json
tools summarize ~/Documents --batch -o summaries.md --format markdown
```

## 支持的文档格式

- 📄 纯文本: `.txt`
- 📝 Markdown: `.md`
- 📑 reStructuredText: `.rst`
- 📕 PDF: `.pdf`
- 📘 Word: `.docx`, `.doc`

## 高级功能

### 批量处理

批量模式会自动扫描目录中所有支持的文档：

```bash
# 批量生成摘要并显示进度
tools summarize ~/Documents --batch

# 保存为JSON格式（便于程序处理）
tools summarize ~/Documents --batch -o result.json

# 保存为Markdown格式（便于阅读）
tools summarize ~/Documents --batch -o result.md --format markdown
```

### 缓存机制

- 相同文档的摘要会自动缓存，避免重复API调用
- 使用 `--no-cache` 强制重新生成摘要

```bash
# 强制重新生成，不使用缓存
tools summarize document.pdf --no-cache
```

### 成本控制

系统内置成本控制机制：
- 每日限额：10元（可配置）
- 每月限额：300元（可配置）
- 超过限额会自动停止

查看当前使用情况：
```bash
# 查看AI使用统计（功能开发中）
tools ai-stats
```

## 示例输出

### 命令行输出
```
正在生成文档摘要: project_report.md

📄 project_report.md
  文档类型: markdown
  原文字数: 1523
  摘要字数: 198

摘要:
本报告总结了2025年第一季度简单工具集项目的开发进展。项目成功完成了基础工具开发、
功能优化和智能化增强三个阶段的主要任务。已开发5个核心工具，实现了智能错误处理、
进度显示等功能增强，并集成了DeepSeek API提供AI能力。项目坚持"简单实用"理念，
避免过度设计，专注解决实际问题。
```

### JSON输出格式
```json
[
  {
    "file": "/path/to/document.pdf",
    "summary": "这是文档的摘要内容...",
    "word_count": 1500,
    "doc_type": "pdf"
  }
]
```

### Markdown输出格式
```markdown
# 文档摘要汇总

生成时间：2025-06-14 10:30:00

## 📄 project_report.md

- 文档类型：markdown
- 原文字数：1523
- 摘要字数：198

**摘要：**
本报告总结了项目进展...

---
```

## 故障排除

### 常见问题

1. **"AI功能未启用"错误**
   - 确保设置了 `SIMPLE_TOOLS_AI_ENABLED=true`
   - 检查配置文件是否正确

2. **"API密钥未配置"错误**
   - 设置 `DEEPSEEK_API_KEY` 环境变量
   - 或在配置文件中设置 `api_key`

3. **"不支持的文档格式"错误**
   - 检查文件扩展名是否在支持列表中
   - 确保文件不是损坏的

4. **摘要生成失败**
   - 检查网络连接
   - 确认API密钥有效
   - 查看是否超过使用限额

### 调试模式

使用 `-v` 启用详细日志：
```bash
tools -v summarize document.pdf
```

## 最佳实践

1. **批量处理大量文档时**
   - 使用批量模式而不是循环调用单个文件
   - 考虑分批处理避免超时

2. **处理敏感文档**
   - 注意文档内容会发送到AI服务
   - 考虑在本地部署模型（未来功能）

3. **优化成本**
   - 利用缓存机制避免重复生成
   - 合理设置摘要长度
   - 定期检查使用统计

## 与其他工具配合

```bash
# 1. 先整理文件，再批量生成摘要
tools organize ~/Downloads --mode type
tools summarize ~/Downloads/文档 --batch -o doc_summaries.md

# 2. 查找重复文件后生成摘要对比
tools duplicates ~/Documents
tools summarize duplicate_file1.pdf duplicate_file2.pdf

# 3. 结合文件列表使用
tools list ~/Documents --format json | jq -r '.files[].path' | xargs -I {} tools summarize {}
```

## 开发计划

- [ ] 支持更多文档格式（如 .epub, .html）
- [ ] 添加摘要质量评分
- [ ] 支持自定义摘要模板
- [ ] 集成本地AI模型选项
- [ ] 添加摘要对比功能
