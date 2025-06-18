#!/usr/bin/env python3
"""测试AI集成功能"""

import os
import subprocess
import sys

import pytest


def test_ai_import() -> None:
    """测试AI模块导入"""
    try:
        from simple_tools.ai.classifier import FileClassifier
        from simple_tools.ai.config import get_ai_config

        print("✅ AI模块导入成功")

        # 验证类可以被实例化
        config = get_ai_config()
        assert config is not None, "AI配置获取失败"

        # 注意：FileClassifier可能需要API key，所以只测试类定义存在
        assert FileClassifier is not None, "FileClassifier类不存在"

    except ImportError as e:
        pytest.fail(f"AI模块导入失败: {e}")


def test_organize_cmd_import() -> None:
    """测试organize命令模块导入"""
    try:
        from simple_tools.core.file_organizer import FileOrganizerTool, organize_cmd

        print("✅ organize命令模块导入成功")

        # 验证函数和类存在
        assert organize_cmd is not None, "organize_cmd函数不存在"
        assert FileOrganizerTool is not None, "FileOrganizerTool类不存在"

    except ImportError as e:
        pytest.fail(f"organize命令模块导入失败: {e}")


def test_organize_help_contains_ai_classify() -> None:
    """测试organize命令帮助信息包含--ai-classify参数"""
    result = subprocess.run(
        [sys.executable, "-m", "simple_tools.cli", "organize", "--help"],
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
    )

    print("=== organize --help 输出 ===")
    print(f"Return code: {result.returncode}")
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)

    # 检查命令是否成功执行
    assert result.returncode == 0, f"命令执行失败，返回码: {result.returncode}"

    # 检查是否包含--ai-classify参数
    if "--ai-classify" in result.stdout:
        print("✅ AI集成成功！--ai-classify 参数已添加")
    else:
        print("❌ AI集成失败！未找到 --ai-classify 参数")

    assert "--ai-classify" in result.stdout, "--ai-classify 参数未找到"


def test_organize_ai_classify_help_text() -> None:
    """测试--ai-classify参数的帮助文本"""
    result = subprocess.run(
        [sys.executable, "-m", "simple_tools.cli", "organize", "--help"],
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
    )

    assert result.returncode == 0, "命令执行失败"

    # 检查帮助文本是否包含AI相关说明
    help_text = result.stdout.lower()
    assert "ai" in help_text or "智能" in help_text, "帮助文本缺少AI功能说明"


def test_ai_integration_complete() -> None:
    """综合测试：验证AI集成的完整性"""
    print("🤖 正在进行AI集成完整性测试...")

    # 1. 检查AI模块可以导入并实例化
    try:
        from simple_tools.ai.classifier import FileClassifier
        from simple_tools.ai.config import get_ai_config
        from simple_tools.ai.deepseek_client import DeepSeekClient
        from simple_tools.ai.prompts import PromptManager

        # 验证模块可用性
        config = get_ai_config()
        assert config is not None, "AI配置获取失败"

        # 验证PromptManager可用
        assert PromptManager is not None, "PromptManager类不存在"
        templates = PromptManager.templates
        assert "file_classify" in templates, "缺少file_classify模板"

        # 验证FileClassifier和DeepSeekClient类存在（不实例化，避免需要API key）
        assert FileClassifier is not None, "FileClassifier类不存在"
        assert DeepSeekClient is not None, "DeepSeekClient类不存在"

        print("✓ 所有AI模块导入成功")
    except ImportError as e:
        pytest.fail(f"AI模块导入失败: {e}")
    except Exception as e:
        pytest.fail(f"AI模块验证失败: {e}")

    # 2. 检查file_organizer集成
    try:
        from simple_tools.core.file_organizer import FileOrganizerTool, OrganizeConfig

        # 尝试创建包含AI功能的实例
        config = OrganizeConfig(path=".")
        organizer = FileOrganizerTool(config, ai_classify=True)
        assert organizer.ai_classify is not None, "AI分类标志未正确设置"
        print("✓ FileOrganizerTool AI集成成功")
    except Exception as e:
        pytest.fail(f"FileOrganizerTool AI集成失败: {e}")

    # 3. 检查CLI集成
    result = subprocess.run(
        [sys.executable, "-m", "simple_tools.cli", "organize", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, "CLI命令执行失败"
    assert "--ai-classify" in result.stdout, "CLI缺少--ai-classify参数"
    print("✓ CLI AI参数集成成功")

    print("🎉 AI集成完整性测试通过！")


if __name__ == "__main__":
    # 如果直接运行此文件，执行所有测试
    pytest.main([__file__, "-v"])
