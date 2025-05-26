import logfire

def test_logfire_trace():
    logfire.trace("ci-trace-test", extra={"env": "ci", "purpose": "verify-logfire-in-ci"})
    assert True  # 简单通过，关键是触发 trace
