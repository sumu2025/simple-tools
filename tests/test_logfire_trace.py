"""logfire trace 功能的单元测试模块."""

import logfire


def test_logfire_trace() -> None:
    """测试 logfire.trace 是否能正常调用."""
    logfire.trace(
        "ci-trace-test ✅ Logfire CI trace 成功",
        extra={"env": "ci", "trigger": "test_logfire_trace"},
    )
    assert True
