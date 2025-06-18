# 第三阶段第1周 - API集成问题解决方案

## 问题总结

从测试结果来看，我们遇到了以下问题：

1. **API响应格式不兼容** ✅ 已修复
   - DeepSeek API返回的usage字段包含嵌套结构
   - 解决方案：将usage类型改为Dict[str, Any]

2. **默认模型配置错误** ✅ 已修复
   - 默认使用了deepseek-reasoner而非deepseek-chat
   - 解决方案：修改默认模型配置

3. **超时问题** ✅ 已修复
   - 30秒对某些请求不够
   - 解决方案：增加到60秒

4. **API密钥类型处理** ✅ 已修复
   - SecretStr类型需要特殊处理
   - 解决方案：使用get_secret_value()方法

## 立即行动步骤

### 1. 运行基础测试
```bash
cd /Users/peacock/Projects/simple-tools
python sandbox/test_deepseek_basic.py
```

这个简化的测试脚本会：
- 验证API连接
- 测试基本对话功能
- 测试JSON响应解析

### 2. 如果基础测试通过
```bash
# 运行完整测试套件
python sandbox/test_deepseek_api.py

# 运行单元测试
poetry run pytest tests/test_ai_module.py -v
```

### 3. 故障排查

#### 如果仍有Pydantic验证错误
可能需要查看实际的API响应格式：
```python
# 在deepseek_client.py的第233行附近添加调试代码
print("API Response:", json.dumps(data, indent=2))
```

#### 如果超时问题持续
```bash
# 临时增加超时时间
export DEEPSEEK_TIMEOUT="120.0"
```

#### 如果模型问题
```bash
# 明确指定使用chat模型
export DEEPSEEK_MODEL="deepseek-chat"
```

## 代码已修复的文件

1. `src/simple_tools/ai/config.py`
   - 默认模型改为deepseek-chat
   - 超时时间增加到60秒

2. `src/simple_tools/ai/deepseek_client.py`
   - usage字段类型改为Dict[str, Any]
   - 修复API密钥访问方式
   - 增加deepseek-reasoner定价

3. `sandbox/test_deepseek_api.py`
   - 增强JSON提取逻辑
   - 更好的错误信息

## 新增的辅助文件

1. `docs/deepseek-integration-fixes.md` - 问题修复说明
2. `sandbox/test_deepseek_basic.py` - 简化的基础测试脚本

## 下一步计划

1. **确认API正常工作**
   - 运行基础测试确保连接正常
   - 解决任何剩余的兼容性问题

2. **开始第2周任务**
   - 实现智能文件分类器
   - 创建`ai/classifier.py`模块
   - 集成到file_organizer工具

3. **优化Prompt设计**
   - 确保AI返回纯JSON格式
   - 针对不同模型优化prompt

## 技术建议

1. **使用chat模型**：deepseek-chat模型更适合我们的应用场景
2. **JSON响应**：在prompt中明确要求"只返回JSON，不要其他内容"
3. **错误处理**：始终准备处理非预期的响应格式
4. **成本监控**：定期检查API使用量和费用

---

请先运行`test_deepseek_basic.py`测试脚本，确认基础功能正常后再继续开发。
