# 智能文本分析功能使用指南

*功能版本: 1.0 | 创建日期: 2025-06-15 | 适用版本: v0.3.0+*

## 功能概述

智能文本分析是 `text_replace` 工具的AI增强功能，能够在执行文本替换前分析潜在的风险，帮助用户避免常见的替换错误。

### 主要特性

- **风险识别**：自动识别可能的误替换情况
- **智能建议**：提供更安全的替换模式
- **上下文感知**：根据文件类型和内容进行分析
- **可选启用**：AI功能完全可选，不影响基础使用

## 快速开始

### 1. 配置AI功能

首先需要配置DeepSeek API密钥：

```bash
# 方式1：环境变量
export SIMPLE_TOOLS_AI_ENABLED=true
export DEEPSEEK_API_KEY="your-api-key"

# 方式2：配置文件 ~/.simple-tools.yml
ai:
  enabled: true
  api_key: "your-api-key"
```

### 2. 使用AI分析

在文本替换命令中添加 `--ai-check` 参数：

```bash
# 基础用法
tools replace "bug:issue" -p ./src --ai-check

# 结合其他选项
tools replace "class:type" -p ./src -e .py --ai-check --execute
```

## 使用示例

### 示例1：检测子串风险

```bash
tools replace "bug:issue" -p ./code --ai-check
```

输出：
```
🤖 正在进行 AI 风险分析...

📊 AI 文本替换分析
==================================================
原始模式: bug → issue

❌ 风险等级: HIGH

🔍 识别的风险:

  1. ❌ 'bug' 是其他常见词的子串
     示例: 可能会影响: debug, bugfix, debugger
     建议: 使用单词边界: \bbug\b

💡 推荐模式: \bbug\b:issue

📈 分析置信度: 85%

⚠️  检测到高风险替换操作！
是否仍要继续执行？ [y/N]:
```

### 示例2：代码文件智能分析

```bash
tools replace "class:cls" -p ./python_project -e .py --ai-check
```

AI会分析Python代码上下文，识别出：
- `class` 关键字的使用
- 变量名中的 `class`
- 字符串中的 `class`

并给出针对性的建议。

### 示例3：删除操作警告

```bash
tools replace "TODO:" -p ./docs --ai-check
```

输出：
```
⚠️ 风险等级: MEDIUM

🔍 识别的风险:
  1. ⚠️ 替换为空字符串会删除匹配的文本
     建议: 确认是否真的要删除这些文本
```

## 风险等级说明

### 🟢 LOW (低风险)
- 简单的文本替换
- 不太可能造成意外影响
- 通常可以安全执行

### 🟡 MEDIUM (中风险)
- 可能有一些副作用
- 需要注意特定情况
- 建议仔细检查

### 🔴 HIGH (高风险)
- 很可能造成意外替换
- 强烈建议修改模式
- 默认需要再次确认

## 高级功能

### 1. 跳过AI确认

如果您确定要执行高风险操作：

```bash
tools replace "test:prod" --ai-check -y
```

### 2. 查看AI分析但不执行

使用预览模式查看分析结果：

```bash
tools replace "pattern" --ai-check --dry-run
```

### 3. 批量文件的智能分析

AI会分析前几个文件的内容样本，提供整体建议：

```bash
tools replace "v2.0:v3.0" -p ./project --ai-check
```

## 常见场景

### 场景1：版本号更新

```bash
# 风险：可能影响到IPv4地址、小数等
tools replace "2.0:3.0" --ai-check

# AI建议：使用更精确的模式
tools replace "version 2.0:version 3.0" --ai-check
```

### 场景2：变量重命名

```bash
# 风险：影响其他包含该词的变量
tools replace "user:customer" -e .js --ai-check

# AI建议：使用单词边界或更具体的模式
```

### 场景3：配置文件修改

```bash
# 在配置文件中替换
tools replace "debug:false" -e .json --ai-check
```

## 注意事项

1. **AI分析需要时间**：特别是首次调用时，可能需要1-3秒
2. **需要网络连接**：AI分析需要调用DeepSeek API
3. **成本考虑**：每次分析会消耗少量API额度
4. **隐私保护**：只发送必要的内容样本，不会发送完整文件

## 故障排除

### AI功能未启用

```
⚠️  AI功能未启用或配置不正确
```

解决方法：
1. 检查环境变量是否设置
2. 确认API密钥是否正确
3. 查看 ~/.simple-tools.yml 配置

### AI分析失败

```
⚠️  AI分析失败: [错误信息]
```

可能原因：
- 网络连接问题
- API密钥无效
- API服务暂时不可用

此时工具会降级到基础分析模式，仍可继续使用。

## 最佳实践

1. **先预览再执行**：使用 `--dry-run` 查看影响范围
2. **从小范围开始**：先在单个文件或小目录测试
3. **利用AI建议**：采纳AI提供的改进模式
4. **保留备份**：重要操作前先备份或使用版本控制

## 与其他功能配合

### 结合进度显示

```bash
tools replace "pattern" --ai-check --execute
# 会显示：AI分析 → 确认 → 进度条 → 结果
```

### 结合输出格式

```bash
tools replace "pattern" --ai-check --format json
```

### 查看操作历史

```bash
tools history
# 会记录是否使用了AI分析
```

---

**提示**：AI分析是辅助工具，最终决定权在您手中。如果您对建议有疑问，可以先在测试环境验证。
