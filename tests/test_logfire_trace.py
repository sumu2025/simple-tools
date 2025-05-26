import logfire

def test_logfire_trace():
    logfire.trace(
        "ci-trace-test ✅ Logfire CI trace 成功",
        extra={
            "env": "ci",
            "trigger": "test_logfire_trace"
        }
     )
    assert True
