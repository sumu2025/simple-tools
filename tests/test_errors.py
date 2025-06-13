"""Tests for the modern error handling system."""

from typing import Any
from unittest.mock import patch

import pytest

from simple_tools.utils.errors import (
    BatchErrorCollector,
    ErrorContext,
    ToolError,
    format_friendly_error,
    get_error_suggestions,
    handle_errors,
)


class TestToolError:
    """Test cases for ToolError exception class."""

    def test_tool_error_basic_creation(self) -> None:
        """Test basic ToolError creation."""
        error = ToolError("Test error message")
        assert str(error) == "Test error message"
        assert error.context is None
        assert error.suggestions == []

    def test_tool_error_with_context(self) -> None:
        """Test ToolError with context."""
        context = ErrorContext(
            operation="test_operation", file_path="/test/path", details={"key": "value"}
        )
        error = ToolError("Test error", context=context)
        assert error.context == context
        assert error.context.operation == "test_operation"

    def test_tool_error_with_suggestions(self) -> None:
        """Test ToolError with suggestions."""
        suggestions = ["Try this", "Or try that"]
        error = ToolError("Test error", suggestions=suggestions)
        assert error.suggestions == suggestions

    def test_tool_error_from_exception(self) -> None:
        """Test creating ToolError from another exception."""
        original = ValueError("Original error")
        error = ToolError.from_exception(original, "Custom message")
        assert "Custom message" in str(error)
        assert "ValueError: Original error" in str(error)
        assert error.__cause__ == original


class TestErrorContext:
    """Test cases for ErrorContext class."""

    def test_error_context_creation(self) -> None:
        """Test ErrorContext creation."""
        context = ErrorContext(
            operation="file_copy",
            file_path="/test/file.txt",
            details={"size": 1024, "permissions": "644"},
        )
        assert context.operation == "file_copy"
        assert context.file_path == "/test/file.txt"
        assert context.details["size"] == 1024

    def test_error_context_optional_fields(self) -> None:
        """Test ErrorContext with optional fields."""
        context = ErrorContext(operation="test_op")
        assert context.operation == "test_op"
        assert context.file_path is None
        assert context.details == {}

    def test_error_context_to_dict(self) -> None:
        """Test ErrorContext serialization."""
        context = ErrorContext(
            operation="test", file_path="/path", details={"key": "value"}
        )
        result = context.to_dict()
        expected = {
            "operation": "test",
            "file_path": "/path",
            "details": {"key": "value"},
        }
        assert result == expected


class TestHandleErrors:
    """Test cases for handle_errors decorator."""

    def test_handle_errors_success(self) -> None:
        """Test handle_errors with successful function."""

        @handle_errors("test_operation")
        def successful_function(x: int) -> int:
            return x * 2

        result = successful_function(5)
        assert result == 10

    def test_handle_errors_with_exception(self) -> None:
        """Test handle_errors with function that raises exception."""

        @handle_errors("test_operation")
        def failing_function() -> None:
            raise ValueError("Something went wrong")

        with pytest.raises(ToolError) as exc_info:
            failing_function()

        error = exc_info.value
        assert "test_operation" in str(error)
        assert "ValueError: Something went wrong" in str(error)
        assert error.context.operation == "test_operation"

    def test_handle_errors_with_file_path(self) -> None:
        """Test handle_errors with file path context."""

        @handle_errors("file_operation", file_path="/test/file.txt")
        def file_function() -> None:
            raise OSError("File not found")

        with pytest.raises(ToolError) as exc_info:
            file_function()

        error = exc_info.value
        assert error.context.file_path == "/test/file.txt"
        assert "file_operation" in str(error)

    def test_handle_errors_with_suggestions(self) -> None:
        """Test handle_errors with custom suggestions."""
        suggestions = ["Check file permissions", "Verify file exists"]

        @handle_errors("file_read", suggestions=suggestions)
        def read_function() -> None:
            raise PermissionError("Access denied")

        with pytest.raises(ToolError) as exc_info:
            read_function()

        error = exc_info.value
        assert error.suggestions == suggestions


class TestBatchErrorCollector:
    """Test cases for BatchErrorCollector class."""

    def test_batch_error_collector_creation(self) -> None:
        """Test BatchErrorCollector creation."""
        collector = BatchErrorCollector("batch_operation")
        assert collector.operation == "batch_operation"
        assert len(collector.errors) == 0
        assert collector.has_errors() is False

    def test_add_error_with_exception(self) -> None:
        """Test adding error from exception."""
        collector = BatchErrorCollector("test_batch")

        try:
            raise ValueError("Test error")
        except Exception as e:
            collector.add_error("item1", e)

        assert collector.has_errors() is True
        assert len(collector.errors) == 1
        assert "item1" in collector.errors

    def test_add_error_with_string(self) -> None:
        """Test adding error from string message."""
        collector = BatchErrorCollector("test_batch")
        collector.add_error("item2", "Custom error message")

        assert collector.has_errors() is True
        assert len(collector.errors) == 1
        assert "item2" in collector.errors

    def test_add_multiple_errors(self) -> None:
        """Test adding multiple errors."""
        collector = BatchErrorCollector("multi_batch")

        collector.add_error("item1", "Error 1")
        collector.add_error("item2", ValueError("Error 2"))
        collector.add_error("item3", "Error 3")

        assert len(collector.errors) == 3
        assert all(item in collector.errors for item in ["item1", "item2", "item3"])

    def test_get_summary(self) -> None:
        """Test getting error summary."""
        collector = BatchErrorCollector("summary_test")

        collector.add_error("file1.txt", "Permission denied")
        collector.add_error("file2.txt", OSError("File not found"))

        summary = collector.get_summary()
        assert "summary_test" in summary
        assert "file1.txt" in summary
        assert "file2.txt" in summary
        assert "Permission denied" in summary
        assert "File not found" in summary

    def test_raise_if_errors(self) -> None:
        """Test raising ToolError if errors exist."""
        collector = BatchErrorCollector("raise_test")
        collector.add_error("item1", "Error message")

        with pytest.raises(ToolError) as exc_info:
            collector.raise_if_errors()

        error = exc_info.value
        assert "raise_test" in str(error)
        assert "item1" in str(error)

    def test_raise_if_errors_no_errors(self) -> None:
        """Test raise_if_errors when no errors exist."""
        collector = BatchErrorCollector("no_errors")
        # Should not raise any exception
        collector.raise_if_errors()


class TestErrorFormatting:
    """Test cases for error formatting functions."""

    def test_format_friendly_error_basic(self) -> None:
        """Test basic error formatting."""
        error = ToolError("Test error message")
        formatted = format_friendly_error(error)

        assert "❌ 错误" in formatted
        assert "Test error message" in formatted

    def test_format_friendly_error_with_context(self) -> None:
        """Test error formatting with context."""
        context = ErrorContext(
            operation="file_copy", file_path="/test/file.txt", details={"size": 1024}
        )
        error = ToolError("Copy failed", context=context)
        formatted = format_friendly_error(error)

        assert "file_copy" in formatted
        assert "/test/file.txt" in formatted
        assert "Copy failed" in formatted

    def test_format_friendly_error_with_suggestions(self) -> None:
        """Test error formatting with suggestions."""
        suggestions = ["Check permissions", "Verify disk space"]
        error = ToolError("Operation failed", suggestions=suggestions)
        formatted = format_friendly_error(error)

        assert "💡 建议" in formatted
        assert "Check permissions" in formatted
        assert "Verify disk space" in formatted

    def test_get_error_suggestions_file_not_found(self) -> None:
        """Test getting suggestions for file not found errors."""
        error = FileNotFoundError("No such file or directory")
        suggestions = get_error_suggestions(error)

        assert len(suggestions) > 0
        assert any("文件路径" in s or "路径" in s for s in suggestions)

    def test_get_error_suggestions_permission_error(self) -> None:
        """Test getting suggestions for permission errors."""
        error = PermissionError("Permission denied")
        suggestions = get_error_suggestions(error)

        assert len(suggestions) > 0
        assert any("权限" in s for s in suggestions)

    def test_get_error_suggestions_generic(self) -> None:
        """Test getting suggestions for generic errors."""
        error = ValueError("Invalid value")
        suggestions = get_error_suggestions(error)

        assert len(suggestions) > 0
        assert any("输入" in s or "值" in s or "参数" in s for s in suggestions)


class TestIntegrationScenarios:
    """Integration test scenarios."""

    def test_file_operation_error_handling(self) -> None:
        """Test error handling in file operations."""

        @handle_errors("file_read", file_path="/nonexistent/file.txt")
        def read_nonexistent_file() -> str:
            with open("/nonexistent/file.txt") as f:
                return f.read()

        with pytest.raises(ToolError) as exc_info:
            read_nonexistent_file()

        error = exc_info.value
        assert error.context.operation == "file_read"
        assert error.context.file_path == "/nonexistent/file.txt"
        assert len(error.suggestions) > 0

    def test_batch_operation_with_mixed_results(self) -> None:
        """Test batch operation with some successes and failures."""
        collector = BatchErrorCollector("batch_file_process")

        files = ["file1.txt", "file2.txt", "file3.txt"]

        for i, filename in enumerate(files):
            try:
                if i == 1:  # Simulate failure for second file
                    raise OSError(f"Cannot process {filename}")
                # Simulate success for other files
            except Exception as e:
                collector.add_error(filename, e)

        assert collector.has_errors() is True
        assert len(collector.errors) == 1
        assert "file2.txt" in collector.errors

        summary = collector.get_summary()
        assert "batch_file_process" in summary
        assert "file2.txt" in summary

    @patch("simple_tools.utils.errors.logfire")
    def test_error_logging_integration(self, mock_logfire: Any) -> None:
        """Test integration with Logfire logging."""

        @handle_errors("logged_operation")
        def failing_operation() -> None:
            raise RuntimeError("Logged error")

        with pytest.raises(ToolError):
            failing_operation()

        # Verify that logfire.error was called
        mock_logfire.error.assert_called()

    def test_nested_error_handling(self) -> None:
        """Test nested error handling scenarios."""

        @handle_errors("outer_operation")
        def outer_function() -> None:
            @handle_errors("inner_operation")
            def inner_function() -> None:
                raise ValueError("Inner error")

            inner_function()

        with pytest.raises(ToolError) as exc_info:
            outer_function()

        # Should get the outer ToolError
        error = exc_info.value
        assert error.context.operation == "outer_operation"
        # The inner ToolError should be the cause
        assert isinstance(error.__cause__, ToolError)
        assert error.__cause__.context.operation == "inner_operation"


class TestPerformanceAndEdgeCases:
    """Test performance and edge cases."""

    def test_large_batch_error_collection(self) -> None:
        """Test handling large number of errors efficiently."""
        collector = BatchErrorCollector("large_batch")

        # Add many errors
        for i in range(1000):
            collector.add_error(f"item_{i}", f"Error {i}")

        assert len(collector.errors) == 1000
        assert collector.has_errors() is True

        # Summary should be generated efficiently
        summary = collector.get_summary()
        assert "large_batch" in summary
        assert len(summary) > 0

    def test_error_with_unicode_content(self) -> None:
        """Test error handling with Unicode content."""
        unicode_message = "文件处理错误: 无法访问 📁 folder"
        error = ToolError(unicode_message)

        formatted = format_friendly_error(error)
        assert unicode_message in formatted

    def test_error_context_with_large_details(self) -> None:
        """Test ErrorContext with large details dictionary."""
        large_details = {f"key_{i}": f"value_{i}" for i in range(100)}
        context = ErrorContext(operation="large_context_test", details=large_details)

        assert len(context.details) == 100
        context_dict = context.to_dict()
        assert len(context_dict["details"]) == 100

    def test_error_handling_with_none_values(self) -> None:
        """Test error handling with None values."""
        context = ErrorContext(operation="test", file_path=None, details=None)

        error = ToolError("Test error", context=context)
        formatted = format_friendly_error(error)

        # Should handle None values gracefully
        assert "Test error" in formatted
        assert formatted is not None


# ... existing code ...


class TestErrorsCoverageImprovement:
    """Additional test cases to improve errors.py coverage to 85%"""

    def test_ioerror_oserror_code_inference(self) -> None:
        """Test IOError and OSError code inference"""
        # Test IOError
        io_error = OSError("Disk full")
        tool_error = ToolError.from_exception(io_error)
        assert tool_error.error_code == "OPERATION_FAILED"

        # Test OSError
        os_error = OSError("Network unavailable")
        tool_error = ToolError.from_exception(os_error)
        assert tool_error.error_code == "OPERATION_FAILED"

    def test_batch_collector_success_methods(self) -> None:
        """Test BatchErrorCollector success tracking methods"""
        collector = BatchErrorCollector("test_operation")

        # Test initial state
        assert collector.total_count == 0
        assert collector.error_count == 0
        assert collector.success_rate == 0.0

        # Test after recording successes
        collector.record_success()
        collector.record_success()
        assert collector.total_count == 2
        assert collector.success_rate == 1.0

        # Test mixed results
        collector.add_error("item1", ValueError("test error"))
        assert collector.total_count == 3
        assert collector.error_count == 1
        assert collector.success_rate == 2 / 3

    def test_error_suggestions_coverage(self) -> None:
        """Test all error suggestion branches"""
        from simple_tools.utils.errors import get_error_suggestions

        # Test IOError suggestions - 修改：期望中文建议
        io_suggestions = get_error_suggestions(OSError("test"))
        assert "检查系统资源" in io_suggestions
        assert "确认磁盘空间可用" in io_suggestions

        # Test OSError suggestions - 修改：期望中文建议
        os_suggestions = get_error_suggestions(OSError("test"))
        assert "检查系统资源" in os_suggestions

        # Test unknown error type - 修改：期望中文建议
        class CustomError(Exception):
            """Custom exception for testing."""

            pass

        custom_suggestions = get_error_suggestions(CustomError("test"))
        assert "仔细查看错误消息" in custom_suggestions
        assert "如需要请联系技术支持" in custom_suggestions

    def test_tool_error_suggestions_property(self) -> None:
        """Test ToolError suggestions for different error codes"""
        # Test INVALID_CONFIG suggestions - 修改：期望中文建议
        error = ToolError("Config error", error_code="INVALID_CONFIG")
        suggestions = error.suggestions
        assert "检查配置文件格式" in suggestions
        assert "确认配置项是否完整" in suggestions

    def test_context_summary_edge_cases(self) -> None:
        """Test ErrorContext summary generation edge cases"""
        # Test with empty details
        context = ErrorContext(operation="test_op", file_path="/test/path", details={})
        summary = context.context_summary
        assert "操作: test_op" in summary
        assert "文件: /test/path" in summary
        assert "详情:" not in summary  # Should not include empty details

        # Test with None values in details
        context = ErrorContext(
            operation="test_op",
            details={"key1": "value1", "key2": None, "key3": "value3"},
        )
        summary = context.context_summary
        assert "key1=value1" in summary
        assert "key3=value3" in summary
        assert "key2=None" not in summary  # Should filter out None values

    @patch("simple_tools.utils.errors.logfire")
    def test_logfire_integration(self, mock_logfire: Any) -> None:
        """Test Logfire logging integration"""
        # Test ToolError logging
        context = ErrorContext(operation="test_op", file_path="/test/path")
        error = ToolError("Test error", context=context)
        error.log_to_logfire()

        mock_logfire.span.assert_called()
        mock_logfire.error.assert_called()

        # Test BatchErrorCollector logging
        collector = BatchErrorCollector("test_operation")
        collector.record_success()
        collector.add_error("item1", ValueError("test"))
        collector.log_summary()

        # Should have called logfire.info
        mock_logfire.info.assert_called()

    def test_batch_format_summary_detailed(self) -> None:
        """Test BatchErrorCollector format_summary with various scenarios"""
        collector = BatchErrorCollector("test_operation")
        # Test with no errors
        summary = collector.format_summary()
        assert "all successful" in summary

        # Test with multiple error types
        collector.add_error("file1.txt", ValueError("Invalid value"))
        collector.add_error("file2.txt", ValueError("Another invalid value"))
        collector.add_error("file3.txt", FileNotFoundError("File missing"))
        collector.record_success()

        summary = collector.format_summary(max_errors_shown=1)
        assert "ValueError (2 items)" in summary
        assert "FileNotFoundError (1 items)" in summary
        assert "1 more similar errors" in summary  # Should show truncation


if __name__ == "__main__":
    pytest.main([__file__])
