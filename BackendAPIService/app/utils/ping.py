import platform
import socket
import subprocess
from typing import Tuple


def _icmp_ping(host: str, timeout_seconds: int = 2) -> bool:
    """Try to ping a host using system ping command. Returns True if reachable."""
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", "1", "-w", str(timeout_seconds * 1000), host]
    else:
        cmd = ["ping", "-c", "1", "-W", str(timeout_seconds), host]
    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout_seconds + 1)
        return res.returncode == 0
    except Exception:
        return False


def _tcp_fallback(host: str, timeout_seconds: int = 2) -> bool:
    """Fallback reachability check using TCP connect to port 80."""
    try:
        with socket.create_connection((host, 80), timeout=timeout_seconds):
            return True
    except Exception:
        return False


# PUBLIC_INTERFACE
def check_reachability(host: str, timeout_seconds: int = 2) -> Tuple[bool, str]:
    """Check if the host is reachable using ICMP ping, with TCP:80 fallback.

    Returns:
        (reachable, method): reachable flag and method used ("icmp" or "tcp_fallback" or "none")
    """
    if _icmp_ping(host, timeout_seconds):
        return True, "icmp"
    if _tcp_fallback(host, timeout_seconds):
        return True, "tcp_fallback"
    return False, "none"
