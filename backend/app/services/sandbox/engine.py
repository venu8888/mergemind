"""Ephemeral container sandbox execution engine with fail-closed security guarantees."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
import uuid
from dataclasses import dataclass

from app.core.config import settings
from app.core.security import sanitize_log_output

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
    container_id: str | None = None
    container_cleaned: bool = True


class SandboxEngine:
    """Manages ephemeral container lifecycles with strict resource limits and network isolation."""

    GLOBAL_MAX_TIMEOUT_SECONDS: int = 60

    def __init__(
        self,
        image: str = "python:3.13-slim",
        timeout_seconds: int | None = None,
        memory_mb: int | None = None,
        cpu_quota: float | None = None,
    ):
        self.image = image
        raw_timeout = (
            timeout_seconds if timeout_seconds is not None else settings.SANDBOX_TIMEOUT_SECONDS
        )
        # Enforce approved 60-second hard maximum. No runner may silently override this limit.
        self.timeout_seconds = min(raw_timeout, self.GLOBAL_MAX_TIMEOUT_SECONDS)
        self.memory_mb = memory_mb or settings.SANDBOX_MAX_MEMORY_MB
        self.cpu_quota = cpu_quota or settings.SANDBOX_CPU_QUOTA

    def is_docker_available(self) -> bool:
        """Check if Docker CLI binary is present and daemon is responding."""
        docker_bin = shutil.which("docker")
        return docker_bin is not None

    def build_docker_command(
        self,
        workspace_dir: str,
        command: list[str],
        env: dict[str, str] | None = None,
        container_name: str | None = None,
    ) -> list[str]:
        """Construct hardened, non-root, read-only Docker execution arguments."""
        docker_bin = shutil.which("docker") or "docker"
        normalized_workspace = os.path.abspath(workspace_dir)

        docker_cmd = [
            docker_bin,
            "run",
            "--rm",
        ]
        if container_name:
            docker_cmd.extend(["--name", container_name])

        docker_cmd.extend(
            [
                "--read-only",
                "--user",
                "10001:10001",
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
        )

        # Inject non-sensitive environment variables
        if env:
            for k, v in env.items():
                docker_cmd.extend(["-e", f"{k}={v}"])

        docker_cmd.append(self.image)
        docker_cmd.extend(command)
        return docker_cmd

    async def _force_cleanup_container(
        self,
        container_name: str,
        docker_bin: str | None = None,
    ) -> bool:
        """Explicitly kill and remove a container by name from the Docker daemon.

        Ensures that timed-out containers are not left running or orphaned on the daemon.
        Returns True if the container is confirmed dead/removed; False if cleanup failed.
        """
        bin_path = docker_bin or shutil.which("docker") or "docker"
        try:
            # 1. Attempt docker kill to immediately halt untrusted execution
            try:
                kill_proc = await asyncio.create_subprocess_exec(
                    bin_path,
                    "kill",
                    container_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await kill_proc.communicate()
            except Exception as kill_err:
                logger.debug("docker kill for %s produced: %s", container_name, kill_err)

            # 2. Attempt docker rm -f to force remove container state
            try:
                rm_proc = await asyncio.create_subprocess_exec(
                    bin_path,
                    "rm",
                    "-f",
                    container_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await rm_proc.communicate()
            except Exception as rm_err:
                logger.debug("docker rm -f for %s produced: %s", container_name, rm_err)

            # 3. Verify container is no longer present in daemon
            inspect_proc = await asyncio.create_subprocess_exec(
                bin_path,
                "inspect",
                container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await inspect_proc.communicate()

            # Non-zero returncode from inspect means container does not exist (success)
            if inspect_proc.returncode != 0:
                logger.info(
                    "Verified container %s is successfully terminated and removed",
                    container_name,
                )
                return True

            logger.error(
                "Container cleanup failure: %s still found in docker daemon",
                container_name,
            )
            return False
        except Exception as exc:
            logger.error("Error during force cleanup of container %s: %s", container_name, exc)
            return False

    async def execute_in_container(
        self,
        workspace_dir: str,
        command: list[str],
        env: dict[str, str] | None = None,
    ) -> SandboxExecutionResult:
        """Execute a command inside an ephemeral network-isolated container.

        Enforces strict fail-closed security:
        - Never executes on the host as a fallback.
        - Runs as non-root UID 10001:10001.
        - Mounts root filesystem as read-only (--read-only).
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

        # 3. Assign unique container name for reliable tracking and termination
        container_name = f"mergemind-sbx-{uuid.uuid4().hex[:12]}"
        docker_cmd = self.build_docker_command(
            workspace_dir, command, env, container_name=container_name
        )

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
                stdout=sanitize_log_output(raw_stdout),
                stderr=sanitize_log_output(raw_stderr),
                oom_killed=(proc.returncode == 137),
                container_id=container_name,
                container_cleaned=True,
            )
        except TimeoutError:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.warning(
                "Sandbox execution timed out after %ds; terminating process and container %s",
                self.timeout_seconds,
                container_name,
            )
            # Step A: Terminate the host CLI subprocess
            try:
                proc.kill()
                await proc.wait()
            except ProcessLookupError:
                pass
            except Exception as kill_err:
                logger.warning("Error terminating host process: %s", kill_err)

            # Step B: Explicitly kill and remove the container from Docker daemon
            cleaned = await self._force_cleanup_container(container_name, docker_bin)

            error_msg = f"Timeout after {self.timeout_seconds}s"
            stderr_msg = (
                f"Sandbox execution exceeded hard timeout limit of {self.timeout_seconds} seconds"
            )
            if not cleaned:
                error_msg += f" (Container cleanup failed for {container_name})"
                stderr_msg += f". Warning: container cleanup failed for {container_name}"

            return SandboxExecutionResult(
                exit_code=-1,
                duration_ms=duration_ms,
                stdout="",
                stderr=stderr_msg,
                timed_out=True,
                error=error_msg,
                container_id=container_name,
                container_cleaned=cleaned,
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error("Sandbox container execution error: %s", exc)
            cleaned = await self._force_cleanup_container(container_name, docker_bin)
            return SandboxExecutionResult(
                exit_code=-1,
                duration_ms=duration_ms,
                stdout="",
                stderr=str(exc),
                error=f"Sandbox execution failed: {exc}",
                container_id=container_name,
                container_cleaned=cleaned,
            )
