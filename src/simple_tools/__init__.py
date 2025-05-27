"""simple-tools - 一个简单实用的Python工具集.

专注解决日常工作中的实际问题，不追求架构完美，只追求功能实用。
"""

import logfire

# 初始化Logfire监控系统
logfire.configure(
    service_name="simple-tools"
    # 移除 console 参数
)

__version__ = "0.1.0"
