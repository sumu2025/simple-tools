"""错误处理模块.

提供统一的错误处理、智能建议生成和批量错误收集功能。
使用 Python 3.13 的 match/case 语法和 Pydantic v2 的 computed_field。
"""

from __future__ import annotations

import traceback
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar

import logfire
from pydantic import BaseModel, Field, computed_field, field_validator

F = TypeVar("F", bound=Callable[..., Any])


class ErrorContext(BaseModel):
    """错误上下文信息模型."""

    operation: str
    file_path: str | None = None
    details: dict[str, Any] | None = Field(default_factory=lambda: {})
    timestamp: str | None = None

    @field_validator("details", mode="before")
    @classmethod
    def validate_details(cls, v: Any) -> dict[str, Any]:
        """Validate details field, convert None to empty dict."""
        if v is None:
            return {}
        return dict(v)  # 确保返回类型是 dict

    @computed_field
    @property
    def context_summary(self) -> str:
        """生成上下文摘要."""
        parts = [f"操作: {self.operation}"]
        if self.file_path:
            parts.append(f"文件: {self.file_path}")
        if self.details:
            details_str = ", ".join(
                f"{k}={v}" for k, v in self.details.items() if v is not None
            )
            if details_str:
                parts.append(f"详情: {details_str}")
        return " | ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "operation": self.operation,
            "file_path": self.file_path,
            "details": self.details or {},
        }


class ToolError(Exception):
    """统一的工具错误类型.

    提供结构化的错误信息、智能建议生成和 Logfire 集成。
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        context: ErrorContext | None = None,
        original_error: Exception | None = None,
        suggestions: list[str] | None = None,
    ) -> None:
        """初始化 ToolError."""
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "GENERAL_ERROR"
        self.context = context
        self.original_error = original_error
        self._suggestions = suggestions

    @classmethod
    def from_exception(
        cls,
        original_error: Exception,
        custom_message: str | None = None,
        error_code: str | None = None,
        context: ErrorContext | None = None,
    ) -> ToolError:
        """从其他异常创建 ToolError.

        Args:
            original_error: 原始异常
            custom_message: 自定义消息
            error_code: 错误代码
            context: 错误上下文

        Returns:
            新的 ToolError 实例

        """
        if custom_message:
            message = (
                f"{custom_message}: {type(original_error).__name__}: {original_error}"
            )
        else:
            message = f"{type(original_error).__name__}: {original_error}"

        # 自动推断错误代码
        if not error_code:
            match type(original_error).__name__:
                case "FileNotFoundError":
                    error_code = "FILE_NOT_FOUND"
                case "PermissionError":
                    error_code = "PERMISSION_DENIED"
                case "ValueError":
                    error_code = "VALIDATION_ERROR"
                case "IOError" | "OSError":
                    error_code = "OPERATION_FAILED"
                case _:
                    error_code = "GENERAL_ERROR"

        error = cls(
            message=message,
            error_code=error_code,
            context=context,
            original_error=original_error,
        )
        error.__cause__ = original_error
        return error

    @property
    def suggestions(self) -> list[str]:
        """智能生成解决建议."""
        if self._suggestions is not None:
            return self._suggestions

        return self._generate_suggestions()

    def _generate_suggestions(self) -> list[str]:
        """基于错误代码生成建议."""
        match self.error_code:
            case "FILE_NOT_FOUND":
                return [
                    "检查文件路径是否正确",
                    "确认文件是否存在",
                    "检查文件权限",
                ]
            case "PERMISSION_DENIED":
                return [
                    "检查文件/目录权限",
                    "尝试使用管理员权限运行",
                    "确认当前用户有访问权限",
                ]
            case "INVALID_CONFIG":
                return [
                    "检查配置文件格式",
                    "确认配置项是否完整",
                    "参考配置文档示例",
                ]
            case "OPERATION_FAILED":
                return [
                    "检查操作参数是否正确",
                    "确认目标状态符合预期",
                    "查看详细错误日志",
                ]
            case "VALIDATION_ERROR":
                return [
                    "检查输入数据格式",
                    "确认必填字段是否完整",
                    "确保数据类型正确",
                ]
            case _:
                return []

    def format_message(self) -> str:
        """格式化用户友好的错误消息."""
        lines = [f"❌ 错误: {self.message}"]

        # Include context information if available
        if self.context:
            if self.context.operation:
                lines.append(f"操作: {self.context.operation}")
            if self.context.file_path:
                lines.append(f"文件: {self.context.file_path}")

        if self.suggestions:
            lines.append("💡 建议:")
            for i, suggestion in enumerate(self.suggestions, 1):
                lines.append(f"   {i}. {suggestion}")

        return "\n".join(lines)

    def log_to_logfire(self) -> None:
        """记录错误到 Logfire."""
        with logfire.span(
            "tool_error",
            error_code=self.error_code,
            message=self.message,
        ) as span:
            if self.context:
                span.set_attributes(
                    {
                        "operation": self.context.operation,
                        "file_path": self.context.file_path,
                        "context_details": self.context.details,
                    }
                )

            if self.original_error:
                span.set_attribute("original_error", str(self.original_error))
                span.set_attribute("traceback", traceback.format_exc())

            logfire.error(
                "Tool operation failed",
                error_code=self.error_code,
                suggestions=self.suggestions,
            )


def handle_errors(
    operation_name: str,
    file_path: str | None = None,
    suggestions: list[str] | None = None,
) -> Callable[[F], F]:
    """错误处理装饰器.

    自动捕获异常并转换为 ToolError，提供统一的错误处理体验。

    Args:
        operation_name: 操作名称，用于错误上下文
        file_path: 可选的文件路径
        suggestions: 可选的自定义建议

    Returns:
        装饰后的函数

    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except ToolError as e:
                # 如果已经是 ToolError，用当前操作名包装它
                # 保持原始错误作为 cause
                context = ErrorContext(
                    operation=operation_name,
                    file_path=file_path,
                    details={"inner_error": str(e)},
                )
                error = ToolError(
                    message=f"{operation_name}: {e.message}",
                    error_code=e.error_code,
                    context=context,
                    original_error=e.original_error,
                    suggestions=suggestions or e.suggestions,
                )
                error.__cause__ = e
                error.log_to_logfire()
                raise error
            except FileNotFoundError as e:
                context = ErrorContext(
                    operation=operation_name,
                    file_path=file_path
                    or (
                        Path(str(e).split("'")[1]).as_posix() if "'" in str(e) else None
                    ),
                )
                error = ToolError(
                    message=f"{operation_name}: File not found",
                    error_code="FILE_NOT_FOUND",
                    context=context,
                    original_error=e,
                    suggestions=suggestions,
                )
                error.log_to_logfire()
                raise error
            except PermissionError as e:
                context = ErrorContext(
                    operation=operation_name,
                    file_path=file_path,
                    details={"permission_error": str(e)},
                )
                error = ToolError(
                    message=f"{operation_name}: Permission denied",
                    error_code="PERMISSION_DENIED",
                    context=context,
                    original_error=e,
                    suggestions=suggestions,
                )
                error.log_to_logfire()
                raise error
            except ValueError as e:
                context = ErrorContext(
                    operation=operation_name,
                    file_path=file_path,
                    details={"value_error": str(e)},
                )
                error = ToolError(
                    message=f"{operation_name}: ValueError: {e}",
                    error_code="VALIDATION_ERROR",
                    context=context,
                    original_error=e,
                    suggestions=suggestions,
                )
                error.log_to_logfire()
                raise error
            except Exception as e:
                context = ErrorContext(
                    operation=operation_name,
                    file_path=file_path,
                    details={"unexpected_error": str(e)},
                )
                error = ToolError(
                    message=f"{operation_name}: {e}",
                    error_code="OPERATION_FAILED",
                    context=context,
                    original_error=e,
                    suggestions=suggestions,
                )
                error.log_to_logfire()
                raise error

        return wrapper  # type: ignore

    return decorator


class BatchErrorCollector:
    """批量错误收集器.

    用于收集批量操作中的错误，提供统一的错误汇总和报告。
    """

    def __init__(self, operation: str) -> None:
        """初始化 BatchErrorCollector."""
        self.operation = operation
        self.errors: dict[Any, Exception] = {}
        self.success_count: int = 0

    def add_error(self, item: Any, error: Exception | str) -> None:
        """添加错误（兼容测试接口）.

        Args:
            item: 处理失败的项目
            error: 发生的错误或错误消息

        """
        if isinstance(error, str):
            error = ToolError(error)

        self.errors[item] = error

        # 记录到 Logfire
        with logfire.span("batch_error_recorded") as span:
            span.set_attributes(
                {
                    "item": str(item),
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
            )

    def record_error(self, item: Any, error: Exception) -> None:
        """记录错误（保持向后兼容）."""
        self.add_error(item, error)

    def record_success(self) -> None:
        """记录成功操作."""
        self.success_count += 1

    def has_errors(self) -> bool:
        """检查是否有错误."""
        return len(self.errors) > 0

    def get_summary(self) -> str:
        """获取错误汇总（兼容测试接口）."""
        if not self.has_errors():
            return f"All {self.success_count} operations completed successfully"

        # Include specific error items and error messages in summary
        error_items = list(self.errors.keys())
        items_str = ", ".join(
            str(item) for item in error_items[:3]
        )  # Show first 3 items
        if len(error_items) > 3:
            items_str += f" and {len(error_items) - 3} more"

        # Include error messages in the summary
        summary_parts = [
            f"{self.operation}: {len(self.errors)} errors occurred. "
            f"Failed items: {items_str}"
        ]

        # Add error details
        for item, error in list(self.errors.items())[:3]:  # Show first 3 errors
            summary_parts.append(f"{item}: {str(error)}")

        return ". ".join(summary_parts)

    def raise_if_errors(self) -> None:
        """如果有错误则抛出 ToolError."""
        if not self.has_errors():
            return

        # 获取第一个错误项作为示例
        first_item = next(iter(self.errors.keys()))

        raise ToolError(
            message=(
                f"Batch operation '{self.operation}' failed with "
                f"{len(self.errors)} errors. First failed item: {first_item}"
            ),
            error_code="BATCH_OPERATION_FAILED",
            context=ErrorContext(
                operation=self.operation,
                details={
                    "total_errors": len(self.errors),
                    "success_count": self.success_count,
                    "first_failed_item": str(first_item),
                },
            ),
        )

    @property
    def total_count(self) -> int:
        """总处理数量."""
        return self.success_count + len(self.errors)

    @property
    def error_count(self) -> int:
        """错误数量."""
        return len(self.errors)

    @property
    def success_rate(self) -> float:
        """成功率."""
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count

    def format_summary(self, max_errors_shown: int = 5) -> str:
        """格式化错误汇总.

        Args:
            max_errors_shown: 最多显示的错误数量

        Returns:
            格式化的错误汇总字符串

        """
        if not self.errors:
            return (
                f"✅ Batch operation completed, processed "
                f"{self.success_count} items, all successful"
            )

        lines = [
            "📊 Batch operation summary:",
            f"   Total: {self.total_count} items",
            f"   Success: {self.success_count} items",
            f"   Failed: {self.error_count} items",
            f"   Success rate: {self.success_rate:.1%}",
            "",
        ]

        # 按错误类型分组
        error_groups: dict[str, list[tuple[Any, Exception]]] = {}
        for item, error in self.errors.items():
            error_type = type(error).__name__
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append((item, error))

        lines.append("❌ Error details:")
        for error_type, group_errors in error_groups.items():
            lines.append(f"   {error_type} ({len(group_errors)} items):")

            # 显示前几个错误示例
            shown_count = min(max_errors_shown, len(group_errors))
            for i, (item, error) in enumerate(group_errors[:shown_count]):
                lines.append(f"     • {item}: {error}")

            # 如果还有更多错误，显示省略信息
            if len(group_errors) > shown_count:
                remaining = len(group_errors) - shown_count
                lines.append(f"     ... {remaining} more similar errors")

            lines.append("")

        return "\n".join(lines)

    def log_summary(self) -> None:
        """记录汇总到 Logfire."""
        with logfire.span(
            "batch_operation_summary",
            total_count=self.total_count,
            success_count=self.success_count,
            error_count=self.error_count,
            success_rate=self.success_rate,
        ):
            if self.errors:
                # 记录错误统计
                error_stats: dict[str, int] = {}
                for _, error in self.errors.items():
                    error_type = type(error).__name__
                    error_stats[error_type] = error_stats.get(error_type, 0) + 1

                logfire.info(
                    "Batch operation completed with errors",
                    error_statistics=error_stats,
                )
            else:
                logfire.info("Batch operation completed successfully")


def format_friendly_error(
    error: ToolError | str,
    context: ErrorContext | None = None,
    suggestions: list[str] | None = None,
) -> str:
    """格式化用户友好的错误消息.

    Args:
        error: ToolError 实例或错误消息字符串
        context: 可选的错误上下文
        suggestions: 可选的建议列表

    Returns:
        格式化的错误消息字符串

    """
    if isinstance(error, str):
        # 如果传入的是字符串，创建一个临时的 ToolError
        temp_error = ToolError(f"Error: {error}", suggestions=suggestions)
        if context:
            temp_error.context = context
        return temp_error.format_message()

    return error.format_message()


def get_error_suggestions(error: Exception) -> list[str]:
    """获取错误建议.

    Args:
        error: 异常实例

    Returns:
        建议列表

    """
    match type(error).__name__:
        case "FileNotFoundError":
            return [
                "检查文件路径是否正确",
                "确认文件是否存在",
                "检查文件权限",
            ]
        case "PermissionError":
            return [
                "检查文件/目录权限",
                "尝试使用管理员权限运行",
                "确认当前用户有访问权限",
            ]
        case "ValueError":
            return [
                "检查输入数据格式",
                "确认必填字段是否完整",
                "确保数据类型正确",
            ]
        case "IOError" | "OSError":
            return [
                "检查系统资源",
                "确认磁盘空间可用",
                "检查网络连接（如适用）",
            ]
        case _:
            return [
                "仔细查看错误消息",
                "检查操作参数",
                "如需要请联系技术支持",
            ]
