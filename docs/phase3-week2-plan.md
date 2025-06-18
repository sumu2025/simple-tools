# 第三阶段第2周 - 智能文件分类器开发计划

*开始日期: 2025-06-14*

## 🎯 本周目标

实现一个基于AI的智能文件分类器，能够：
1. 根据文件内容智能判断文件类别
2. 提供分类建议和置信度
3. 与file_organizer工具无缝集成
4. 保持良好的用户体验

## 📋 开发任务清单

### Day 1-2: 分类器核心模块
- [ ] 创建 `src/simple_tools/ai/classifier.py`
- [ ] 实现文件内容提取功能
- [ ] 设计分类数据结构
- [ ] 实现基础分类逻辑

### Day 3-4: 集成和优化
- [ ] 修改 file_organizer 添加AI选项
- [ ] 实现分类结果展示
- [ ] 添加用户确认机制
- [ ] 优化分类准确度

### Day 5: 测试和文档
- [ ] 编写单元测试
- [ ] 测试各种文件类型
- [ ] 更新使用文档
- [ ] 完成集成测试

## 🏗️ 技术设计

### 1. 文件分类器架构

```python
class FileClassifier:
    """智能文件分类器"""

    def __init__(self, client: DeepSeekClient):
        self.client = client
        self.cache = {}

    async def classify_file(self, file_path: Path) -> ClassificationResult:
        """分类单个文件"""
        # 1. 提取文件信息
        # 2. 生成分类prompt
        # 3. 调用AI获取分类
        # 4. 解析返回结果

    async def classify_batch(self, files: List[Path]) -> List[ClassificationResult]:
        """批量分类文件"""
        # 并发处理多个文件
```

### 2. 文件信息提取

```python
def extract_file_info(file_path: Path) -> FileInfo:
    """提取文件信息用于分类"""
    # - 文件名和扩展名
    # - 文件大小
    # - 修改时间
    # - 内容预览（文本文件前200字符）
    # - MIME类型
```

### 3. 集成到file_organizer

```python
# 在 organize 命令添加选项
@click.option('--ai-classify', is_flag=True, help='使用AI智能分类')
@click.option('--show-confidence', is_flag=True, help='显示分类置信度')
```

## 📝 实施步骤

### Step 1: 创建分类器模块框架
```bash
# 创建新文件
touch src/simple_tools/ai/classifier.py
touch tests/test_ai_classifier.py
```

### Step 2: 实现基础功能
1. 文件信息提取
2. Prompt生成
3. AI调用
4. 结果解析

### Step 3: 测试驱动开发
- 先写测试用例
- 实现功能
- 优化性能

### Step 4: 集成测试
- 测试不同文件类型
- 验证分类准确性
- 确保错误处理

## 🧪 测试计划

### 测试文件类型
1. **文档类** - .pdf, .docx, .txt
2. **图片类** - .jpg, .png, .gif
3. **代码类** - .py, .js, .java
4. **数据类** - .csv, .json, .xml
5. **媒体类** - .mp3, .mp4, .avi

### 预期分类类别
- 工作文档
- 个人文件
- 项目代码
- 学习资料
- 临时文件
- 系统文件
- 归档文件
- 其他

## 🚀 快速开始

```bash
# 1. 确保环境配置正确
source ~/.zshrc  # 加载API密钥

# 2. 进入项目目录
cd /Users/peacock/Projects/simple-tools

# 3. 创建分类器模块
mkdir -p src/simple_tools/ai
touch src/simple_tools/ai/classifier.py

# 4. 开始开发！
```

## 📊 成功标准

- [ ] 分类准确率达到80%以上
- [ ] 平均响应时间小于5秒
- [ ] 支持至少10种文件类型
- [ ] 用户体验友好
- [ ] 测试覆盖完整

## 💡 开发提示

1. **保持简单** - 先实现基础功能，再优化
2. **缓存优化** - 相同类型文件可以复用分类规则
3. **批量处理** - 考虑并发调用提高效率
4. **用户控制** - AI只建议，用户决定

---

准备好开始第2周的开发了吗？让我们创建智能文件分类器！
