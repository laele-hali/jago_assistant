import subprocess


def run_command(cmd: str) -> str:
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15
        )
        output = result.stdout.strip() or result.stderr.strip()
        return output or "No output."
    except Exception as e:
        return f"Error: {e}"


def get_uptime() -> str:
    return run_command("uptime -p")


def get_disk() -> str:
    return run_command("df -h /")


def get_sysinfo() -> str:
    return run_command("top -b -n1 | head -n 5")
