import platform
import subprocess
from datetime import datetime
from bson import ObjectId

# PUBLIC_INTERFACE
def to_object_id(id_str: str) -> ObjectId:
    """Convert a string to a BSON ObjectId, raising ValueError if invalid."""
    if not ObjectId.is_valid(id_str):
        raise ValueError("Invalid ObjectId")
    return ObjectId(id_str)

def now_utc() -> datetime:
    """Current UTC timestamp without timezone info (stored as naive UTC)."""
    return datetime.utcnow()

def try_ping(ip: str, timeout_seconds: int = 2) -> str:
    """
    Try to ping the given IP address.
    Returns one of: 'online', 'offline', 'unknown'
    - 'unknown' is returned when ping utility is not available or fails unexpectedly.
    """
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", "1", "-w", str(timeout_seconds * 1000), ip]
    else:
        # On Unix, -c 1 (one packet), -W timeout in seconds (Linux); on mac, -W is in ms, but we keep small timeout
        cmd = ["ping", "-c", "1", "-W", str(timeout_seconds), ip]
    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout_seconds + 2)
        if res.returncode == 0:
            return "online"
        return "offline"
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return "unknown"
