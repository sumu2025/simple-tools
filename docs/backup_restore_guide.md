# 文本替换备份和恢复指南

## 使用备份功能

### 1. 创建备份
使用 `--backup` 选项在执行替换前自动备份文件：

```bash
tools replace "old:new" --backup --execute
```

### 2. 备份位置
备份文件保存在：`~/.simpletools-backup/`

每次备份创建一个带时间戳的目录，例如：
- `~/.simpletools-backup/replace_20250613_103000/`

### 3. 备份内容
- 所有将被修改的文件的原始副本
- `backup_info.json` 文件，包含备份信息

## 恢复文件

### 方法1：手动恢复单个文件
```bash
# 查看备份目录
ls ~/.simpletools-backup/

# 查看最新备份
ls ~/.simpletools-backup/replace_20250613_103000/

# 恢复单个文件
cp ~/.simpletools-backup/replace_20250613_103000/path/to/file.txt ./path/to/file.txt
```

### 方法2：恢复所有文件
```bash
# 进入备份目录
cd ~/.simpletools-backup/replace_20250613_103000/

# 恢复所有文件（保持目录结构）
cp -r * /original/project/path/
```

### 方法3：使用 rsync 恢复
```bash
# 更安全的恢复方式
rsync -av ~/.simpletools-backup/replace_20250613_103000/ /original/project/path/
```

## 查看备份信息
```bash
# 查看备份详情
cat ~/.simpletools-backup/replace_20250613_103000/backup_info.json
```

## 清理旧备份
```bash
# 删除超过30天的备份
find ~/.simpletools-backup -type d -mtime +30 -exec rm -rf {} +

# 或手动删除特定备份
rm -rf ~/.simpletools-backup/replace_20250613_103000/
```

## 最佳实践

1. **重要操作必须备份**
   ```bash
   tools replace "critical:change" --backup --execute
   ```

2. **先预览再执行**
   ```bash
   # 第一步：预览
   tools replace "old:new"

   # 第二步：确认后执行并备份
   tools replace "old:new" --backup --execute
   ```

3. **定期清理备份**
   - 备份会占用磁盘空间
   - 建议每月清理一次旧备份

## 注意事项

- 备份功能只在 `--execute` 模式下生效
- 预览模式（`--dry-run`）不会创建备份
- 备份保持原始文件的时间戳和权限
- 如果备份失败，操作仍会继续（会有警告）

## 紧急恢复步骤

如果误操作后需要紧急恢复：

1. **立即停止** - 不要再执行其他操作
2. **查找最新备份**
   ```bash
   ls -lt ~/.simpletools-backup/ | head -5
   ```
3. **验证备份内容**
   ```bash
   ls ~/.simpletools-backup/replace_XXXXXX_XXXXXX/
   ```
4. **恢复文件**
   ```bash
   cp -i ~/.simpletools-backup/replace_XXXXXX_XXXXXX/* .
   ```
   （-i 选项会在覆盖前询问）

---

💡 **提示**：虽然有备份功能，但最好的保护是使用版本控制系统（如 Git）！
