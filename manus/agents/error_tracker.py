"""ErrorTracker - P2: Error pattern tracking and statistics."""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class ErrorCategory(Enum):
    """Error categories."""
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    EXECUTION = "execution"
    TOOL_NOT_FOUND = "tool_not_found"
    TOOL_ERROR = "tool_error"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorRecord:
    """Record of a single error."""
    id: str
    timestamp: datetime
    error_type: str
    error_message: str
    category: ErrorCategory
    severity: ErrorSeverity
    tool_name: str | None = None
    task_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution: str | None = None


@dataclass
class ErrorPattern:
    """Pattern of recurring errors."""
    pattern: str
    category: ErrorCategory
    count: int = 0
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    recent_errors: list[ErrorRecord] = field(default_factory=list)
    suggested_fix: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "category": self.category.value,
            "count": self.count,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "recent_errors": len(self.recent_errors),
            "suggested_fix": self.suggested_fix,
        }


@dataclass
class ErrorStats:
    """Error statistics."""
    total_errors: int = 0
    by_category: dict[str, int] = field(default_factory=dict)
    by_severity: dict[str, int] = field(default_factory=dict)
    by_tool: dict[str, int] = field(default_factory=dict)
    avg_resolution_time: float = 0.0
    top_patterns: list[ErrorPattern] = field(default_factory=list)


class ErrorTracker:
    """P2: Error pattern tracking and statistics.
    
    Features:
    - Error categorization
    - Pattern detection
    - Statistics aggregation
    - Trend analysis
    """

    CATEGORY_PATTERNS: dict[ErrorCategory, list[str]] = {
        ErrorCategory.NETWORK: [
            "connection", "timeout", "network", "dns", "refused",
            "econnrefused", "socket", "ssl", "tls",
        ],
        ErrorCategory.AUTHENTICATION: [
            "auth", "unauthorized", "forbidden", "invalid token",
            "api key", "credential", "permission denied", "access denied",
        ],
        ErrorCategory.RATE_LIMIT: [
            "rate limit", "too many requests", "429", "quota",
            "throttle", "rate limit exceeded",
        ],
        ErrorCategory.TIMEOUT: [
            "timeout", "timed out", "deadline exceeded",
            "request timeout", "connection timeout",
        ],
        ErrorCategory.VALIDATION: [
            "validation", "invalid", "malformed", "parse error",
            "schema", "type error", "required field",
        ],
        ErrorCategory.EXECUTION: [
            "execution failed", "runtime error", "process error",
            "exception", "crash", "killed",
        ],
        ErrorCategory.TOOL_NOT_FOUND: [
            "tool not found", "no such tool", "unknown tool",
            "tool.*not found", "cannot find tool",
        ],
        ErrorCategory.TOOL_ERROR: [
            "tool error", "tool failed", "execute error",
            "tool execution", "operation failed",
        ],
    }

    def __init__(self, max_history: int = 1000, pattern_window: int = 100):
        self.max_history = max_history
        self.pattern_window = pattern_window
        
        self._errors: list[ErrorRecord] = []
        self._patterns: dict[str, ErrorPattern] = {}
        self._tool_errors: dict[str, list[ErrorRecord]] = defaultdict(list)
        self._category_counts: dict[ErrorCategory, int] = defaultdict(int)
        self._severity_counts: dict[ErrorSeverity, int] = defaultdict(int)

    def track_error(
        self,
        error: Exception | str,
        tool_name: str | None = None,
        task_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> ErrorRecord:
        """Track an error occurrence."""
        error_type = type(error).__name__ if isinstance(error, Exception) else "Error"
        error_message = str(error)
        
        category = self._categorize_error(error_message)
        severity = self._estimate_severity(error_message, category)
        
        record = ErrorRecord(
            id=f"err_{len(self._errors)}_{datetime.now().timestamp()}",
            timestamp=datetime.now(),
            error_type=error_type,
            error_message=error_message,
            category=category,
            severity=severity,
            tool_name=tool_name,
            task_id=task_id,
            context=context or {},
        )
        
        self._errors.append(record)
        self._category_counts[category] += 1
        self._severity_counts[severity] += 1
        
        if tool_name:
            self._tool_errors[tool_name].append(record)
        
        self._update_pattern(record)
        
        if len(self._errors) > self.max_history:
            self._errors = self._errors[-self.max_history:]
        
        return record

    def _categorize_error(self, error_message: str) -> ErrorCategory:
        """Categorize error by message content."""
        error_lower = error_message.lower()
        
        for category, patterns in self.CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if pattern in error_lower:
                    return category
        
        return ErrorCategory.UNKNOWN

    def _estimate_severity(
        self,
        error_message: str,
        category: ErrorCategory,
    ) -> ErrorSeverity:
        """Estimate error severity."""
        error_lower = error_message.lower()
        
        if category in [ErrorCategory.RATE_LIMIT, ErrorCategory.TIMEOUT]:
            return ErrorSeverity.MEDIUM
        
        if category == ErrorCategory.AUTHENTICATION:
            return ErrorSeverity.HIGH
        
        if "fatal" in error_lower or "crash" in error_lower:
            return ErrorSeverity.CRITICAL
        
        if "warning" in error_lower or "minor" in error_lower:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM

    def _update_pattern(self, record: ErrorRecord):
        """Update error pattern tracking."""
        key = self._extract_pattern_key(record.error_message)
        
        if key not in self._patterns:
            self._patterns[key] = ErrorPattern(
                pattern=key,
                category=record.category,
                first_seen=record.timestamp,
            )
        
        pattern = self._patterns[key]
        pattern.count += 1
        pattern.last_seen = record.timestamp
        pattern.recent_errors.append(record)
        
        if len(pattern.recent_errors) > self.pattern_window:
            pattern.recent_errors = pattern.recent_errors[-self.pattern_window:]
        
        if pattern.count >= 3:
            pattern.suggested_fix = self._generate_fix_suggestion(pattern)

    def _extract_pattern_key(self, error_message: str) -> str:
        """Extract pattern key from error message."""
        error_lower = error_message.lower()
        
        if "timeout" in error_lower:
            return "timeout_error"
        if "connection" in error_lower:
            return "connection_error"
        if "authentication" in error_lower or "unauthorized" in error_lower:
            return "authentication_error"
        if "rate limit" in error_lower or "429" in error_lower:
            return "rate_limit_error"
        if "not found" in error_lower:
            return "not_found_error"
        if "invalid" in error_lower:
            return "validation_error"
        
        words = re.findall(r'\w+', error_lower)
        if len(words) > 3:
            return f"error_{words[0]}_{words[1]}"
        
        return error_lower[:50]

    def _generate_fix_suggestion(self, pattern: ErrorPattern) -> str:
        """Generate fix suggestion for pattern."""
        suggestions = {
            "timeout_error": "Consider increasing timeout or using exponential backoff",
            "connection_error": "Check network connectivity and API endpoint",
            "authentication_error": "Verify API key is valid and not expired",
            "rate_limit_error": "Implement rate limiting and retry with backoff",
            "not_found_error": "Check resource exists or spelling",
            "validation_error": "Review input format and required fields",
        }
        
        return suggestions.get(pattern.pattern, "Review error details and retry")

    def get_stats(self, time_window: timedelta | None = None) -> ErrorStats:
        """Get error statistics."""
        errors = self._errors
        
        if time_window:
            cutoff = datetime.now() - time_window
            errors = [e for e in errors if e.timestamp >= cutoff]
        
        stats = ErrorStats(
            total_errors=len(errors),
            by_category={k.value: v for k, v in self._category_counts.items()},
            by_severity={k.value: v for k, v in self._severity_counts.items()},
        )
        
        for tool, errors_list in self._tool_errors.items():
            if time_window:
                errors_list = [e for e in errors_list if e.timestamp >= cutoff]
            stats.by_tool[tool] = len(errors_list)
        
        sorted_patterns = sorted(
            self._patterns.values(),
            key=lambda p: p.count,
            reverse=True,
        )
        stats.top_patterns = sorted_patterns[:5]
        
        return stats

    def get_patterns(self, min_count: int = 1) -> list[ErrorPattern]:
        """Get error patterns."""
        return [
            p for p in self._patterns.values()
            if p.count >= min_count
        ]

    def get_recent_errors(
        self,
        limit: int = 10,
        category: ErrorCategory | None = None,
    ) -> list[ErrorRecord]:
        """Get recent errors."""
        errors = self._errors[-limit:]
        
        if category:
            errors = [e for e in errors if e.category == category]
        
        return errors

    def get_tool_errors(self, tool_name: str) -> list[ErrorRecord]:
        """Get errors for specific tool."""
        return self._tool_errors.get(tool_name, [])

    def clear(self):
        """Clear all error data."""
        self._errors.clear()
        self._patterns.clear()
        self._tool_errors.clear()
        self._category_counts.clear()
        self._severity_counts.clear()


_global_tracker: ErrorTracker | None = None


def get_error_tracker() -> ErrorTracker:
    """Get global error tracker instance."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = ErrorTracker()
    return _global_tracker
