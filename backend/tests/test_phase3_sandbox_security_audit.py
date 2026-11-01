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
    """Verify that container execution exceeding timeout_seconds is terminated and cleaned up."""
    engine = SandboxEngine(timeout_seconds=1)
    mock_p = MagicMock()
    mock_p.kill = MagicMock()
    mock_p.wait = AsyncMock()
    mock_p.communicate = AsyncMock(return_value=(b"", b""))
    mock_p.returncode = 1  # For inspect: non-zero means container does not exist (success)

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
            assert res.container_cleaned is True
            assert res.container_id is not None
            assert res.container_id.startswith("mergemind-sbx-")


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
async def test_sandbox_normal_execution_and_cleanup():
    """Verify normal execution life-cycle: container is uniquely named, executes, and cleans up cleanly."""
    engine = SandboxEngine(timeout_seconds=30)
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.wait = AsyncMock(return_value=0)
    mock_proc.communicate = AsyncMock(return_value=(b"Execution completed successfully\n", b""))

    mock_exec = AsyncMock(return_value=mock_proc)

    with tempfile.TemporaryDirectory() as tmpdir:
        with (
            patch("shutil.which", return_value="/fake/docker"),
            patch("asyncio.create_subprocess_exec", mock_exec),
        ):
            res = await engine.execute_in_container(tmpdir, ["pytest", "-v"])
            assert res.exit_code == 0
            assert res.timed_out is False
            assert res.container_cleaned is True
            assert res.container_id is not None
            assert res.container_id.startswith("mergemind-sbx-")
            assert res.stdout.startswith("Exec")

            # Verify that --name was passed in the docker command
            cmd_args = mock_exec.call_args.args
            assert "--name" in cmd_args
            name_idx = cmd_args.index("--name")
            assert cmd_args[name_idx + 1] == res.container_id


@pytest.mark.asyncio
async def test_sandbox_timeout_with_successful_container_termination():
    """Verify complete timeout lifecycle: host process is killed, docker kill/rm/inspect are executed."""
    engine = SandboxEngine(timeout_seconds=2)
    proc_run = MagicMock()
    proc_run.kill = MagicMock()
    proc_run.wait = AsyncMock(return_value=0)

    proc_kill = MagicMock()
    proc_kill.communicate = AsyncMock(return_value=(b"", b""))

    proc_rm = MagicMock()
    proc_rm.communicate = AsyncMock(return_value=(b"", b""))

    proc_inspect = MagicMock()
    # returncode = 1 indicates container does not exist (successfully purged)
    proc_inspect.returncode = 1
    proc_inspect.communicate = AsyncMock(return_value=(b"", b"Error: No such container"))

    executed_subprocesses = []

    def subprocess_router(*args, **kwargs):
        executed_subprocesses.append(list(args))
        if "kill" in args:
            return proc_kill
        elif "rm" in args:
            return proc_rm
        elif "inspect" in args:
            return proc_inspect
        return proc_run

    with tempfile.TemporaryDirectory() as tmpdir:
        with (
            patch("shutil.which", return_value="/fake/docker"),
            patch("asyncio.create_subprocess_exec", side_effect=subprocess_router),
            patch("asyncio.wait_for", side_effect=TimeoutError()),
        ):
            res = await engine.execute_in_container(tmpdir, ["sleep", "60"])

            # 1. Host process termination
            proc_run.kill.assert_called_once()
            proc_run.wait.assert_awaited_once()

            # 2. Daemon-level container termination and removal
            assert res.timed_out is True
            assert res.container_cleaned is True
            assert res.container_id is not None

            # 3. Verify kill, rm, and inspect commands were dispatched with container_id
            cmd_names = [call[1] for call in executed_subprocesses if len(call) > 1]
            assert "run" in cmd_names
            assert "kill" in cmd_names
            assert "rm" in cmd_names
            assert "inspect" in cmd_names

            for call in executed_subprocesses:
                if len(call) > 1 and call[1] in ("kill", "rm", "inspect"):
                    assert res.container_id in call


@pytest.mark.asyncio
async def test_sandbox_timeout_with_container_cleanup_failure():
    """Verify that if a container cannot be removed, failure is reported and logged."""
    engine = SandboxEngine(timeout_seconds=2)
    proc_run = MagicMock()
    proc_run.kill = MagicMock()
    proc_run.wait = AsyncMock(return_value=0)

    proc_kill = MagicMock()
    proc_kill.communicate = AsyncMock(return_value=(b"", b""))

    proc_rm = MagicMock()
    proc_rm.communicate = AsyncMock(return_value=(b"", b""))

    proc_inspect = MagicMock()
    # returncode = 0 indicates container is STILL present (removal failed)
    proc_inspect.returncode = 0
    proc_inspect.communicate = AsyncMock(return_value=(b"{}", b""))

    def subprocess_router(*args, **kwargs):
        if "kill" in args:
            return proc_kill
        elif "rm" in args:
            return proc_rm
        elif "inspect" in args:
            return proc_inspect
        return proc_run

    with tempfile.TemporaryDirectory() as tmpdir:
        with (
            patch("shutil.which", return_value="/fake/docker"),
            patch("asyncio.create_subprocess_exec", side_effect=subprocess_router),
            patch("asyncio.wait_for", side_effect=TimeoutError()),
        ):
            res = await engine.execute_in_container(tmpdir, ["sleep", "60"])
            assert res.timed_out is True
            # Cleanup was flagged as failed
            assert res.container_cleaned is False
            assert "Container cleanup failed" in (res.error or "")
            assert "Warning: container cleanup failed" in res.stderr


@pytest.mark.asyncio
async def test_sandbox_docker_daemon_unavailable():
    """Verify that if the Docker daemon cannot be contacted, execution fails closed without host fallback."""
    engine = SandboxEngine()
    with tempfile.TemporaryDirectory() as tmpdir:
        with (
            patch("shutil.which", return_value="/fake/docker"),
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=OSError("Cannot connect to the Docker daemon"),
            ),
        ):
            res = await engine.execute_in_container(tmpdir, ["pytest"])
            assert res.exit_code == -1
            assert "Cannot connect to the Docker daemon" in (res.error or "")
            assert res.timed_out is False
