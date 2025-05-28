## PyPI 发布说明

### 包名说明
- **GitHub 项目名**: `simple-tools`
- **PyPI 包名**: `sumu-simple-tools`
- **命令行工具名**: `tools`

由于 PyPI 上 `simple-tools` 名称已被占用，本项目在 PyPI 上使用 `sumu-simple-tools` 作为包名。但这不影响使用体验：
- 安装命令：`pip install sumu-simple-tools`
- 使用命令：`tools list`、`tools duplicates` 等保持不变

### 发布流程
1. 更新版本号：`poetry version patch/minor/major`
2. 更新 CHANGELOG.md
3. 提交代码：`git commit -m "chore: 发布版本 x.x.x"`
4. 创建标签：`git tag -a vx.x.x -m "版本 x.x.x"`
5. 推送到 GitHub：`git push origin main --tags`
6. 发布到 PyPI：`poetry publish --build`

### 相关链接
- PyPI 项目页面：https://pypi.org/project/sumu-simple-tools/
- GitHub 项目：https://github.com/sumu2025/simple-tools
