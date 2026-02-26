"""Docker-based sandbox implementation."""

import asyncio
import json
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


class DockerSandbox(Sandbox):
    """Docker-based sandbox for secure code execution."""

    def __init__(
        self,
        config: SandboxConfig | None = None,
        image: str = "manus-sandbox:latest",
        container_name_prefix: str = "manus_sandbox_",
    ):
        super().__init__(config)
        self.image = image
        self.container_prefix = container_name_prefix
        self._active_containers: list[str] = []

    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout: int | None = None,
        memory_limit: int | None = None,
    ) -> SandboxResult:
        """Execute code in Docker container."""
        timeout = timeout or self.config.timeout
        memory_limit = memory_limit or self.config.memory_limit

        container_name = f"{self.container_prefix}{int(time.time() * 1000)}"

        try:
            result = await self._run_in_container(
                code, language, container_name, timeout, memory_limit
            )
            return result

        except TimeoutError as e:
            await self._cleanup_container(container_name)
            return SandboxResult(
                success=False,
                output="",
                error=str(e),
                execution_time=timeout,
            )

        except Exception as e:
            await self._cleanup_container(container_name)
            return SandboxResult(
                success=False,
                output="",
                error=f"Docker execution error: {str(e)}",
            )

        finally:
            await self._cleanup_container(container_name)

    async def _run_in_container(
        self,
        code: str,
        language: str,
        container_name: str,
        timeout: int,
        memory_limit: int,
    ) -> SandboxResult:
        """Run code inside Docker container."""
        import aiofiles

        ext = self._get_file_extension(language)
        executor = self._get_executor(language)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=ext, delete=False
        ) as f:
            f.write(code)
            code_file = f.name

        code_filename = Path(code_file).name

        try:
            pull_cmd = [
                "docker", "pull", self.image
            ]
            try:
                await asyncio.create_subprocess_exec(
                    *pull_cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            except Exception:
                pass

            cmd = [
                "docker", "run",
                "--rm",
                "--name", container_name,
                "--network", "none" if not self.config.network_enabled else "bridge",
                "--memory", f"{memory_limit}m",
                "--cpus", str(self.config.cpu_limit),
                "-v", f"{Path(code_file).parent}:/code",
                "-w", "/code",
                self.image,
                executor, code_filename
            ]

            start_time = time.time()

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            self._active_containers.append(container_name)

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
                    metadata={
                        "returncode": proc.returncode,
                        "container": container_name,
                    },
                )

            except asyncio.TimeoutError:
                await self._cleanup_container(container_name)
                raise SandboxTimeoutError(f"Execution timeout after {timeout}s")

        finally:
            Path(code_file).unlink(missing_ok=True)

    async def _cleanup_container(self, container_name: str) -> None:
        """Clean up Docker container."""
        try:
            kill_proc = await asyncio.create_subprocess_exec(
                "docker", "kill", container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await kill_proc.wait()
        except Exception:
            pass

        if container_name in self._active_containers:
            self._active_containers.remove(container_name)

    async def cleanup(self) -> None:
        """Clean up all active containers."""
        for container in self._active_containers[:]:
            await self._cleanup_container(container)
        self._active_containers.clear()

    async def is_docker_available(self) -> bool:
        """Check if Docker is available."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.wait()
            return proc.returncode == 0
        except Exception:
            return False


class DockerSandboxPool:
    """Pool of Docker sandboxes for better performance."""

    def __init__(
        self,
        image: str = "manus-sandbox:latest",
        pool_size: int = 5,
        config: SandboxConfig | None = None,
    ):
        self.image = image
        self.pool_size = pool_size
        self.config = config or SandboxConfig()
        self._pool: asyncio.Queue[DockerSandbox] = asyncio.Queue()
        self._created = 0

    async def initialize(self) -> None:
        """Initialize the pool."""
        for _ in range(self.pool_size):
            sandbox = DockerSandbox(self.config, self.image)
            await self._pool.put(sandbox)

    async def acquire(self) -> DockerSandbox:
        """Acquire a sandbox from the pool."""
        try:
            return await asyncio.wait_for(
                self._pool.get(),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            return DockerSandbox(self.config, self.image)

    async def release(self, sandbox: DockerSandbox) -> None:
        """Release a sandbox back to the pool."""
        if self._pool.qsize() < self.pool_size:
            await self._pool.put(sandbox)

    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout: int | None = None,
        memory_limit: int | None = None,
    ) -> SandboxResult:
        """Execute code using pooled sandbox."""
        sandbox = await self.acquire()
        try:
            return await sandbox.execute(
                code, language, timeout, memory_limit
            )
        finally:
            await self.release(sandbox)

    async def cleanup(self) -> None:
        """Clean up all sandboxes in the pool."""
        while not self._pool.empty():
            try:
                sandbox = self._pool.get_nowait()
                await sandbox.cleanup()
            except Exception:
                break
