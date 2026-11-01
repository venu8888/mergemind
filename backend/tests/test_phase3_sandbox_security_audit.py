"""Audit verification tests for Sandbox Security and Container Isolation guarantees."""

from __future__ import annotations

import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import settings
from app.services.sandbox.engine import SandboxEngine


def test_sandbox_docker_security_arguments():
    """Verify that every security enforcement flag required by Phase 3 architecture is present."""
    engine = SandboxEngine(
        image="python:3.13-slim",
        timeout_seconds=45,
        memory_mb=512,
        cpu_quota=1.0,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = engine.build_docker_command(
            workspace_dir=tmpdir,
            command=["pytest", "-v"],
            env={"FOO": "BAR"},
        )

        # 1. Ephemeral execution environment
        assert "--rm" in cmd, "Ephemeral flag --rm must be present"

        # 2. Non-root execution: UID 10001
        assert "--user" in cmd, "--user flag must be present"
        user_idx = cmd.index("--user")
        assert cmd[user_idx + 1] == "10001:10001", "Execution user must be 10001:10001"

        # 3. Read-only root filesystem
        assert "--read-only" in cmd, "--read-only flag must be present"

        # 4. Network isolation
        assert "--network" in cmd, "--network flag must be present"
        net_idx = cmd.index("--network")
        assert cmd[net_idx + 1] == "none", "Network must be strictly disabled (--network none)"

        # 5. Linux capability dropping
        assert "--cap-drop" in cmd, "--cap-drop flag must be present"
        cap_idx = cmd.index("--cap-drop")
        assert cmd[cap_idx + 1] == "ALL", "All Linux capabilities must be dropped"

        # 6. Privilege escalation prevention
        assert "--security-opt" in cmd, "--security-opt flag must be present"
        sec_idx = cmd.index("--security-opt")
        assert cmd[sec_idx + 1] == "no-new-privileges:true", "no-new-privileges must be true"

        # 7. Resource limits: memory and CPU quotas
        assert "--memory" in cmd
        mem_idx = cmd.index("--memory")
        assert cmd[mem_idx + 1] == "512m", "Memory limit must be 512m"

        assert "--cpus=1.0" in cmd, "CPU quota must be enforced"

        # 8. Temporary writable directory via tmpfs
        assert "--tmpfs" in cmd
        tmp_idx = cmd.index("--tmpfs")
        assert "size=128m" in cmd[tmp_idx + 1]

        # 9. No Docker socket exposure
        assert not any("docker.sock" in arg for arg in cmd), (
            "Docker socket must never be exposed to container"
        )

        # 10. No host credentials or secrets mounted
        assert not any(".ssh" in arg for arg in cmd), "Host SSH directory must not be mounted"
        assert not any(".aws" in arg for arg in cmd), "Host AWS directory must not be mounted"
        assert not any(".env" in arg for arg in cmd), "Host .env file must not be mounted"

        # 11. Workspace mount restricted
        assert any(":/workspace:rw" in arg for arg in cmd), (
            "Only workspace must be mounted as /workspace:rw"
        )


@pytest.mark.asyncio
async def test_sandbox_zero_host_execution_fallback():
    """Verify zero host execution fallback when Docker is disabled or binary is absent."""
    orig_type = settings.SANDBOX_TYPE
    try:
        # Case A: Sandbox explicitly disabled by configuration -> Fail closed
        settings.SANDBOX_TYPE = "disabled"
        engine = SandboxEngine()
        with tempfile.TemporaryDirectory() as tmpdir:
            res = await engine.execute_in_container(tmpdir, ["echo", "untrusted"])
            assert res.exit_code == -1
            assert (
                "Execution sandbox is disabled by configuration (fail-closed policy enforced; zero host fallback)"
                in (res.error or "")
            )

        # Case B: Sandbox configured but Docker CLI is missing -> Fail closed
        settings.SANDBOX_TYPE = "container"
        with patch("shutil.which", return_value=None):
            res_no_docker = await engine.execute_in_container(tmpdir, ["echo", "untrusted"])
            assert res_no_docker.exit_code == -1
            assert "Docker CLI not found for sandbox execution" in (res_no_docker.error or "")
    finally:
        settings.SANDBOX_TYPE = orig_type


@pytest.mark.asyncio
async def test_sandbox_hard_execution_timeout():
    """Verify that container execution exceeding timeout_seconds is terminated."""
    engine = SandboxEngine(timeout_seconds=1)
    mock_p = MagicMock()
    mock_p.kill = MagicMock()
    mock_p.wait = AsyncMock()
    with tempfile.TemporaryDirectory() as tmpdir:
        # Simulate timeout by patching asyncio.wait_for to raise TimeoutError
        with (
            patch("shutil.which", return_value="/fake/docker"),
            patch("asyncio.create_subprocess_exec", return_value=mock_p),
            patch("asyncio.wait_for", side_effect=TimeoutError()),
        ):
            res = await engine.execute_in_container(tmpdir, ["sleep", "100"])
            assert res.timed_out is True
            assert res.exit_code in (-1, 124)
            assert "Timeout after 1s" in (res.error or "")


def test_sandbox_timeout_clamped_to_global_maximum():
    """Verify that timeout cannot silently exceed the approved 60s hard maximum."""
    # Attempting to set 300s must be clamped to 60s
    engine_long = SandboxEngine(timeout_seconds=300)
    assert engine_long.timeout_seconds == 60
    assert engine_long.timeout_seconds <= SandboxEngine.GLOBAL_MAX_TIMEOUT_SECONDS

    # Setting shorter timeout (e.g. 25s) is allowed
    engine_short = SandboxEngine(timeout_seconds=25)
    assert engine_short.timeout_seconds == 25


@pytest.mark.asyncio
async def test_sandbox_timeout_terminates_container_process():
    """Verify that a timed-out execution explicitly kills the underlying container process."""
    engine = SandboxEngine(timeout_seconds=2)
    mock_proc = MagicMock()
    mock_proc.kill = MagicMock()
    mock_proc.wait = AsyncMock()

    with tempfile.TemporaryDirectory() as tmpdir:
        with (
            patch("shutil.which", return_value="/fake/docker"),
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("asyncio.wait_for", side_effect=TimeoutError()),
        ):
            res = await engine.execute_in_container(tmpdir, ["sleep", "60"])
            assert res.timed_out is True
            # Verified process termination
            mock_proc.kill.assert_called_once()
            mock_proc.wait.assert_awaited_once()
