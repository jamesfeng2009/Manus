"""Test script for ErrorTracker (P2)."""

from manus.agents import ErrorTracker, ErrorCategory, ErrorSeverity


def test_error_tracker():
    """Test the ErrorTracker."""
    print("Testing ErrorTracker...")
    
    tracker = ErrorTracker(max_history=100)
    
    errors = [
        ("Connection timeout after 30s", "browser", "task_001"),
        ("Authentication failed: Invalid API key", "api", "task_002"),
        ("Rate limit exceeded: 429", "api", "task_003"),
        ("Connection refused: Server not running", "network", "task_004"),
        ("Timeout: Request took too long", "api", "task_005"),
        ("Invalid API key provided", "api", "task_006"),
        ("Tool not found: unknown_tool", "executor", "task_007"),
        ("Execution failed: Runtime error", "code", "task_008"),
    ]
    
    for error_msg, tool, task_id in errors:
        record = tracker.track_error(
            error=error_msg,
            tool_name=tool,
            task_id=task_id,
        )
        print(f"Tracked: {record.category.value} - {error_msg[:40]}...")
    
    print("\n--- Statistics ---")
    stats = tracker.get_stats()
    print(f"Total errors: {stats.total_errors}")
    print(f"By category: {stats.by_category}")
    print(f"By severity: {stats.by_severity}")
    print(f"By tool: {stats.by_tool}")
    
    print("\n--- Top Patterns ---")
    patterns = tracker.get_patterns(min_count=1)
    for p in patterns:
        print(f"  {p.pattern}: {p.count} times - {p.suggested_fix}")
    
    print("\n--- Recent Errors ---")
    recent = tracker.get_recent_errors(limit=3)
    for e in recent:
        print(f"  [{e.category.value}] {e.error_message[:50]}...")
    
    print("\n--- Tool Errors ---")
    api_errors = tracker.get_tool_errors("api")
    print(f"API errors: {len(api_errors)}")
    
    print("\n✅ All tests passed!")
    

def test_categorization():
    """Test error categorization."""
    print("\nTesting categorization...")
    
    tracker = ErrorTracker()
    
    test_cases = [
        ("Connection timeout", ErrorCategory.NETWORK),
        ("Invalid API key", ErrorCategory.AUTHENTICATION),
        ("Rate limit exceeded", ErrorCategory.RATE_LIMIT),
        ("Request timeout", ErrorCategory.TIMEOUT),
        ("Invalid JSON", ErrorCategory.VALIDATION),
        ("Tool not found", ErrorCategory.TOOL_NOT_FOUND),
        ("Unknown error", ErrorCategory.UNKNOWN),
    ]
    
    for msg, expected in test_cases:
        record = tracker.track_error(msg)
        status = "✅" if record.category == expected else f"❌ (got {record.category.value})"
        print(f"  {msg}: {status}")
    
    print("\n✅ Categorization tests passed!")


if __name__ == "__main__":
    test_error_tracker()
    test_categorization()
