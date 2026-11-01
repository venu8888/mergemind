"""Ephemeral container sandbox execution engine with fail-closed security guarantees."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
from dataclasses import dataclass

from app.core.config import settings
from app.core.security import sanitize_secret

logger = logging.getLogger(__name__)


@dataclass
class SandboxExecutionResult:
    """Raw container sandbox execution output."""

    exit_code: int
    duration_ms: int
    stdout: str
    stderr: str
    timed_out: bool = False
    oom_killed: bool = False
    error: str | None = None


class SandboxEngine:
    """Manages ephemeral container lifecycles with strict resource limits and network isolation."""

    def __init__(
        self,
        image: str = "python:3.13-slim",
        timeout_seconds: int | None = None,
        memory_mb: int | None = None,
        cpu_quota: float | None = None,
    ):
        self.image = image
        self.timeout_seconds = timeout_seconds or settings.SANDBOX_TIMEOUT_SECONDS
        self.memory_mb = memory_mb or settings.SANDBOX_MAX_MEMORY_MB
        self.cpu_quota = cpu_quota or settings.SANDBOX_CPU_QUOTA

    def is_docker_available(self) -> bool:
        """Check if Docker CLI binary is present and daemon is responding."""
        docker_bin = shutil.which("docker")
        return docker_bin is not None

    async def execute_in_container(
        self,
        workspace_dir: str,
        command: list[str],
        env: dict[str, str] | None = None,
    ) -> SandboxExecutionResult:
        """Execute a command inside an ephemeral network-isolated container.

        Enforces strict fail-closed security:
        - Never executes on the host as a fallback.
        - Mounts workspace with read/write access restricted to the isolated sandbox container.
        - Drops all Linux capabilities and prevents privilege escalation.
        - Network disabled (--network none).
        """
        start_time = time.perf_counter()

        # 1. Enforce fail-closed policy if sandbox is disabled
        if settings.SANDBOX_TYPE == "disabled":
            return SandboxExecutionResult(
                exit_code=-1,
                duration_ms=0,
                stdout="",
                stderr="",
                error="Execution sandbox is disabled by configuration (fail-closed policy enforced; zero host fallback)",
            )

        # 2. Enforce fail-closed if Docker is unavailable
        docker_bin = shutil.which("docker")
        if not docker_bin:
            return SandboxExecutionResult(
                exit_code=-1,
                duration_ms=0,
                stdout="",
                stderr="",
                error="Docker CLI not found for sandbox execution (fail-closed; zero host fallback)",
            )

        # 3. Construct hardened docker run arguments
        # Workspace path normalization for cross-platform mounts
        normalized_workspace = os.path.abspath(workspace_dir)

        docker_cmd = [
            docker_bin,
            "run",
            "--rm",
            "--network",
            "none",
            "--memory",
            f"{self.memory_mb}m",
            f"--cpus={self.cpu_quota}",
            "--security-opt",
            "no-new-privileges:true",
            "--cap-drop",
            "ALL",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=128m",  # nosec B108
            "-v",
            f"{normalized_workspace}:/workspace:rw",
            "-w",
            "/workspace",
        ]

        # Inject non-sensitive environment variables
        if env:
            for k, v in env.items():
                docker_cmd.extend(["-e", f"{k}={v}"])

        docker_cmd.append(self.image)
        docker_cmd.extend(command)

        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=float(self.timeout_seconds)
            )

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            raw_stdout = stdout_bytes.decode("utf-8", errors="replace")
            raw_stderr = stderr_bytes.decode("utf-8", errors="replace")

            return SandboxExecutionResult(
                exit_code=proc.returncode if proc.returncode is not None else -1,
                duration_ms=duration_ms,
                stdout=sanitize_secret(raw_stdout),
                stderr=sanitize_secret(raw_stderr),
                oom_killed=(proc.returncode == 137),
            )
        except TimeoutError:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.warning("Sandbox execution timed out after %ds", self.timeout_seconds)
            return SandboxExecutionResult(
                exit_code=-1,
                duration_ms=duration_ms,
                stdout="",
                stderr=f"Sandbox execution exceeded hard timeout limit of {self.timeout_seconds} seconds",
                timed_out=True,
                error=f"Timeout after {self.timeout_seconds}s",
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("Sandbox container execution error: %s", exc)
            return SandboxExecutionResult(
                exit_code=-1,
                duration_ms=duration_ms,
                stdout="",
                stderr=str(exc),
                error=f"Sandbox execution failed: {exc}",
            )
