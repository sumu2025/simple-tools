# AI功能配置示例

## 1. 设置环境变量（推荐）

在你的shell配置文件（如 ~/.bashrc 或 ~/.zshrc）中添加：

```bash
# DeepSeek API密钥
export DEEPSEEK_API_KEY="sk-your-api-key-here"

# 启用AI功能
export SIMPLE_TOOLS_AI_ENABLED="true"

# 可选：自定义API端点
# export DEEPSEEK_API_BASE="https://api.deepseek.com/v1"
```

然后重新加载配置：
```bash
source ~/.bashrc  # 或 source ~/.zshrc
```

## 2. 在配置文件中设置

编辑 `~/.simple-tools.yml` 文件：

```yaml
# AI配置
ai:
  enabled: true                    # 启用AI功能
  provider: deepseek              # AI提供商
  model: deepseek-chat            # 使用的模型
  max_tokens: 1000                # 最大生成token数
  temperature: 0.7                # 生成温度（0-1）
  cache_ttl: 3600                 # 缓存有效期（秒）

  # 成本控制
  daily_limit: 10.0               # 每日费用限额（元）
  monthly_limit: 300.0            # 每月费用限额（元）

  # 功能开关
  features:
    smart_classify: true          # 智能文件分类
    auto_summarize: true          # 文档自动摘要
    content_analysis: true        # 内容智能分析
```

## 3. 测试配置

运行测试脚本验证配置：

```bash
cd /Users/peacock/Projects/simple-tools/sandbox
python test_deepseek_api.py
```

## 4. 在命令中使用AI功能

### 智能文件整理（即将实现）
```bash
# 使用AI分析文件内容进行智能分类
tools organize ~/Downloads --ai-classify
```

### 文档摘要（即将实现）
```bash
# 生成文档摘要
tools summarize report.pdf
```

### 文本替换智能分析（即将实现）
```bash
# AI分析替换风险
tools replace "bug:feature" --ai-check
```

## 5. 查看AI使用统计（即将实现）

```bash
# 查看今日AI使用情况
tools ai-stats

# 查看详细使用历史
tools ai-stats --detailed
```

## 注意事项

1. **API密钥安全**：不要将API密钥提交到版本控制系统
2. **成本控制**：设置合理的每日/每月限额
3. **隐私保护**：敏感文件不会发送到AI
4. **网络要求**：需要稳定的网络连接访问DeepSeek API

## 常见问题

### Q: 如何获取DeepSeek API密钥？
A: 访问 https://platform.deepseek.com 注册账号并创建API密钥

### Q: AI功能是否必需？
A: 不是。所有AI功能都是可选的增强功能，基础工具功能不依赖AI

### Q: 如何禁用AI功能？
A: 设置环境变量 `SIMPLE_TOOLS_AI_ENABLED=false` 或在配置文件中设置 `ai.enabled: false`

### Q: API调用失败怎么办？
A: 工具会自动降级到非AI模式，不影响基础功能使用
