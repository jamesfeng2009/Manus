"""Sandbox manager for creating and managing sandboxes."""

import asyncio
from typing import Any

from manus.sandbox.base import Sandbox, SandboxConfig, SandboxType, SandboxResult
from manus.sandbox.subprocess import SubprocessSandbox, RestrictedSubprocessSandbox
from manus.sandbox.docker import DockerSandbox, DockerSandboxPool


class SandboxManager:
    """Manager for creating and managing sandbox instances."""

    def __init__(self):
        self._sandbox_cache: dict[str, Sandbox] = {}
        self._default_type = SandboxType.SUBPROCESS

    def get_sandbox(
        self,
        sandbox_type: SandboxType | str = SandboxType.SUBPROCESS,
        config: SandboxConfig | None = None,
    ) -> Sandbox:
        """Get or create a sandbox instance.

        Args:
            sandbox_type: Type of sandbox (subprocess, docker)
            config: Sandbox configuration

        Returns:
            Sandbox instance
        """
        if isinstance(sandbox_type, str):
            sandbox_type = SandboxType(sandbox_type)

        cache_key = f"{sandbox_type.value}_{id(config)}"

        if cache_key not in self._sandbox_cache:
            if sandbox_type == SandboxType.SUBPROCESS:
                self._sandbox_cache[cache_key] = SubprocessSandbox(config)
            elif sandbox_type == SandboxType.DOCKER:
                self._sandbox_cache[cache_key] = DockerSandbox(config)
            else:
                raise ValueError(f"Unknown sandbox type: {sandbox_type}")

        return self._sandbox_cache[cache_key]

    async def execute(
        self,
        code: str,
        language: str = "python",
        sandbox_type: SandboxType | str = SandboxType.SUBPROCESS,
        timeout: int | None = None,
        memory_limit: int | None = None,
        config: SandboxConfig | None = None,
    ) -> SandboxResult:
        """Execute code in a sandbox.

        Args:
            code: Source code to execute
            language: Programming language
            sandbox_type: Type of sandbox to use
            timeout: Execution timeout in seconds
            memory_limit: Memory limit in MB
            config: Sandbox configuration

        Returns:
            Execution result
        """
        sandbox = self.get_sandbox(sandbox_type, config)
        return await sandbox.execute(
            code=code,
            language=language,
            timeout=timeout,
            memory_limit=memory_limit,
        )

    async def cleanup_all(self) -> None:
        """Clean up all sandbox instances."""
        for sandbox in self._sandbox_cache.values():
            await sandbox.cleanup()
        self._sandbox_cache.clear()


_manager: SandboxManager | None = None


def get_sandbox_manager() -> SandboxManager:
    """Get the global sandbox manager."""
    global _manager
    if _manager is None:
        _manager = SandboxManager()
    return _manager


def get_sandbox(
    sandbox_type: SandboxType | str = SandboxType.SUBPROCESS,
    config: SandboxConfig | None = None,
) -> Sandbox:
    """Get a sandbox instance (convenience function).

    Args:
        sandbox_type: Type of sandbox
        config: Sandbox configuration

    Returns:
        Sandbox instance
    """
    manager = get_sandbox_manager()
    return manager.get_sandbox(sandbox_type, config)


async def execute_in_sandbox(
    code: str,
    language: str = "python",
    sandbox_type: SandboxType | str = SandboxType.SUBPROCESS,
    timeout: int | None = None,
    memory_limit: int | None = None,
) -> SandboxResult:
    """Execute code in sandbox (convenience function).

    Args:
        code: Source code to execute
        language: Programming language
        sandbox_type: Type of sandbox
        timeout: Execution timeout
        memory_limit: Memory limit

    Returns:
        Execution result
    """
    manager = get_sandbox_manager()
    return await manager.execute(
        code=code,
        language=language,
        sandbox_type=sandbox_type,
        timeout=timeout,
        memory_limit=memory_limit,
    )
