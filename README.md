# simple-tools

[![CI](https://github.com/sumu2025/simple-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/sumu2025/simple-tools/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-70%25-yellowgreen)](https://github.com/sumu2025/simple-tools)
[![Python](https://img.shields.io/badge/python-3.13+-blue)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/poetry-managed-blueviolet)](https://python-poetry.org/)
[![PyPI](https://img.shields.io/pypi/v/sumu-simple-tools)](https://pypi.org/project/sumu-simple-tools/)

一个简单实用的 Python 工具集，专注解决日常工作中的实际问题。

## 🚀 特性

- **极简主义**：每个工具控制在 100 行代码内
- **实用至上**：解决实际问题，避免花哨功能
- **监控集成**：使用 Logfire 进行性能监控
- **高测试覆盖**：核心功能测试覆盖率 90%+

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

### 1. list_files - 文件列表工具
智能展示目录内容，支持隐藏文件和详细信息显示。

```bash
# 列出当前目录
tools list

# 列出指定目录，显示隐藏文件
tools list ~/Downloads --all

# 显示详细信息（文件大小、修改时间）
tools list --long
```

### 2. find_duplicates - 重复文件检测
高效查找重复文件，支持按大小、扩展名过滤。

```bash
# 扫描当前目录
tools duplicates

# 只扫描大于 1MB 的文件
tools duplicates -s 1048576

# 只检测特定类型文件
tools duplicates -e .jpg -e .png

# 显示删除建议
tools duplicates --show-commands
```

### 3. batch_rename - 批量重命名
支持文本替换和序号添加两种模式。

```bash
# 文本替换模式
tools rename "old:new"

# 序号模式
tools rename "photo" -n

# 只处理特定类型文件
tools rename "draft:final" -f "*.txt"

# 直接执行（跳过预览）
tools rename "test:prod" --execute
```

### 4. text_replace - 文本批量替换
在文件中查找并替换指定文本内容。

```bash
# 单文件替换
tools replace "localhost:127.0.0.1" -f config.ini

# 批量替换目录下的文件
tools replace "v2.0:v2.1" -p docs

# 只处理特定类型文件
tools replace "TODO:DONE" -e .txt -e .md

# 跳过确认直接执行
tools replace "old:new" -y
```

### 5. file_organizer - 文件自动整理
根据文件类型或日期自动整理文件。

```bash
# 按类型整理（默认）
tools organize ~/Downloads

# 按日期整理
tools organize . --mode date

# 混合模式（先类型后日期）
tools organize ~/Desktop --mode mixed

# 递归处理子目录
tools organize . --recursive
```

## 💻 开发

### 环境要求
- Python 3.13+
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
```

### 项目结构
```
simple-tools/
├── src/
│   └── simple_tools/
│       ├── __init__.py       # Logfire 初始化
│       ├── cli.py           # CLI 入口
│       ├── config.py        # 配置管理
│       └── core/            # 核心工具模块
│           ├── file_tool.py
│           ├── duplicate_finder.py
│           ├── batch_rename.py
│           ├── text_replace.py
│           └── file_organizer.py
├── tests/                   # 单元测试
├── docs/                    # 项目文档
└── pyproject.toml          # 项目配置
```

## 🧪 测试

项目使用 pytest 进行测试，核心功能测试覆盖率达到 90% 以上。

```bash
# 运行所有测试
poetry run pytest

# 运行特定测试文件
poetry run pytest tests/test_file_tool.py

# 生成 HTML 覆盖率报告
poetry run pytest --cov-report=html
open htmlcov/index.html
```

## 📊 监控

项目集成了 Logfire 监控系统，首次运行时会引导配置：

1. 运行任意命令时，Logfire 会自动创建配置文件
2. 按照提示完成认证
3. 访问 Logfire 控制台查看性能数据

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发原则
- 保持简单，拒绝过度设计
- 每个工具独立，避免复杂依赖
- 代码清晰，添加充分注释
- 完善测试，确保稳定性

## 📚 项目文档导航

- 📄 [第二阶段工作规划](docs/phase2-plan.md)

## 📝 版本历史

### v0.1.0 (2025-05-28)
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
# just to trigger CI at 2025年 5月30日 星期五 22时17分27秒 CST
