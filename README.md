# simple-tools

[![CI](https://github.com/sumu2025/simple-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/sumu2025/simple-tools/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen)](https://github.com/sumu2025/simple-tools)
[![Python](https://img.shields.io/badge/python-3.13+-blue)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/poetry-managed-blueviolet)](https://python-poetry.org/)
[![PyPI](https://img.shields.io/pypi/v/sumu-simple-tools)](https://pypi.org/project/sumu-simple-tools/)

一个简单实用的 Python 工具集，专注解决日常工作中的实际问题。

## 🚀 特性

- **极简主义**：每个工具控制在 100 行代码内
- **实用至上**：解决实际问题，避免花哨功能
- **现代化技术栈**：充分利用 Python 3.13+ 和 Pydantic v2.11.5+ 的最新特性
- **智能交互**：增强的确认对话和风险评估系统
- **错误处理**：友好的错误提示和智能建议生成
- **性能优化**：分块处理、异步操作和高效目录扫描
- **多格式输出**：支持 plain、JSON、CSV 等多种输出格式
- **监控集成**：使用 Logfire 进行深度性能监控
- **高测试覆盖**：核心功能测试覆盖率 85%+

## 📦 安装

### 使用 pip 安装
```bash
pip install sumu-simple-tools
```

> **注意**：由于 PyPI 上 `simple-tools` 名称已被占用，本项目在 PyPI 上的包名为 `sumu-simple-tools`，但安装后命令行工具仍然是 `tools`。

### 从源码安装
```bash
# 克隆项目
git clone https://github.com/sumu2025/simple-tools.git
cd simple-tools

# 使用 Poetry 安装
poetry install

# 或使用 pip
pip install .
```

## 🛠️ 工具列表

### 1. list_files - 智能文件列表工具
智能展示目录内容，支持多种输出格式和详细信息显示。

```bash
# 列出当前目录
tools list

# 列出指定目录，显示隐藏文件
tools list ~/Downloads --all

# 显示详细信息（文件大小、修改时间）
tools list --long

# JSON格式输出
tools list --format json

# CSV格式输出
tools list --format csv > files.csv
```

### 2. find_duplicates - 智能重复文件检测
高效查找重复文件，支持按大小、扩展名过滤，智能风险评估。

```bash
# 扫描当前目录
tools duplicates

# 只扫描大于 1MB 的文件
tools duplicates -s 1048576

# 只检测特定类型文件
tools duplicates -e .jpg -e .png

# 显示删除建议
tools duplicates --show-commands

# JSON格式输出
tools duplicates --format json > duplicates.json
```

### 3. batch_rename - 智能批量重命名
支持文本替换和序号添加，带有预览确认和风险评估。

```bash
# 文本替换模式
tools rename \"old:new\"

# 序号模式
tools rename \"photo\" -n

# 只处理特定类型文件
tools rename \"draft:final\" -f \"*.txt\"

# 直接执行（跳过预览）
tools rename \"test:prod\" --execute

# CSV格式输出结果
tools rename \"old:new\" --format csv > rename_results.csv
```

### 4. text_replace - 智能文本批量替换
在文件中查找并替换指定文本内容，支持大文件优化处理。

```bash
# 单文件替换
tools replace \"localhost:127.0.0.1\" -f config.ini

# 批量替换目录下的文件
tools replace \"v2.0:v2.1\" -p docs

# 只处理特定类型文件
tools replace \"TODO:DONE\" -e .txt -e .md

# 跳过确认直接执行
tools replace \"old:new\" -y

# 🆕 执行前自动备份文件（推荐）
tools replace \"old:new\" --backup --execute

# 使用 AI 风险分析
tools replace \"bug:issue\" --ai-check --execute

# JSON格式输出结果
tools replace \"old:new\" --format json > replace_results.json
```

#### 🛡️ 备份和恢复
文本替换支持自动备份功能，保护您的数据安全：

```bash
# 使用 --backup 选项在执行前创建备份
tools replace \"critical:change\" --backup --execute

# 备份位置：~/.simpletools-backup/replace_YYYYMMDD_HHMMSS/
# 查看备份
ls ~/.simpletools-backup/

# 手动恢复文件
cp ~/.simpletools-backup/replace_20250613_103000/file.txt ./file.txt
```

> 💡 **提示**：虽然有备份功能，但最好的保护是使用版本控制系统（如 Git）！

### 5. file_organizer - 智能文件自动整理
根据文件类型或日期自动整理文件，支持自定义规则和批量处理。

```bash
# 按类型整理（默认）
tools organize ~/Downloads

# 按日期整理
tools organize . --mode date

# 混合模式（先类型后日期）
tools organize ~/Desktop --mode mixed

# 递归处理子目录
tools organize . --recursive

# JSON格式输出结果
tools organize . --format json > organize_results.json
```

### 6. history - 操作历史查看
查看最近的操作历史记录。

```bash
# 查看最近10条记录
tools history

# 查看最近20条记录
tools history -n 20
```

## 🔧 第二阶段增强功能

### 🛡️ 现代化错误处理系统
- **智能错误分类**：使用 Python 3.13 的 match/case 语法进行错误模式匹配
- **智能建议生成**：基于错误类型自动生成解决方案
- **批量错误收集**：支持批量操作的错误汇总和友好展示
- **结构化错误信息**：便于 Logfire 分析和监控

### 🧠 智能交互系统
- **增强确认对话**：智能风险评估和操作预览
- **异步支持**：使用 Python 3.13 的现代异步特性
- **智能命令建议**：基于相似度匹配提供命令建议
- **操作历史记录**：自动记录操作历史便于追踪

### ⚡ 性能优化系统
- **分块文件处理**：优化大文件处理，避免内存溢出
- **异步批量操作**：支持高并发文件处理
- **高效目录扫描**：使用生成器减少内存占用
- **性能监控装饰器**：自动性能分析和优化建议

### 📊 多格式输出系统
- **Plain格式**：默认的人类友好格式
- **JSON格式**：结构化数据输出，便于程序集成
- **CSV格式**：表格数据导出，便于数据分析
- **统一接口**：所有工具支持一致的输出格式

### 📈 深度监控集成
- **Logfire深度集成**：实时性能监控和错误追踪
- **操作指标收集**：吞吐量、响应时间、资源使用情况
- **智能性能分析**：自动性能等级评估和优化建议

## 💻 开发

### 环境要求
- Python 3.13+（充分利用最新特性）
- Poetry（依赖管理）
- Logfire（监控，首次运行时配置）

### 本地开发
```bash
# 安装开发依赖
poetry install

# 运行测试
poetry run pytest

# 运行测试并查看覆盖率
poetry run pytest --cov=src/simple_tools

# 安装 pre-commit 钩子
poetry run pre-commit install

# 运行代码质量检查
poetry run pre-commit run --all-files
```

### 项目结构
```
simple-tools/
├── src/
│   └── simple_tools/
│       ├── __init__.py           # Logfire 初始化
│       ├── cli.py               # CLI 入口
│       ├── config.py            # 配置管理
│       ├── _typing.py           # 类型定义
│       ├── core/                # 核心工具模块
│       │   ├── file_tool.py
│       │   ├── duplicate_finder.py
│       │   ├── batch_rename.py
│       │   ├── text_replace.py
│       │   └── file_organizer.py
│       └── utils/               # 第二阶段增强功能
│           ├── errors.py        # 现代化错误处理
│           ├── smart_interactive.py # 智能交互系统
│           ├── performance_optimizer.py # 性能优化
│           ├── formatter.py     # 格式化输出
│           ├── progress.py      # 进度显示
│           └── config_loader.py # 配置加载器
├── tests/                       # 单元测试
├── docs/                        # 项目文档
└── pyproject.toml              # 项目配置
```

## 🧪 测试

项目使用 pytest 进行测试，核心功能测试覆盖率达到 85% 以上。

```bash
# 运行所有测试
poetry run pytest

# 运行特定测试文件
poetry run pytest tests/test_file_tool.py

# 生成 HTML 覆盖率报告
poetry run pytest --cov-report=html
open htmlcov/index.html

# 运行第二阶段功能测试
poetry run pytest tests/test_errors.py
poetry run pytest tests/test_smart_interactive.py
poetry run pytest tests/test_performance_optimizer.py
```

## 📊 监控

项目集成了 Logfire 深度监控系统，提供实时性能分析：

1. **首次运行配置**：运行任意命令时，Logfire 会自动引导配置
2. **性能监控**：自动收集操作指标、响应时间、资源使用情况
3. **错误追踪**：结构化的错误信息和智能建议生成
4. **控制台访问**：访问 Logfire 控制台查看详细监控数据

## 🔧 配置

支持通过 `.simple-tools.yml` 配置文件自定义行为：

```yaml
# .simple-tools.yml
tools:
  # 全局配置
  format: json
  verbose: true

  # 各工具配置
  list:
    show_all: true
    long: true

  duplicates:
    recursive: true
    min_size: 1048576  # 1MB

  rename:
    dry_run: true

  replace:
    extensions: [.txt, .md, .rst]

  organize:
    mode: type
    recursive: false
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发原则
- 保持简单，拒绝过度设计
- 每个工具独立，避免复杂依赖
- 充分利用 Python 3.13+ 的现代特性
- 代码清晰，添加充分注释
- 完善测试，确保稳定性

### 代码质量
- **Black**：代码格式化
- **isort**：导入排序
- **Ruff**：代码检查和自动修复
- **MyPy**：严格类型检查
- **pre-commit**：Git提交前自动检查

## 📚 文档

- 📖 [开发指南](docs/development.md)
- 🛡️ [备份和恢复指南](docs/backup_restore_guide.md)
- 🔧 [第二阶段开发总结](docs/phase2-completion-summary.md)
- 🛠️ [工具集成指南](docs/第二阶段4-6板块儿开发方案材料/工具集成指南)
- 📊 [性能优化文档](docs/第二阶段4-6板块儿开发方案材料/性能优化系统)
- 🧠 [智能交互文档](docs/第二阶段4-6板块儿开发方案材料/智能交互系统)
- 🛡️ [错误处理文档](docs/第二阶段4-6板块儿开发方案材料/现代化错误处理系统)

## 📝 版本历史

### v0.2.1 (2025-06-14) - 备份功能增强
**数据安全增强版**

#### 🆕 新增功能
- 🛡️ **文本替换备份功能**：使用 `--backup` 选项在执行前自动备份文件
- 🤖 **AI 增强改进**：高风险操作强制确认（需输入 \"YES\")
- 💡 **推荐模式询问**：AI 提供改进建议时会询问是否使用

#### 🔧 改进
- 增强了非技术用户的数据安全保护
- 改进了操作历史记录功能
- 编写了详细的备份和恢复指南

### v0.2.0 (2025-06-13) - 第二阶段完成 🎉
**现代化增强版本**

#### 🆕 新增功能
- ✨ **现代化错误处理系统**：智能错误分类、建议生成和批量错误收集
- 🧠 **智能交互系统**：增强确认对话、风险评估和操作历史记录
- ⚡ **性能优化系统**：分块处理、异步操作和高效目录扫描
- 📊 **多格式输出**：支持 plain、JSON、CSV 等多种输出格式
- 📈 **深度监控集成**：Logfire 性能监控和错误追踪
- 🔧 **配置文件支持**：`.simple-tools.yml` 配置文件
- 📋 **操作历史记录**：`tools history` 命令查看操作历史

#### 🔧 技术栈升级
- 🐍 **Python 3.13+**：充分利用最新特性（match/case、异步增强等）
- 📦 **Pydantic v2.11.5+**：现代数据验证和序列化
- 📊 **Logfire 3.16.0+**：深度性能监控集成
- 🧪 **测试覆盖率**：从 70% 提升到 85%+
- 🔍 **代码质量**：集成 pre-commit、black、isort、ruff、mypy

#### 🏗️ 架构改进
- 📁 **utils模块**：新增 `src/simple_tools/utils/` 目录
- 🎯 **类型系统**：完善的类型注解和严格的类型检查
- 🔄 **异步支持**：关键操作支持异步处理
- 📊 **性能监控**：自动性能分析和优化建议

### v0.1.0 (2025-05-28) - 第一阶段完成
- ✅ 完成 5 个核心工具：文件列表、重复文件检测、批量重命名、文本替换、文件整理
- ✅ 集成 Logfire 监控系统
- ✅ 测试覆盖率达到 70%+
- ✅ 配置 GitHub Actions CI/CD
- ✅ 添加代码质量工具：black, isort, ruff, mypy

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 👨‍💻 作者

- [@sumu2025](https://github.com/sumu2025)

---

**项目理念**：工具是拿来用的，不是拿来秀的！

**第二阶段成就**：现代化技术栈 + 智能化交互 + 深度性能优化 = 极致用户体验 🚀
