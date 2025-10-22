import platform
import subprocess
from typing import Tuple


# PUBLIC_INTERFACE
def ping_host(ip: str, timeout_ms: int = 2000) -> Tuple[bool, str]:
    """Ping a host once with a timeout.
    Returns (is_online, raw_message). Never raises on failure.
    """
    system = platform.system().lower()

    # Calculate flags for platform
    if "windows" in system:
        # -n count, -w timeout in ms
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), ip]
    else:
        # -c count, -W timeout in seconds (round up), -n numeric output
        timeout_sec = max(1, int(round(timeout_ms / 1000)))
        cmd = ["ping", "-c", "1", "-W", str(timeout_sec), "-n", ip]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        success = proc.returncode == 0
        output = (proc.stdout or "") + (proc.stderr or "")
        return success, output.strip()
    except Exception as e:
        return False, f"Ping failed: {e!r}"
