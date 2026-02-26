"""Code execution tool for running code in sandboxed environment."""

import asyncio
import tempfile
from pathlib import Path
from typing import Any

from manus.tools.base import Tool, ToolResult, ToolStatus


class CodeExecutionTool(Tool):
    """Execute code in a sandboxed environment."""

    def __init__(self, timeout: int = 60, max_output: int = 10000):
        super().__init__(
            name="execute_code",
            description="Execute Python code in a sandboxed environment. Use this to run code, analyze data, or test functions.",
            parameters={
                "code": {
                    "schema": {"type": "string", "description": "Python code to execute"},
                    "required": True,
                },
                "language": {
                    "schema": {"type": "string", "enum": ["python", "bash"], "default": "python"},
                    "required": False,
                },
            },
        )
        self.timeout = timeout
        self.max_output = max_output

    async def execute(self, code: str, language: str = "python", **kwargs) -> ToolResult:
        """Execute code."""
        try:
            if language == "python":
                return await self._execute_python(code)
            elif language == "bash":
                return await self._execute_bash(code)
            else:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error=f"Unsupported language: {language}",
                )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )

    async def _execute_python(self, code: str) -> ToolResult:
        """Execute Python code."""
        output = ""
        error = None

        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                temp_file = f.name

            process = await asyncio.create_subprocess_exec(
                "python3",
                temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.TIMEOUT,
                    error=f"Execution timeout after {self.timeout} seconds",
                )

            output = stdout.decode("utf-8", errors="replace")
            error_msg = stderr.decode("utf-8", errors="replace")

            if output:
                output = output[: self.max_output]
            if error_msg:
                error = error_msg[: self.max_output]

            Path(temp_file).unlink(missing_ok=True)

            if process.returncode != 0:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    content=output,
                    error=error,
                )

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                content=output,
                metadata={"language": "python"},
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )

    async def _execute_bash(self, code: str) -> ToolResult:
        """Execute bash command."""
        try:
            process = await asyncio.create_subprocess_shell(
                code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.TIMEOUT,
                    error=f"Execution timeout after {self.timeout} seconds",
                )

            output = stdout.decode("utf-8", errors="replace")[: self.max_output]
            error_msg = stderr.decode("utf-8", errors="replace")[: self.max_output]

            if process.returncode != 0:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    content=output,
                    error=error_msg,
                )

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                content=output,
                metadata={"language": "bash"},
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )
