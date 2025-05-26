# 简单工具集项目开发指南 v2.1

*文档版本: 2.1.0 | 更新日期: 2025-05-24 | 最后验证日期: 2025-05-24*

## 1. 项目概述

### 1.1 项目定位
一个简单实用的Python工具集，专注解决日常工作中的实际问题。不追求架构完美，只追求功能实用。

### 1.2 核心原则
- **极简主义**：每个工具控制在100行代码内
- **实用至上**：解决实际问题，避免花哨功能
- **快速完成**：完成比完美更重要
- **合理工具**：使用成熟工具但避免过度使用

### 1.3 设计红线
- ❌ 严禁多仓架构
- ❌ 禁止过早优化扩展性
- ❌ 拒绝100%测试覆盖追求
- ❌ 避免过度抽象设计

## 2. 技术规范

### 2.1 技术栈标准
```
Python版本: 3.13.3+
Pydantic版本: 2.11.5+ (严格使用v2.x)
Logfire版本: 3.16.0+
依赖管理工具：Poetry
CLI框架：Click
测试框架：pytest
```

### 2.2 项目目录结构
```
simple-tools/
├── pyproject.toml       # Poetry项目配置
├── poetry.lock          # 依赖版本锁定
├── src/
│   └── simple_tools/
│       ├── __init__.py  # Logfire监控初始化
│       ├── cli.py       # Click命令行入口
│       ├── core/        # 核心功能模块
│       │   ├── file_tool.py      # 文件处理工具
│       │   ├── text_tool.py      # 文本处理工具
│       │   └── ...               # 其他工具模块
│       └── config.py    # 配置管理中心
├── tests/               # pytest测试套件
│   ├── conftest.py      # 测试配置
│   └── test_*.py        # 具体测试文件
├── sandbox/             # 临时测试环境（已忽略）
├── docs/                # 项目文档
│   └── development.md   # 本开发指南
├── README.md            # 项目说明
└── .gitignore          # Git忽略配置
```

### 2.3 依赖管理策略

#### 核心依赖（必需）
```toml
[tool.poetry.dependencies]
python = "^3.13"
click = "^8.1"         # CLI命令行框架
pydantic = "^2.11"     # 数据验证（严格v2.x）
logfire = "^3.16.0"    # 监控日志系统

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"        # 单元测试框架
pytest-cov = "^5.0"    # 测试覆盖率统计
```

#### 可选依赖（按需添加）
- **httpx**: HTTP请求场景
- **rich**: 终端输出美化
- **python-dotenv**: 环境变量管理（如需使用 .env 文件）

### 2.4 编码标准
- 详细的中文注释说明
- 单个函数不超过20行
- 单个文件不超过100行
- 严格使用Python类型提示
- 必要的异常错误处理

## 3. 环境准备

### 3.1 开发环境配置
```bash
# 安装Python 3.13+
# macOS使用Homebrew
brew install python@3.13

# 安装Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 配置Poetry使用项目内虚拟环境
poetry config virtualenvs.in-project true
```

### 3.2 Logfire认证配置
Logfire 使用本地配置文件管理认证，首次运行时会自动引导配置：
```bash
# 首次运行时，Logfire会自动创建 .logfire/logfire_credentials.json
# 按照提示完成认证即可

# 注意：.logfire/ 目录应该加入 .gitignore
echo ".logfire/" >> .gitignore
```

### 3.3 Logfire初始化配置
在 `src/simple_tools/__init__.py` 中的标准配置：
```python
import logfire

# 初始化Logfire监控系统
logfire.configure(
    service_name="simple-tools"
)

# 注意：Logfire会自动读取本地配置文件进行认证
# 无需手动配置token等信息
```

### 3.4 环境变量配置（可选）
如果需要使用环境变量进行更灵活的配置，可以安装 `python-dotenv`：
```bash
# 可选：添加环境变量支持
poetry add python-dotenv

# 创建 .env 文件
echo "DEBUG=true" >> .env
echo "LOG_LEVEL=INFO" >> .env
```

## 4. 监控集成方案

### 4.1 Logfire配置标准
Logfire 使用本地配置文件自动管理认证，初次使用时会引导完成配置。配置文件存储在 `.logfire/` 目录中，无需手动管理 token。

### 4.2 监控使用规范
- 关键功能入口添加span跟踪
- 重要操作记录info级别日志
- 异常处理记录error级别日志
- 性能敏感操作添加时间统计

### 4.3 监控代码示例
```python
import logfire

class FileListTool:
    """文件列表工具"""

    def list_files(self, path: str, show_all: bool = False) -> list:
        """列出目录文件"""
        with logfire.span("list_files", attributes={
            "path": path,
            "show_all": show_all
        }):
            try:
                logfire.info(f"开始列出目录: {path}")
                # 功能实现代码
                result = self._scan_directory(path, show_all)
                logfire.info(f"成功列出 {len(result)} 个文件",
                           attributes={"item_count": len(result)})
                return result
            except Exception as e:
                logfire.error(f"列出目录失败: {str(e)}")
                raise
```

### 4.4 错误处理模板
```python
from typing import Optional
import logfire
import click

def safe_operation(func):
    """安全操作装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            logfire.error(f"文件未找到: {e}")
            raise click.ClickException(f"错误：文件或目录不存在 - {e}")
        except PermissionError as e:
            logfire.error(f"权限不足: {e}")
            raise click.ClickException(f"错误：没有访问权限 - {e}")
        except Exception as e:
            logfire.error(f"未知错误: {e}")
            raise click.ClickException(f"发生未知错误：{e}")
    return wrapper
```

## 5. 开发阶段规划

### 第一阶段：基础工具开发（1-2周）
**目标**：完成5个核心工具，建立项目基础框架

| 工具名称 | 功能说明 | 开发状态 | CLI命令 |
|----------|----------|----------|---------|
| list_files | 智能文件列表展示 | ✅ 已完成 | `tools list PATH` |
| find_duplicates | 重复文件检测清理 | ⏳ 待开发 | `tools duplicates PATH` |
| batch_rename | 批量文件重命名 | ⏳ 待开发 | `tools rename PATTERN` |
| text_replace | 文本批量替换 | ⏳ 待开发 | `tools replace FILE` |
| file_organizer | 自动文件整理 | ⏳ 待开发 | `tools organize PATH` |

### 第二阶段：功能完善优化（3-4周）
**目标**：提升工具使用体验和稳定性

**主要任务**：
- 完善异常错误处理机制
- 添加操作进度显示功能
- 实现多种输出格式支持
- 编写完整的单元测试套件

### 第三阶段：智能化能力增强（5-8周）
**目标**：选择性集成AI能力，保持简单原则

**可选功能**：
- Claude API集成调用
- 智能文件分类器
- 文档自动摘要生成
- 保持调用接口简单

### 第四阶段：MCP工具化封装（2-3个月后）
**目标**：封装为MCP协议工具，扩展使用场景

**实现计划**：
- 深入学习MCP协议标准
- 设计适配器模式封装
- 保持核心代码架构不变
- 发布到MCP生态系统

## 6. 开发工作流程

### 6.1 项目初始化流程
```bash
# 1. 创建项目结构
mkdir -p simple-tools/{src/simple_tools/{core},tests,docs,sandbox}
cd simple-tools

# 2. 初始化Poetry项目
poetry init

# 3. 添加核心依赖
poetry add python@^3.13 click@^8.1 pydantic@^2.11 logfire@^3.16.0
poetry add --group dev pytest@^8.0 pytest-cov@^5.0

# 4. 可选：添加环境变量支持
# poetry add python-dotenv

# 5. 安装依赖
poetry install

# 6. 初始化Git
git init
echo "/sandbox/" >> .gitignore
echo ".env" >> .gitignore
echo "__pycache__/" >> .gitignore
echo ".logfire/" >> .gitignore
echo ".pytest_cache/" >> .gitignore
echo ".venv/" >> .gitignore
```

### 6.2 新工具开发标准流程
1. 在core目录实现核心功能逻辑
2. 在cli.py添加对应Click命令
3. 编写相应的pytest单元测试
4. 使用Logfire添加关键监控日志
5. 在sandbox环境进行手动测试
6. 代码审查通过后提交版本控制

### 6.3 工具开发模板
```python
# src/simple_tools/core/example_tool.py
"""示例工具模块"""
from typing import List, Optional
import logfire
from pydantic import BaseModel, Field

class ToolConfig(BaseModel):
    """工具配置模型"""
    path: str = Field(..., description="处理路径")
    recursive: bool = Field(False, description="是否递归处理")

class ExampleTool:
    """示例工具类"""

    def __init__(self, config: ToolConfig):
        self.config = config
        logfire.info(f"初始化工具: {config.model_dump()}")

    def process(self) -> List[str]:
        """执行处理逻辑"""
        with logfire.span("process", attributes={"path": self.config.path}):
            try:
                # 实现具体功能
                results = []
                logfire.info(f"处理完成，共 {len(results)} 项")
                return results
            except Exception as e:
                logfire.error(f"处理失败: {e}")
                raise
```

### 6.4 CLI命令集成模板
```python
# 在 src/simple_tools/cli.py 中添加
import click

@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--recursive', '-r', is_flag=True, help='递归处理子目录')
def example(path: str, recursive: bool):
    """示例工具命令"""
    from .core.example_tool import ExampleTool, ToolConfig

    config = ToolConfig(path=path, recursive=recursive)
    tool = ExampleTool(config)
    results = tool.process()

    # 输出结果
    for item in results:
        click.echo(item)
```

### 6.5 测试策略方针
采用实用主义测试策略，重点测试核心功能和边界情况，避免过度测试。

#### 单元测试模板
```python
# tests/test_example_tool.py
import pytest
from simple_tools.core.example_tool import ExampleTool, ToolConfig

class TestExampleTool:
    """示例工具测试类"""

    def test_basic_functionality(self, tmp_path):
        """测试基本功能"""
        config = ToolConfig(path=str(tmp_path))
        tool = ExampleTool(config)
        results = tool.process()
        assert isinstance(results, list)

    def test_error_handling(self):
        """测试错误处理"""
        config = ToolConfig(path="/invalid/path")
        tool = ExampleTool(config)
        with pytest.raises(FileNotFoundError):
            tool.process()
```

### 6.6 Sandbox测试环境使用
sandbox目录用于手动测试和实验，不会被Git跟踪。**注意：这里使用简单的Python脚本，不需要pytest**。

#### Sandbox使用原则
- 快速验证：直接编写可执行的Python脚本
- 临时性质：测试完成后可随时删除
- 不追求规范：代码可以"脏"一点，重在快速验证
- 独立运行：每个测试脚本都应该能独立执行

#### 示例测试脚本
```bash
# 在sandbox中创建测试脚本
# sandbox/test_new_feature.py
import sys
sys.path.insert(0, '../src')

from simple_tools.core.example_tool import ExampleTool, ToolConfig

# 快速测试新功能
config = ToolConfig(path="./test_data")
tool = ExampleTool(config)
results = tool.process()

# 直接打印结果查看
print(f"处理结果: {results}")
print(f"结果数量: {len(results)}")

# 可以加入临时的调试代码
import pprint
pprint.pprint(results[:5])  # 只看前5个结果
```

#### 运行方式
```bash
# 方式1：直接运行
cd sandbox
python test_new_feature.py

# 方式2：使用poetry环境运行
poetry run python sandbox/test_new_feature.py

# 方式3：交互式测试
poetry run python
>>> from simple_tools.core.file_tool import FileListTool
>>> tool = FileListTool()
>>> tool.list_files(".")
```

## 7. AI协作工作规范

### 7.1 任务边界控制
- **单次任务**：每次仅实现一个独立小功能
- **代码限制**：单次展示代码不超过50行
- **拒绝建议**：严格拒绝"顺便优化"类建议

### 7.2 代码审查标准流程
1. **AI展示**：提供代码和详细中文解释
2. **人工确认**：确保理解无误后执行
3. **沙盒测试**：在sandbox环境验证功能
4. **正式提交**：测试通过后写入src目录

### 7.3 设计红线警告
- 出现"框架"、"架构"词汇 → 立即中止讨论
- 建议新增3个以上文件 → 重新评估必要性
- 引入新外部依赖 → 必须充分论证必要性

### 7.4 AI输出规范
- 优先使用自然语言说明方案
- 需要输出代码时先询问确认
- 代码输出采用artifact格式
- 避免一次性输出过长内容

## 8. 版本与进度管理

### 8.1 版本号管理规则
- **0.1.x**：基础工具功能完成
- **0.2.x**：CLI用户体验优化
- **0.3.x**：智能化功能集成
- **1.0.0**：MCP工具正式发布

### 8.2 进度跟踪记录
采用CHANGELOG.md文件记录每个版本的功能变更和bug修复。

#### CHANGELOG.md 模板
```markdown
# 更新日志

## [0.1.1] - 2025-05-24
### 新增
- 完成 list_files 工具基础功能
- 添加 Logfire 监控集成

### 修复
- 修复路径处理中的编码问题

### 变更
- 优化文件大小显示格式

## [0.1.0] - 2025-05-23
### 新增
- 项目初始化
- 基础目录结构创建
- Poetry 依赖配置
```

### 8.3 Git工作流程

#### 分支管理策略
- **main分支**：稳定版本，所有代码直接提交
- **不使用feature分支**：保持简单，避免过度流程

#### 提交规范
```bash
# 功能开发
git add .
git commit -m "feat: 添加文件列表功能"

# 问题修复
git commit -m "fix: 修复路径处理错误"

# 文档更新
git commit -m "docs: 更新使用说明"

# 测试添加
git commit -m "test: 添加单元测试"

# 配置调整
git commit -m "config: 更新依赖配置"
```

#### 版本发布流程
```bash
# 1. 更新版本号
poetry version patch  # 0.1.0 -> 0.1.1

# 2. 更新 CHANGELOG.md
# 手动编辑添加版本变更说明

# 3. 提交版本变更
git add pyproject.toml CHANGELOG.md
git commit -m "chore: 发布版本 0.1.1"

# 4. 创建版本标签
git tag -a v0.1.1 -m "版本 0.1.1"
git push origin main --tags
```

### 8.4 依赖版本更新策略
- **月度检查**：每月第一周检查依赖更新
- **保守更新**：只更新补丁版本（patch）
- **测试验证**：更新后必须运行全部测试
- **记录变更**：在CHANGELOG中记录依赖更新

## 9. 常见问题预防机制

### 9.1 依赖膨胀控制
- **严格评估**：每个新依赖都需论证必要性
- **优先复用**：优先使用已有依赖提供的功能
- **定期审查**：定期review和清理无用依赖

#### 依赖评估检查清单
```
□ 是否可以用标准库实现？
□ 现有依赖是否已提供类似功能？
□ 依赖的维护状态是否活跃？
□ 依赖的体积是否合理？
□ 是否真的能显著简化开发？
```

### 9.2 功能范围控制
- **严格边界**：严格按照规划的5个工具开发
- **需求记录**：新需求记录但不立即实现
- **阶段完成**：当前阶段完成后再考虑扩展

#### 需求管理模板
```markdown
# ideas.md - 功能想法记录（不立即实现）

## 待评估功能
1. **批量图片压缩** - 用户A提出，2025-05-24
   - 需求：批量压缩图片文件
   - 评估：可能需要引入Pillow依赖
   - 决策：延后到第二阶段考虑

2. **文件加密工具** - 用户B提出，2025-05-25
   - 需求：对敏感文件进行加密
   - 评估：需要密码学库
   - 决策：超出项目范围，不实现
```

### 9.3 过度优化预防
- **可用优先**：第一版只要能正常工作即可
- **反馈驱动**：基于用户反馈再进行优化
- **性能诊断**：性能问题使用Logfire进行定位

#### 优化时机判断标准
1. **不要优化**：功能刚完成，还没有用户使用
2. **考虑优化**：多个用户反馈相同问题
3. **必须优化**：Logfire显示明显性能瓶颈

### 9.4 代码复杂度控制
```python
# ❌ 错误示例：过度抽象
from abc import ABC, abstractmethod

class AbstractFileProcessor(ABC):
    @abstractmethod
    def process(self): pass

class FileProcessorFactory:
    def create_processor(self, type): pass

# ✅ 正确示例：简单直接
from pathlib import Path
from typing import List

def process_files(path: str) -> List[str]:
    """处理文件，返回结果列表"""
    results = []
    for file in Path(path).iterdir():
        results.append(str(file))
    return results
```

## 10. 项目成功标准

### 10.1 各阶段验收标准
1. **第一阶段验收**：5个核心工具都能正常运行
2. **第二阶段验收**：具备完整友好的CLI使用体验
3. **第三阶段验收**：至少实现1个AI智能增强功能
4. **第四阶段验收**：能够作为MCP工具正常使用

### 10.2 项目整体成功标志
- ✅ **日常使用**：开发者自己每天都在使用
- ✅ **代码质量**：代码简单易懂易维护
- ✅ **架构稳定**：没有重构的冲动和需求
- ✅ **价值实现**：切实解决了实际工作问题

### 10.3 质量检查清单
```markdown
## 发布前检查清单
- [ ] 所有工具都有完整的中文注释
- [ ] 每个工具都有对应的测试用例
- [ ] CLI帮助信息清晰明了
- [ ] 错误信息友好且有指导性
- [ ] README文档包含所有使用示例
- [ ] 依赖版本已锁定（poetry.lock）
- [ ] Logfire监控正常工作（已配置认证）
- [ ] 在干净环境中测试安装流程
```

## 11. 长期维护策略

### 11.1 维护边界（不做什么）
- **避免重构**：除非绝对必要否则不进行重构
- **功能克制**：不添加"可能会用到"的功能
- **架构简单**：不追求所谓完美架构设计

### 11.2 持续改进方向
- **用户反馈**：积极收集和响应使用反馈
- **问题修复**：及时修复实际使用中的bug
- **小步迭代**：采用小步快跑的迭代优化策略

### 11.3 文档维护计划
**触发文档更新的条件**：
1. 新增或移除依赖时
2. 项目结构发生变化时
3. 开发流程有重大调整时
4. 发现文档与实际不符时

**文档更新原则**：
- 保持文档与代码同步
- 优先更新最常用的部分
- 删除过时的内容
- 保持简洁，避免冗余

## 12. CLI命令速查表

```bash
# 已实现的命令
tools list PATH              # 列出目录文件
tools list PATH --all        # 包含隐藏文件
tools list PATH --long       # 显示详细信息

# 计划实现的命令
tools duplicates PATH        # 查找重复文件
tools rename PATTERN         # 批量重命名
tools replace FILE           # 文本替换
tools organize PATH          # 文件整理

# 通用选项
--help                       # 显示帮助信息
--version                    # 显示版本号
--verbose                    # 详细输出模式
```

---

## 核心理念提醒

**始终记住**：简单实用，快速完成，适度工具化，坚决拒绝过度设计！

**成功关键**：解决实际问题 > 技术完美度 > 架构优雅性

**开发原则**：能用 > 好用 > 完美

**项目口号**：「工具是拿来用的，不是拿来秀的」

---

*本指南将随项目发展持续更新，最新版本请查看项目知识库。*
