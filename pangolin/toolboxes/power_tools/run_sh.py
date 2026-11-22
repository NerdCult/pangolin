import os
import sys
import signal
import subprocess

SCHEMA = {
    "name": "run_sh",
    "description": (
        "Run a shell command on the host machine and return exit_code, stdout and stderr. "
        "NOT sandboxed: runs with the agent's full user permissions. "
        "The agent's Python interpreter directory is first on PATH, so `python` / `python -m pip` "
        "target the agent's own environment. stdin is closed, so interactive prompts fail instead of hanging."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute."},
            "timeout": {"type": "integer", "description": "Seconds before the command (and its children) are killed. Default 120, max 1800."},
            "cwd": {"type": "string", "description": "Working directory. Default: the agent's current working directory."},
        },
        "required": ["command"],
    },
}

MAX_OUTPUT = 20000


def _trim(s):
    if s is None:
        return ""
    if isinstance(s, bytes):
        s = s.decode("utf-8", errors="replace")
    if len(s) <= MAX_OUTPUT:
        return s
    half = MAX_OUTPUT // 2
    return s[:half] + f"\n...[{len(s) - MAX_OUTPUT} chars truncated]...\n" + s[-half:]


def _kill_tree(p):
    try:
        if os.name == "posix":
            os.killpg(p.pid, signal.SIGKILL)
        else:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
    except Exception:
        p.kill()


def run(command, timeout=120, cwd=None):
    timeout = max(1, min(int(timeout or 120), 1800))
    env = os.environ.copy()
    env["PATH"] = os.path.dirname(sys.executable) + os.pathsep + env.get("PATH", "")

    kwargs = dict(
        shell=True,
        cwd=cwd or os.getcwd(),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if os.name == "posix":
        kwargs["start_new_session"] = True  # own process group so timeout kills children too

    try:
        p = subprocess.Popen(command, **kwargs)
    except Exception as e:
        return {"exit_code": None, "error": f"{type(e).__name__}: {e}"}

    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(p)
        out, err = p.communicate()
        return {"exit_code": None, "timed_out": True, "error": f"killed after {timeout}s",
                "stdout": _trim(out), "stderr": _trim(err)}

    return {"exit_code": p.returncode, "stdout": _trim(out), "stderr": _trim(err)}
