"""simple-tools - 一个简单实用的Python工具集.

专注解决日常工作中的实际问题，不追求架构完美，只追求功能实用。
"""

import os
import sys

import logfire

# 初始化Logfire监控系统

# 检查是否在格式化输出模式
is_formatted_output = False
if "--format" in sys.argv:
    format_index = sys.argv.index("--format")
    if format_index + 1 < len(sys.argv):
        format_type = sys.argv[format_index + 1]
        if format_type in ["json", "csv"]:
            is_formatted_output = True

# 检查环境变量
if os.environ.get("LOGFIRE_CONSOLE", "").lower() == "false":
    is_formatted_output = True

# 配置 Logfire
if is_formatted_output:
    # 格式化输出时，禁用控制台日志
    logfire.configure(
        service_name="simple-tools",
        console=False,  # 禁用控制台输出
        send_to_logfire=False,  # 也禁用发送，避免重试日志
    )
else:
    # 正常模式
    logfire.configure(service_name="simple-tools")

__version__ = "0.1.0"
