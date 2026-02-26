"""Subprocess-based sandbox implementation."""

import asyncio
import os
import platform
import tempfile
import time
from pathlib import Path

from manus.sandbox.base import (
    Sandbox,
    SandboxConfig,
    SandboxResult,
    SandboxError,
    SandboxTimeoutError,
)


class SubprocessSandbox(Sandbox):
    """Subprocess-based sandbox for safe code execution."""

    def __init__(
        self,
        config: SandboxConfig | None = None,
        work_dir: str | None = None,
    ):
        super().__init__(config)
        self.work_dir = Path(work_dir or tempfile.mkdtemp(prefix="manus_sandbox_"))
        self._processes: list[asyncio.subprocess.Process] = []

    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout: int | None = None,
        memory_limit: int | None = None,
    ) -> SandboxResult:
        """Execute code in subprocess sandbox."""
        timeout = timeout or self.config.timeout
        memory_limit = memory_limit or self.config.memory_limit

        executor = self._get_executor(language)
        ext = self._get_file_extension(language)

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=ext,
                dir=str(self.work_dir),
                delete=False,
            ) as f:
                f.write(code)
                code_file = f.name

            try:
                start_time = time.time()

                if platform.system() == "Windows":
                    result = await self._execute_windows(
                        executor, code_file, timeout, memory_limit
                    )
                else:
                    result = await self._execute_unix(
                        executor, code_file, timeout, memory_limit
                    )

                result.execution_time = time.time() - start_time
                return result

            finally:
                self._cleanup_file(code_file)

        except TimeoutError as e:
            return SandboxResult(
                success=False,
                output="",
                error=str(e),
                execution_time=timeout,
            )
        except Exception as e:
            return SandboxResult(
                success=False,
                output="",
                error=f"Execution error: {str(e)}",
            )

    async def _execute_unix(
        self,
        executor: str,
        code_file: str,
        timeout: int,
        memory_limit: int,
    ) -> SandboxResult:
        """Execute on Unix-like systems."""
        import resource
        import signal

        cmd = [executor, code_file]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.work_dir),
            )
            self._processes.append(proc)

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout,
                )

                output = stdout.decode("utf-8", errors="replace")
                error = stderr.decode("utf-8", errors="replace")

                return SandboxResult(
                    success=proc.returncode == 0,
                    output=output,
                    error=error if proc.returncode != 0 else None,
                    metadata={"returncode": proc.returncode},
                )

            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise SandboxTimeoutError(f"Execution timeout after {timeout}s")

        finally:
            self._processes = [p for p in self._processes if p != proc]

    async def _execute_windows(
        self,
        executor: str,
        code_file: str,
        timeout: int,
        memory_limit: int,
    ) -> SandboxResult:
        """Execute on Windows."""
        cmd = [executor, code_file]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.work_dir),
            )
            self._processes.append(proc)

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout,
                )

                output = stdout.decode("utf-8", errors="replace")
                error = stderr.decode("utf-8", errors="replace")

                return SandboxResult(
                    success=proc.returncode == 0,
                    output=output,
                    error=error if proc.returncode != 0 else None,
                    metadata={"returncode": proc.returncode},
                )

            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise SandboxTimeoutError(f"Execution timeout after {timeout}s")

        finally:
            self._processes = [p for p in self._processes if p != proc]

    def _cleanup_file(self, path: str) -> None:
        """Clean up temporary file."""
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass

    async def cleanup(self) -> None:
        """Clean up sandbox resources."""
        for proc in self._processes:
            try:
                if proc.returncode is None:
                    proc.kill()
                    await proc.wait()
            except Exception:
                pass
        self._processes.clear()

        try:
            import shutil
            if self.work_dir.exists():
                shutil.rmtree(self.work_dir)
        except Exception:
            pass


class RestrictedSubprocessSandbox(SubprocessSandbox):
    """Subprocess sandbox with additional restrictions."""

    def __init__(self, config: SandboxConfig | None = None):
        config = config or SandboxConfig()
        config.blocked_modules = [
            "os.system",
            "subprocess",
            "socket",
            "requests",
            "urllib",
            "importlib",
            "ctypes",
            "fcntl",
            "pty",
            "sys.exit",
            "sys.setrecursionlimit",
        ]
        super().__init__(config)

    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout: int | None = None,
        memory_limit: int | None = None,
    ) -> SandboxResult:
        """Execute with code restrictions."""
        if language == "python":
            restricted_code = self._add_restrictions(code)
            return await super().execute(restricted_code, language, timeout, memory_limit)
        return await super().execute(code, language, timeout, memory_limit)

    def _add_restrictions(self, code: str) -> str:
        """Add security restrictions to Python code."""
        restrictions = """
import sys
import os

_original_exit = sys.exit
def _blocked_exit(*args, **kwargs):
    raise RuntimeError("sys.exit is blocked in sandbox")
sys.exit = _blocked_exit

_original_system = os.system
def _blocked_system(*args, **kwargs):
    raise RuntimeError("os.system is blocked in sandbox")
os.system = _blocked_system

_original_popen = os.popen
def _blocked_popen(*args, **kwargs):
    raise RuntimeError("os.popen is blocked in sandbox")
os.popen = _blocked_popen

"""
        return restrictions + code
