# 更新日志

所有重要的变更都将记录在此文件中。

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

## [未发布]

### 新增
- 初始化项目结构，使用 Poetry 管理依赖
- 完成 5 个核心工具的开发：
  - `list_files` - 文件列表工具
  - `find_duplicates` - 重复文件检测工具
  - `batch_rename` - 批量重命名工具
  - `text_replace` - 文本批量替换工具
  - `file_organizer` - 文件自动整理工具
- 集成 Logfire 监控系统
- 添加完整的单元测试，覆盖率达到 70%+
- 配置 GitHub Actions CI/CD
- 添加 pre-commit 钩子确保代码质量
- 编写项目文档和 README

### 技术栈
- Python 3.13.3+
- Pydantic 2.11.5+
- Logfire 3.16.0+
- Click 8.1+ (CLI框架)
- pytest 8.0+ (测试框架)

## [0.1.0] - 即将发布

第一个正式版本，包含 5 个实用工具。
