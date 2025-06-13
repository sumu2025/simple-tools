#!/bin/bash
cd /Users/peacock/Projects/simple-tools
echo "=== 更新版本号到 v0.2.0 ==="
poetry version 0.2.0
echo "版本更新完成"

echo "=== 提交 v0.2.0 版本 ==="
git add .
git commit -m "feat: 发布 v0.2.0 版本

🎉 第二阶段开发完成 - 现代化增强版本

✨ 新增功能:
- 现代化错误处理系统 (智能建议生成)
- 智能交互系统 (风险评估、操作历史)
- 性能优化系统 (分块处理、异步操作)
- 多格式输出支持 (plain/JSON/CSV)
- 深度监控集成 (Logfire性能追踪)
- 配置文件支持 (.simple-tools.yml)

🔧 技术栈升级:
- Python 3.13+ 现代特性
- Pydantic v2.11.5+ 数据验证
- 测试覆盖率提升至 85%+
- 完整的代码质量工具链

📁 新增 src/simple_tools/utils/ 模块:
- errors.py - 现代化错误处理
- smart_interactive.py - 智能交互
- performance_optimizer.py - 性能优化
- formatter.py - 格式化输出
- progress.py - 进度显示
- config_loader.py - 配置加载"

echo "=== 创建版本标签 ==="
git tag -a v0.2.0 -m "第二阶段完成 - 现代化增强版本

主要成就:
- 🧠 智能交互和错误处理
- ⚡ 性能优化和异步支持
- 📊 多格式输出和深度监控
- 🔧 Python 3.13+ 现代技术栈
- 🧪 85%+ 测试覆盖率"

echo "完成! v0.2.0 版本已发布 🎉"
