"""Sandbox base interfaces and types."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SandboxType(Enum):
    """Sandbox types."""
    SUBPROCESS = "subprocess"
    DOCKER = "docker"


class Language(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    BASH = "bash"


@dataclass
class SandboxResult:
    """Result of sandbox execution."""
    success: bool
    output: str
    error: str | None = None
    execution_time: float = 0.0
    memory_used: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SandboxConfig:
    """Sandbox configuration."""
    timeout: int = 30
    memory_limit: int = 256
    cpu_limit: int = 1
    network_enabled: bool = False
    allowed_dirs: list[str] = field(default_factory=lambda: ["/tmp"])
    blocked_modules: list[str] = field(
        default_factory=lambda: [
            "os.system",
            "subprocess",
            "socket",
            "requests",
            "urllib",
            "importlib",
            "ctypes",
            "fcntl",
            "pty",
        ]
    )


class Sandbox(ABC):
    """Abstract base class for sandbox implementations."""

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()

    @abstractmethod
    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout: int | None = None,
        memory_limit: int | None = None,
    ) -> SandboxResult:
        """Execute code in sandbox.

        Args:
            code: Source code to execute
            language: Programming language (python, javascript, bash)
            timeout: Maximum execution time in seconds
            memory_limit: Maximum memory in MB

        Returns:
            SandboxResult with execution output
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup sandbox resources."""
        pass

    def _get_file_extension(self, language: str) -> str:
        """Get file extension for language."""
        extensions = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "bash": ".sh",
        }
        return extensions.get(language, ".txt")

    def _get_executor(self, language: str) -> str:
        """Get executor command for language."""
        executors = {
            "python": "python3",
            "javascript": "node",
            "typescript": "npx ts-node",
            "bash": "bash",
        }
        return executors.get(language, "python3")

    async def _run_with_timeout(
        self,
        coro: Any,
        timeout: int,
    ) -> Any:
        """Run coroutine with timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Execution timeout after {timeout} seconds")


class SandboxError(Exception):
    """Sandbox execution error."""
    pass


class SandboxTimeoutError(SandboxError):
    """Execution timeout error."""
    pass


class SandboxPermissionError(SandboxError):
    """Permission denied error."""
    pass
