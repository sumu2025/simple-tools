# DeepSeek API 集成问题修复说明

*更新日期: 2025-06-13*

## 已发现并修复的问题

### 1. API响应格式兼容性 ✅
**问题**：DeepSeek API返回的usage字段包含嵌套结构（如`prompt_tokens_details`），导致Pydantic模型解析失败。

**修复**：
- 将`DeepSeekResponse`模型中的`usage`字段类型从`Dict[str, int]`改为`Dict[str, Any]`
- 支持处理不同模型返回的不同格式

### 2. 默认模型配置 ✅
**问题**：默认模型被设置为`deepseek-reasoner`，而文档中说明使用`deepseek-chat`。

**修复**：
- 将默认模型改为`deepseek-chat`
- 增加对`deepseek-reasoner`模型的定价支持

### 3. API超时问题 ✅
**问题**：默认30秒超时对某些请求不够。

**修复**：
- 将默认超时时间从30秒增加到60秒

### 4. SecretStr类型处理 ✅
**问题**：配置中使用了`SecretStr`类型保护API密钥，但客户端代码访问方式不正确。

**修复**：
- 使用`get_secret_value()`方法正确访问密钥值

### 5. JSON响应解析 ✅
**问题**：某些模型的响应可能包含额外的解释文本，不是纯JSON格式。

**修复**：
- 增强测试脚本，使用正则表达式提取JSON部分
- 更好的错误处理和调试信息

## 重新运行测试

```bash
# 1. 确保最新代码
cd /Users/peacock/Projects/simple-tools

# 2. 设置环境变量（如果需要）
export DEEPSEEK_API_KEY="sk-b58b3a9773554f63ba64676f3f2a4775"
export SIMPLE_TOOLS_AI_ENABLED="true"

# 3. 运行测试
python sandbox/test_deepseek_api.py
```

## 可选配置

如果想测试特定模型，可以设置环境变量：
```bash
# 测试chat模型（默认）
export DEEPSEEK_MODEL="deepseek-chat"

# 测试reasoner模型
export DEEPSEEK_MODEL="deepseek-reasoner"

# 测试coder模型
export DEEPSEEK_MODEL="deepseek-coder"
```

## 注意事项

1. **模型差异**：不同的DeepSeek模型可能有不同的响应格式和性能特征
2. **成本控制**：`deepseek-reasoner`模型可能比`deepseek-chat`更贵，注意监控使用量
3. **响应时间**：复杂的推理任务可能需要更长时间，已将超时增加到60秒

## 下一步

1. 运行修复后的测试，确认所有功能正常
2. 运行单元测试：`poetry run pytest tests/test_ai_module.py -v`
3. 开始第2周的智能文件分类器开发

## 故障排除

### 如果仍然出现超时
```python
# 可以临时增加超时时间
export DEEPSEEK_TIMEOUT="120.0"  # 2分钟
```

### 如果JSON解析仍有问题
检查实际返回的内容，可能需要针对特定模型调整prompt，要求返回纯JSON格式。

### 查看详细日志
```bash
# 启用更详细的日志
export LOGFIRE_LEVEL="DEBUG"
```
