# 更新日志

所有重要的变更都将记录在此文件中。

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

## [0.3.0] - 2025-06-18

第三阶段发布：智能化能力增强完成。

### 新增
- **AI 智能功能集成**：
  - 集成 DeepSeek API，提供智能分析能力
  - 智能文件分类器：基于文件内容自动分类
  - 文档自动摘要生成：支持 txt、md、pdf、docx 等格式
  - 智能文本分析：为文本替换提供风险提示和智能建议
  - 重复文件版本识别：智能识别同一文件的不同版本
- **新增 summarize 命令**：
  - `tools summarize FILE/PATH` - 生成文档摘要
  - 支持批量摘要处理
  - 多格式输出支持（JSON、纯文本）
- **AI 增强的现有工具**：
  - `tools organize --ai-classify` - 智能文件分类
  - `tools replace --ai-check` - 智能替换风险检测
  - `tools duplicates --ai-analyze` - 智能版本分析

### 增强
- **第二阶段功能完善**：
  - 现代化错误处理系统：友好的错误提示和恢复建议
  - 智能交互系统：增强的用户确认对话
  - 性能优化系统：针对大文件的优化处理
  - 进度显示：大批量操作显示进度条
  - 多格式输出：支持 JSON、CSV 输出格式
  - 操作历史记录：`tools history` 查看操作历史
- **配置管理增强**：
  - 支持 `.simple-tools.yml` 配置文件
  - AI 功能开关和参数配置
  - 环境变量支持

### 技术改进
- 添加异步支持：httpx 用于 AI API 调用
- 新增文档处理依赖：python-docx、pypdf
- 充分利用 Python 3.13.3 和 Pydantic v2 新特性
- 测试覆盖率提升至 87.8%

### 配置要求
- 需要设置 `DEEPSEEK_API_KEY` 环境变量以使用 AI 功能
- AI 功能默认关闭，需在配置中启用

## [0.2.0] - 2025-06-02

第二阶段发布：功能完善优化。

### 新增
- 进度显示系统：大批量操作显示进度条
- 多格式输出支持：JSON、CSV、纯文本格式
- 配置文件支持：`.simple-tools.yml` 配置管理
- 现代化错误处理：友好的错误提示和恢复建议
- 智能交互系统：增强的用户确认对话
- 性能优化系统：针对大文件优化
- 操作历史记录：`tools history` 命令

### 改进
- 错误信息更友好，提供明确的解决建议
- 批量操作不因单个错误中断
- 大文件处理性能优化
- 用户交互体验显著提升

### 技术栈更新
- 添加 PyYAML 6.0+ 用于配置文件
- 完善类型提示和错误处理
- 测试覆盖率维持在 85%+

## [0.1.0] - 2025-05-28

首个正式版本，已发布到 [PyPI](https://pypi.org/project/sumu-simple-tools/)。

### 新增
- 初始化项目结构，使用 Poetry 管理依赖
- 完成 5 个核心工具的开发：
  - `list_files` - 文件列表工具
  - `find_duplicates` - 重复文件检测工具
  - `batch_rename` - 批量重命名工具
  - `text_replace` - 文本批量替换工具
  - `file_organizer` - 文件自动整理工具
- 集成 Logfire 监控系统
- 添加完整的单元测试，覆盖率达到 85%+
- 配置 GitHub Actions CI/CD
- 添加 pre-commit 钩子确保代码质量
- 编写项目文档和 README

### 技术栈
- Python 3.13.3+
- Pydantic 2.11.5+
- Logfire 3.16.0+
- Click 8.2.1+ (CLI框架)
- pytest 8.3.5+ (测试框架)
- 代码质量工具：black, isort, ruff, mypy

### CLI 命令
- `tools list PATH` - 列出目录文件
- `tools duplicates PATH` - 查找重复文件
- `tools rename PATTERN` - 批量重命名文件
- `tools replace PATTERN` - 批量替换文本
- `tools organize PATH` - 自动整理文件
